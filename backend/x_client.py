# =============================================================
# Rasd App — X (Twitter) Client
# =============================================================
# Fetches the latest tweets for a public account using X's
# guest token + public GraphQL endpoints. NO personal cookies.
#
# - Guest token cached for ~3 hours
# - Per-account result cache (15 min)
# - Soft rate limiting (0.3s between requests)
# - Returns a normalized {posts: [...]} structure or {error: "..."}
# =============================================================

import json
import os
import re
import threading
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

import requests

# Public web-client bearer token (NOT personal — same value the X website uses).
BEARER_TOKEN = (
    "AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D"
    "1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA"
)

# Optional personal cookies — read ONLY from env vars (never hardcode!).
# When set, the timeline is real chronological tweets. When missing, X falls
# back to a "highlights" set which is mostly old/random tweets — usable but
# not what most monitoring use-cases want.
AUTH_TOKEN = os.environ.get("X_AUTH_TOKEN", "").strip()
CT0        = os.environ.get("X_CT0", "").strip()
USE_COOKIES = bool(AUTH_TOKEN and CT0)

if not USE_COOKIES:
    print("[x_client] WARNING: X_AUTH_TOKEN / X_CT0 env vars not set.")
    print("[x_client] Falling back to guest token (X will return 'highlights' only).")
    print("[x_client] See README.md to enable real chronological timeline.")

GRAPHQL = "https://api.x.com/graphql"
USER_BY_SCREEN_NAME_ID = "G3KGOASz96M-Qu0nwmGXNg"
USER_TWEETS_ID         = "E3opETHurmVJflFsUBVuUQ"

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)

# ---------------------- guest token ----------------------
_GUEST_TOKEN = None
_GUEST_AT = 0.0
_GUEST_TTL = 3 * 3600
_TOKEN_LOCK = threading.Lock()


def get_guest_token(force=False):
    global _GUEST_TOKEN, _GUEST_AT
    with _TOKEN_LOCK:
        if not force and _GUEST_TOKEN and (time.time() - _GUEST_AT) < _GUEST_TTL:
            return _GUEST_TOKEN
        try:
            r = requests.post(
                "https://api.x.com/1.1/guest/activate.json",
                headers={"Authorization": f"Bearer {BEARER_TOKEN}", "User-Agent": UA},
                timeout=15,
            )
            if r.status_code == 200:
                tok = r.json().get("guest_token")
                if tok:
                    _GUEST_TOKEN = tok
                    _GUEST_AT = time.time()
                    return tok
        except Exception as e:
            print(f"[x_client] guest token error: {e}")
        return None


def _session():
    s = requests.Session()
    headers = {
        "Authorization": f"Bearer {BEARER_TOKEN}",
        "User-Agent": UA,
        "x-twitter-active-user": "yes",
        "x-twitter-client-language": "en",
        "Origin": "https://x.com",
        "Referer": "https://x.com/",
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Content-Type": "application/json",
    }
    if USE_COOKIES:
        headers["x-csrf-token"] = CT0
        headers["x-twitter-auth-type"] = "OAuth2Session"
        s.cookies.set("auth_token", AUTH_TOKEN, domain=".x.com")
        s.cookies.set("ct0", CT0, domain=".x.com")
    else:
        headers["x-guest-token"] = get_guest_token() or ""
    s.headers.update(headers)
    return s


# ---------------------- rate limiting ----------------------
_LAST = 0.0
_LAST_LOCK = threading.Lock()
_MIN_DELAY = 0.3


def _throttle():
    global _LAST
    with _LAST_LOCK:
        gap = time.time() - _LAST
        if gap < _MIN_DELAY:
            time.sleep(_MIN_DELAY - gap)
        _LAST = time.time()


# ---------------------- cache ----------------------
_USER_ID_CACHE = {}          # screen_name -> (timestamp, rest_id)
_USER_ID_TTL = 6 * 3600      # 6 hours
_TWEETS_CACHE = {}           # screen_name|limit -> (timestamp, payload)
_TWEETS_TTL = 900            # 15 min


def _cache_get(store, key, ttl):
    entry = store.get(key)
    if not entry:
        return None
    ts, val = entry
    if time.time() - ts > ttl:
        store.pop(key, None)
        return None
    return val


def _cache_set(store, key, val):
    store[key] = (time.time(), val)


# ---------------------- helpers ----------------------
def _resolve_user_id(screen_name):
    cached = _cache_get(_USER_ID_CACHE, screen_name.lower(), _USER_ID_TTL)
    if cached:
        return cached

    variables = {"screen_name": screen_name, "withSafetyModeUserFields": True}
    features = {
        "hidden_profile_subscriptions_enabled": True,
        "responsive_web_graphql_exclude_directive_enabled": True,
        "verified_phone_label_enabled": False,
        "subscriptions_verification_info_is_identity_verified_enabled": True,
        "subscriptions_verification_info_verified_since_enabled": True,
        "highlights_tweets_tab_ui_enabled": True,
        "responsive_web_twitter_article_notes_tab_enabled": True,
        "subscriptions_feature_can_gift_premium": True,
        "creator_subscriptions_tweet_preview_api_enabled": True,
        "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
        "responsive_web_graphql_timeline_navigation_enabled": True,
    }
    field_toggles = {"withAuxiliaryUserLabels": False}
    url = (
        f"{GRAPHQL}/{USER_BY_SCREEN_NAME_ID}/UserByScreenName"
        f"?variables={quote(json.dumps(variables))}"
        f"&features={quote(json.dumps(features))}"
        f"&fieldToggles={quote(json.dumps(field_toggles))}"
    )
    _throttle()
    try:
        r = _session().get(url, timeout=20)
        if r.status_code != 200:
            return None
        data = r.json()
        result = data.get("data", {}).get("user", {}).get("result", {})
        typename = result.get("__typename")
        if typename == "UserUnavailable":
            return "_unavailable_"
        rest_id = result.get("rest_id")
        if rest_id:
            _cache_set(_USER_ID_CACHE, screen_name.lower(), rest_id)
            return rest_id
    except Exception as e:
        print(f"[x_client] resolve user error for @{screen_name}: {e}")
    return None


_DATE_FILTERS = {
    "24h":  timedelta(hours=24),
    "3d":   timedelta(days=3),
    "7d":   timedelta(days=7),
    "30d":  timedelta(days=30),
    "90d":  timedelta(days=90),
    "all":  None,
}


def _within_filter(created_at_iso, df):
    if df not in _DATE_FILTERS or _DATE_FILTERS[df] is None:
        return True
    try:
        dt = datetime.fromisoformat(created_at_iso.replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - dt) <= _DATE_FILTERS[df]
    except Exception:
        return True


def _parse_x_date(s):
    # "Sat May 17 21:12:43 +0000 2026" -> ISO
    try:
        dt = datetime.strptime(s, "%a %b %d %H:%M:%S %z %Y")
        return dt.isoformat()
    except Exception:
        return s


def _normalize_tweet(legacy, screen_name):
    text = legacy.get("full_text") or legacy.get("text") or ""
    # Drop trailing t.co media link only when there's an attached media
    media = (legacy.get("entities") or {}).get("media") or []
    if media:
        text = re.sub(r"\s*https://t\.co/\w+\s*$", "", text).rstrip()

    images, videos = [], []
    for m in media:
        if m.get("type") == "photo":
            url = m.get("media_url_https")
            if url:
                images.append(url)
        elif m.get("type") in ("video", "animated_gif"):
            variants = (m.get("video_info") or {}).get("variants") or []
            best = None
            best_br = -1
            for v in variants:
                if v.get("content_type") == "video/mp4":
                    br = v.get("bitrate", 0)
                    if br > best_br:
                        best_br = br
                        best = v.get("url")
            if best:
                videos.append(best)

    tid = legacy.get("id_str") or str(legacy.get("id") or "")
    return {
        "id": tid,
        "username": screen_name,
        "post_url": f"https://x.com/{screen_name}/status/{tid}" if tid else "",
        "caption": text,
        "likes":     int(legacy.get("favorite_count") or 0),
        "retweets":  int(legacy.get("retweet_count")  or 0),
        "comments":  int(legacy.get("reply_count")    or 0),
        "bookmarks": int(legacy.get("bookmark_count") or 0),
        "views":     0,  # filled below from `views` field if present
        "image_urls": images,
        "video_urls": videos,
        "has_video": bool(videos),
        "is_retweet": bool(legacy.get("retweeted_status_result")),
        "created_at": _parse_x_date(legacy.get("created_at") or ""),
    }


def fetch_user_tweets(screen_name, limit=5, date_filter="7d"):
    """Return latest original posts (excluding pure retweets) for @screen_name."""
    screen_name = screen_name.strip().lstrip("@")
    if not screen_name:
        return {"error": "empty username", "posts": []}

    cache_key = f"{screen_name.lower()}|{limit}|{date_filter}"
    cached = _cache_get(_TWEETS_CACHE, cache_key, _TWEETS_TTL)
    if cached:
        return cached

    rest_id = _resolve_user_id(screen_name)
    if rest_id == "_unavailable_":
        payload = {"error": "account unavailable", "posts": []}
        _cache_set(_TWEETS_CACHE, cache_key, payload)
        return payload
    if not rest_id:
        payload = {"error": "could not resolve user", "posts": []}
        # Don't cache resolve failures for long — they're often transient
        return payload

    # Ask for a bit more than `limit` to leave room for filtering retweets out
    count = max(limit * 3, 20)
    variables = {
        "userId": rest_id,
        "count": count,
        "includePromotedContent": False,
        "withQuickPromoteEligibilityTweetFields": False,
        "withVoice": False,
        "withV2Timeline": True,
    }
    features = {
        "rweb_lists_timeline_redesign_enabled": True,
        "responsive_web_graphql_exclude_directive_enabled": True,
        "verified_phone_label_enabled": False,
        "creator_subscriptions_tweet_preview_api_enabled": True,
        "responsive_web_graphql_timeline_navigation_enabled": True,
        "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
        "tweetypie_unmention_optimization_enabled": True,
        "responsive_web_edit_tweet_api_enabled": True,
        "graphql_is_translatable_rweb_tweet_is_translatable_enabled": True,
        "view_counts_everywhere_api_enabled": True,
        "longform_notetweets_consumption_enabled": True,
        "responsive_web_twitter_article_tweet_consumption_enabled": False,
        "tweet_awards_web_tipping_enabled": False,
        "freedom_of_speech_not_reach_fetch_enabled": True,
        "standardized_nudges_misinfo": True,
        "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": True,
        "longform_notetweets_rich_text_read_enabled": True,
        "longform_notetweets_inline_media_enabled": True,
        "responsive_web_media_download_video_enabled": False,
        "responsive_web_enhance_cards_enabled": False,
    }
    url = (
        f"{GRAPHQL}/{USER_TWEETS_ID}/UserTweets"
        f"?variables={quote(json.dumps(variables))}"
        f"&features={quote(json.dumps(features))}"
    )
    _throttle()
    try:
        r = _session().get(url, timeout=25)
        if r.status_code == 429:
            return {"error": "rate limited by X, try again later", "posts": []}
        if r.status_code != 200:
            return {"error": f"http {r.status_code}", "posts": []}
        data = r.json()
    except Exception as e:
        return {"error": f"network: {e}", "posts": []}

    posts = []
    try:
        instructions = (
            data.get("data", {})
                .get("user", {})
                .get("result", {})
                .get("timeline_v2", {})
                .get("timeline", {})
                .get("instructions", [])
        )
        entries = []
        for ins in instructions:
            if ins.get("type") == "TimelineAddEntries":
                entries = ins.get("entries", [])
                break

        for entry in entries:
            content = entry.get("content", {}) or {}
            item = content.get("itemContent") or {}
            if item.get("itemType") != "TimelineTweet":
                continue
            tweet_res = (item.get("tweet_results") or {}).get("result") or {}
            if tweet_res.get("__typename") == "TweetWithVisibilityResults":
                tweet_res = tweet_res.get("tweet") or {}
            legacy = tweet_res.get("legacy")
            if not legacy:
                continue

            # Skip pure retweets (retweeted by user, not authored)
            if legacy.get("retweeted_status_result"):
                continue

            normalized = _normalize_tweet(legacy, screen_name)
            views_count = tweet_res.get("views", {}).get("count")
            if views_count:
                try:
                    normalized["views"] = int(views_count)
                except (TypeError, ValueError):
                    pass

            if not _within_filter(normalized["created_at"], date_filter):
                continue

            posts.append(normalized)
            if len(posts) >= limit:
                break
    except Exception as e:
        print(f"[x_client] parse error for @{screen_name}: {e}")

    payload = {"posts": posts, "error": None}
    _cache_set(_TWEETS_CACHE, cache_key, payload)
    return payload
