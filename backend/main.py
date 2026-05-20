# =============================================================
# Rasd App — FastAPI Backend
# =============================================================
# Endpoints:
#   GET  /                        health check
#   GET  /api/categories          list all source categories (for tabs)
#   GET  /api/sources             list all accounts (optionally filter by category)
#   GET  /api/feed                aggregated latest posts from all accounts
# =============================================================

import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# Manually load .env (small parser — avoids adding python-dotenv dependency).
_ENV_PATH = Path(__file__).resolve().parent / ".env"
if _ENV_PATH.exists():
    for line in _ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from sources import SOURCES, categories_meta, flatten
from x_client import fetch_user_tweets, USE_COOKIES

app = FastAPI(title="Rasd Monitoring API")

# Permissive CORS so the bundled single-file frontend can call us when opened
# via file:// or any local port.
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=".*",
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "rasd-monitoring"}


@app.get("/api/categories")
def list_categories():
    return {
        "categories": categories_meta(),
        "auth_mode": "cookies" if USE_COOKIES else "guest",
    }


@app.get("/api/sources")
def list_sources(category: str | None = Query(None)):
    cats = [category] if category else None
    return {"sources": flatten(categories=cats)}


# ---------------------- single-account fetch ----------------------
@app.get("/api/account")
def fetch_one_account(
    handle: str = Query(..., description="X username or FB page slug/id"),
    platform: str = Query("x", description="x | fb"),
    per_account: int = Query(5, ge=1, le=20),
    date_filter: str = Query("all", description="24h|3d|7d|30d|90d|all"),
):
    """Fetch one account's posts. Designed for on-demand click-to-load UX
    instead of fanning out across all 41+ configured sources at once."""
    handle = handle.strip().lstrip("@")
    if not handle:
        return {"error": "empty handle", "posts": []}

    if date_filter not in ("24h", "3d", "7d", "30d", "90d", "all"):
        date_filter = "all"

    if platform == "fb":
        # Facebook now blocks unauthenticated scraping at the platform level
        # (both mbasic.facebook.com and www.facebook.com return error pages
        # without a logged-in session). We surface a clear message so the
        # UI can render a "open page" fallback.
        return {
            "handle": handle,
            "platform": "fb",
            "posts": [],
            "error": "facebook_blocks_scraping",
        }

    res = fetch_user_tweets(handle, limit=per_account, date_filter=date_filter)
    return {
        "handle": handle,
        "platform": "x",
        "posts": res.get("posts") or [],
        "error": res.get("error"),
    }


# ---------------------- aggregated feed ----------------------
_FEED_CACHE = {}
_FEED_TTL = 600  # 10 min
_FEED_LOCK = threading.Lock()


def _feed_cache_get(key):
    with _FEED_LOCK:
        e = _FEED_CACHE.get(key)
        if not e:
            return None
        ts, v = e
        if time.time() - ts > _FEED_TTL:
            _FEED_CACHE.pop(key, None)
            return None
        return v


def _feed_cache_set(key, v):
    with _FEED_LOCK:
        _FEED_CACHE[key] = (time.time(), v)


def _fetch_one(acc, per_account, date_filter):
    if acc["platform"] != "x":
        # Facebook handled separately by the frontend (direct link).
        return {**acc, "posts": [], "error": "facebook_link_only"}
    try:
        res = fetch_user_tweets(acc["handle"], limit=per_account, date_filter=date_filter)
        return {**acc, "posts": res.get("posts") or [], "error": res.get("error")}
    except Exception as e:
        return {**acc, "posts": [], "error": str(e)}


@app.get("/api/feed")
def feed(
    category: str | None = Query(None, description="Category id (omit for all)"),
    per_account: int = Query(5, ge=1, le=20),
    date_filter: str = Query("7d", description="24h|3d|7d|30d|90d|all"),
    # Without auth cookies X rate-limits aggressively, so be polite by default.
    parallel: int = Query(6 if USE_COOKIES else 2, ge=1, le=12),
    force: int = Query(0, description="1 = bypass 10-min cache"),
):
    if date_filter not in ("24h", "3d", "7d", "30d", "90d", "all"):
        date_filter = "7d"

    cache_key = f"{category or 'all'}|{per_account}|{date_filter}"
    if not force:
        cached = _feed_cache_get(cache_key)
        if cached:
            return {**cached, "cached": True}

    cats = [category] if category else None
    x_accounts  = flatten(categories=cats, platform="x")
    fb_accounts = flatten(categories=cats, platform="fb")

    started = time.time()
    results = []
    with ThreadPoolExecutor(max_workers=parallel) as ex:
        futures = [ex.submit(_fetch_one, a, per_account, date_filter) for a in x_accounts]
        for f in as_completed(futures):
            results.append(f.result())

    # Add Facebook accounts as direct-link cards (no scraping for now).
    for acc in fb_accounts:
        results.append({**acc, "posts": [], "error": "facebook_link_only"})

    # Sort: accounts with posts first, then by latest post date desc
    def _sort_key(a):
        posts = a.get("posts") or []
        if not posts:
            return (1, "")
        return (0, "-" + (posts[0].get("created_at") or ""))
    results.sort(key=_sort_key)

    payload = {
        "category": category or "all",
        "date_filter": date_filter,
        "per_account": per_account,
        "elapsed_sec": round(time.time() - started, 2),
        "accounts": results,
        "cached": False,
    }
    _feed_cache_set(cache_key, payload)
    return payload


# ---------------------- serve the frontend ----------------------
# Lets `python main.py` run the whole app at http://127.0.0.1:8765
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
if FRONTEND_DIR.exists():
    @app.get("/")
    def root():
        return FileResponse(FRONTEND_DIR / "index.html")
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


if __name__ == "__main__":
    import uvicorn
    print("\n  ===============================================")
    print("   Rasd Monitoring App")
    print("   Open in browser: http://127.0.0.1:8765")
    print("  ===============================================\n")
    uvicorn.run(app, host="127.0.0.1", port=8765)
