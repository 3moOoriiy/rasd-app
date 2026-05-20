# =============================================================
# Rasd App — Facebook Client (Selenium / Edge)
# =============================================================
# Facebook now blocks unauthenticated scraping at the platform level, so
# we drive a real Edge browser, log in once with a throwaway account
# (configured via env vars), and reuse that session for every fetch.
#
# Env vars (read from backend/.env):
#   FB_EMAIL           — login email
#   FB_PASSWORD        — login password
#   EDGE_DRIVER_PATH   — path to msedgedriver.exe (or leave blank to use PATH)
#   FB_HEADLESS        — "1" (default) for headless, "0" to show the browser
# =============================================================

import json
import os
import re
import threading
import time
from pathlib import Path
from typing import Optional

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.edge.options import Options as EdgeOptions
    from selenium.webdriver.edge.service import Service as EdgeService
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import (
        NoSuchElementException, TimeoutException, WebDriverException,
    )
    _SELENIUM_OK = True
except ImportError:
    _SELENIUM_OK = False


FB_EMAIL         = os.environ.get("FB_EMAIL", "").strip()
FB_PASSWORD      = os.environ.get("FB_PASSWORD", "").strip()
EDGE_DRIVER_PATH = os.environ.get("EDGE_DRIVER_PATH", "").strip()
FB_HEADLESS      = os.environ.get("FB_HEADLESS", "1") != "0"

FB_AVAILABLE = _SELENIUM_OK and bool(FB_EMAIL and FB_PASSWORD)

if not _SELENIUM_OK:
    print("[fb_client] selenium not installed — FB scraping disabled.")
elif not FB_AVAILABLE:
    print("[fb_client] FB_EMAIL / FB_PASSWORD not set — FB scraping disabled.")
else:
    print(f"[fb_client] FB scraping enabled (headless={FB_HEADLESS}).")


_DRIVER = None
_LOGGED_IN = False
_DRIVER_LOCK = threading.Lock()

# Persisted cookies — once we successfully log in, save the cookies so the
# next process boot can skip the email/password flow (and the FB 2FA wall
# that comes with it for fresh / throwaway accounts).
COOKIES_PATH = Path(__file__).resolve().parent / "fb_cookies.json"


def _save_cookies(drv):
    try:
        cookies = drv.get_cookies()
        COOKIES_PATH.write_text(json.dumps(cookies, ensure_ascii=False), encoding="utf-8")
        print(f"[fb_client] saved {len(cookies)} cookies → fb_cookies.json")
    except Exception as e:
        print(f"[fb_client] could not save cookies: {e}")


def _load_cookies_into(drv) -> bool:
    """Try to restore a previous session from disk. Returns True if the
    cookies actually got us a logged-in homepage."""
    if not COOKIES_PATH.exists():
        return False
    try:
        cookies = json.loads(COOKIES_PATH.read_text(encoding="utf-8"))
        # Need to be on the domain first to add cookies for it
        drv.get("https://www.facebook.com/")
        for c in cookies:
            # Selenium rejects sameSite=None unless we strip it
            c.pop("sameSite", None)
            # expiry must be int, drop if it's a float in the file
            if "expiry" in c:
                try: c["expiry"] = int(c["expiry"])
                except Exception: c.pop("expiry", None)
            try:
                drv.add_cookie(c)
            except Exception:
                continue
        drv.get("https://www.facebook.com/")
        time.sleep(3)
        url = drv.current_url.lower()
        ok = "login" not in url and "checkpoint" not in url and "two_step" not in url
        if ok:
            print("[fb_client] restored session from fb_cookies.json")
        return ok
    except Exception as e:
        print(f"[fb_client] could not load cookies: {e}")
        return False


def _build_driver():
    """Create a fresh Edge driver. Caller holds _DRIVER_LOCK."""
    opts = EdgeOptions()
    opts.add_argument("--disable-notifications")
    opts.add_argument("--lang=ar")
    opts.add_argument("--window-size=1280,900")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    )
    if FB_HEADLESS:
        opts.add_argument("--headless=new")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)

    if EDGE_DRIVER_PATH:
        service = EdgeService(EDGE_DRIVER_PATH)
        drv = webdriver.Edge(service=service, options=opts)
    else:
        drv = webdriver.Edge(options=opts)
    drv.set_page_load_timeout(45)
    return drv


def _do_login(drv):
    """Log into facebook.com. Returns True on success."""
    drv.get("https://www.facebook.com/")
    try:
        WebDriverWait(drv, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='email']"))
        )
    except TimeoutException:
        # No login form — likely already logged in via cookies
        return True

    try:
        drv.find_element(By.CSS_SELECTOR, "input[name='email']").send_keys(FB_EMAIL)
        drv.find_element(By.CSS_SELECTOR, "input[name='pass']").send_keys(FB_PASSWORD)
        # FB has used several selectors for the submit button over time.
        # Try them in order until one works.
        submit = None
        for sel in (
            "button[name='login']",
            "button[type='submit']",
            "[data-testid='royal_login_button']",
            "button[data-pressed='false']",
        ):
            try:
                submit = drv.find_element(By.CSS_SELECTOR, sel)
                break
            except NoSuchElementException:
                continue
        if submit is None:
            # Fall back to pressing Enter in the password field
            from selenium.webdriver.common.keys import Keys
            drv.find_element(By.CSS_SELECTOR, "input[name='pass']").send_keys(Keys.RETURN)
        else:
            submit.click()

        # When the browser is visible, give the user up to 3 minutes to solve
        # any 2FA / checkpoint challenge manually. In headless we can only
        # handle the happy path.
        max_wait = 180 if not FB_HEADLESS else 15
        warned = False
        start = time.time()
        while time.time() - start < max_wait:
            time.sleep(2)
            url = drv.current_url.lower()
            if all(x not in url for x in ("login", "checkpoint", "two_step")):
                return True
            if not warned and ("checkpoint" in url or "two_step" in url):
                if FB_HEADLESS:
                    print("[fb_client] FB security challenge — set FB_HEADLESS=0 in .env and restart, solve it once in the visible browser, cookies will then persist")
                    return False
                else:
                    print("[fb_client] FB security challenge — please solve it in the visible browser window. Waiting up to 3 minutes...")
                    warned = True
        print(f"[fb_client] login timed out at URL={drv.current_url}")
        return False
    except Exception as e:
        print(f"[fb_client] login failed: {e}")
        return False


def _ensure_session():
    """Boot driver + log in if needed. Caller holds _DRIVER_LOCK."""
    global _DRIVER, _LOGGED_IN
    if _DRIVER is None:
        _DRIVER = _build_driver()
        _LOGGED_IN = False
    if _LOGGED_IN:
        return True
    # Try saved cookies first — skips the 2FA wall that new accounts hit
    if _load_cookies_into(_DRIVER):
        _LOGGED_IN = True
        return True
    # Fall back to email/password
    if _do_login(_DRIVER):
        _save_cookies(_DRIVER)
        _LOGGED_IN = True
        return True
    return False


def _page_url(handle: str) -> str:
    """Build the FB profile URL from a handle (slug or numeric id)."""
    h = handle.strip().lstrip("@")
    if h.isdigit():
        return f"https://www.facebook.com/profile.php?id={h}"
    return f"https://www.facebook.com/{h}"


_AR_RELATIVE_DATE = re.compile(
    r"(?:قبل|منذ)\s+\d+\s*(?:ثانية|ثوان|دقيقة|دقائق|ساعة|ساعات|يوم|أيام|أسبوع|أسابيع|شهر|أشهر|سنة|سنوات)",
    re.UNICODE,
)


def _looks_like_post(text: str) -> bool:
    """Filter out non-post articles (suggestions, ads, side widgets)."""
    if not text or len(text) < 40:
        return False
    bad = [
        "Suggested for you",
        "اقتراحات لك",
        "إعلان",
        "Sponsored",
        "People you may know",
        "ربما تعرفهم",
    ]
    return not any(b in text for b in bad)


def _clean_caption(text: str) -> str:
    """Strip the typical FB UI noise that comes inside an article's text."""
    if not text:
        return ""
    lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
    # Drop short UI-control lines and reaction counters.
    cleaned = []
    drop_after = False
    for ln in lines:
        if drop_after:
            break
        low = ln.lower()
        if ln in ("Like", "Comment", "Share", "Send", "إعجاب", "تعليق", "مشاركة", "إرسال"):
            drop_after = True
            continue
        if re.fullmatch(r"[\d.,KMBkmb]+\s*(?:reactions?|التفاعلات|تعليق(?:ات)?|مشاركة|comments?|shares?)?", ln):
            continue
        cleaned.append(ln)
    return "\n".join(cleaned[:25]).strip()  # cap at ~25 lines


def fetch_fb_posts(handle: str, limit: int = 5) -> dict:
    """Navigate to the FB page and extract up to `limit` recent posts."""
    if not FB_AVAILABLE:
        return {"error": "fb_not_configured", "posts": []}

    handle = (handle or "").strip().lstrip("@")
    if not handle:
        return {"error": "empty handle", "posts": []}

    with _DRIVER_LOCK:
        try:
            if not _ensure_session():
                return {"error": "facebook_login_failed", "posts": []}

            url = _page_url(handle)
            try:
                _DRIVER.get(url)
            except WebDriverException as e:
                return {"error": f"navigation: {e}", "posts": []}

            time.sleep(4)  # let the feed render

            # Scroll a few times to load more articles
            for _ in range(max(2, limit)):
                _DRIVER.execute_script("window.scrollBy(0, 1800);")
                time.sleep(1.8)

            try:
                articles = _DRIVER.find_elements(By.CSS_SELECTOR, 'div[role="article"]')
            except Exception:
                articles = []

            posts = []
            seen_texts = set()
            for art in articles:
                try:
                    raw = art.text or ""
                    if not _looks_like_post(raw):
                        continue
                    caption = _clean_caption(raw)
                    if not caption or caption[:80] in seen_texts:
                        continue
                    seen_texts.add(caption[:80])

                    # Try to find a permalink (timestamp link or "open story")
                    post_url = url
                    try:
                        link_el = art.find_element(By.CSS_SELECTOR, 'a[href*="/posts/"], a[href*="/permalink/"], a[href*="story.php"]')
                        href = link_el.get_attribute("href") or ""
                        if href:
                            post_url = href.split("?")[0]
                    except NoSuchElementException:
                        pass

                    # Try to find an image
                    image_urls = []
                    try:
                        for img in art.find_elements(By.CSS_SELECTOR, "img"):
                            src = img.get_attribute("src") or ""
                            if src.startswith("https://") and "scontent" in src and src not in image_urls:
                                image_urls.append(src)
                                if len(image_urls) >= 3:
                                    break
                    except Exception:
                        pass

                    posts.append({
                        "id": str(abs(hash(caption[:200])))[:18],
                        "username": handle,
                        "post_url": post_url,
                        "caption": caption,
                        "likes": 0, "retweets": 0, "comments": 0, "bookmarks": 0, "views": 0,
                        "image_urls": image_urls,
                        "video_urls": [],
                        "has_video": False,
                        "is_retweet": False,
                        "created_at": "",
                    })
                    if len(posts) >= limit:
                        break
                except Exception:
                    continue

            return {"posts": posts, "error": None}

        except WebDriverException as e:
            # Driver crashed — reset so the next call rebuilds it
            print(f"[fb_client] driver error, resetting: {e}")
            shutdown()
            return {"error": f"selenium: {e}", "posts": []}


def shutdown():
    """Clean up the driver (called on FastAPI shutdown)."""
    global _DRIVER, _LOGGED_IN
    with _DRIVER_LOCK:
        if _DRIVER is not None:
            try:
                _DRIVER.quit()
            except Exception:
                pass
            _DRIVER = None
            _LOGGED_IN = False
