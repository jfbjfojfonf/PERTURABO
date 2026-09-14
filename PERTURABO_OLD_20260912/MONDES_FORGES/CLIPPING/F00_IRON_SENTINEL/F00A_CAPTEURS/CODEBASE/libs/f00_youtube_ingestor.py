"""
youtube_ingestor.py — Senseur YouTube Data API v3 (F00_CAPTEURS)
================================================================
SIGNAL 3 (vues réelles) via la clé YouTube (CONTRACTS/youtube_secrets.json).
Trois endpoints :
  - videos_statistics : vues/likes/commentaires d'une vidéo par ID
  - search            : recherche par mot-clé triée par vues (order=viewCount)
  - trending          : chart=mostPopular (global ou par catégorie)

Quota : 10 000 unités/jour (search = 100 unités, videos.statistics = 1).
Best-effort : jamais de levée, tout échec -> status fetch_failed.
"""

import json
import os
import urllib.error
import urllib.parse
import urllib.request

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# libs/ -> CODEBASE -> CAPTEURS -> CLIPPING (les CONTRACTS sont au niveau CLIPPING)
_CLIPPING_DIR = os.path.dirname(os.path.dirname(os.path.dirname(_SCRIPT_DIR)))

SECRETS_PATH = os.path.join(_CLIPPING_DIR, "CONTRACTS", "youtube_secrets.json")
BASE_URL = "https://www.googleapis.com/youtube/v3"


def _load_key() -> str | None:
    """Lit la clé YouTube depuis youtube_secrets.json (gitignored)."""
    if not os.path.exists(SECRETS_PATH):
        return None
    try:
        with open(SECRETS_PATH, "r", encoding="utf-8") as f:
            return (json.load(f) or {}).get("key")
    except (OSError, ValueError):
        return None


def _api_key_available() -> bool:
    return bool(_load_key())


def _get(path: str, params: dict, timeout: int = 20):
    """GET Google API. Retourne (dict | None, error_reason)."""
    key = _load_key()
    if not key:
        return None, "no_youtube_key"
    params = dict(params)
    params["key"] = key
    url = f"{BASE_URL}{path}?{urllib.parse.urlencode(params)}"
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "PERTURABO-F00/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8")), None
    except urllib.error.HTTPError as e:
        try:
            body = json.loads(e.read().decode("utf-8", errors="replace"))
            msg = body.get("error", {}).get("message", "")
        except ValueError:
            msg = ""
        return None, f"http_{e.code}: {msg[:120]}"
    except urllib.error.URLError as e:
        return None, f"network_{e.reason}"
    except TimeoutError:
        return None, "timeout"


def _parse_stats(data: dict) -> dict:
    items = (data or {}).get("items", []) or []
    if not items:
        return {}
    it = items[0]
    sn = it.get("snippet", {})
    st = it.get("statistics", {})
    return {
        "video_id": it.get("id"),
        "title": sn.get("title", ""),
        "channel": sn.get("channelTitle", ""),
        "published_at": sn.get("publishedAt", ""),
        "view_count": int(st.get("viewCount", 0) or 0),
        "like_count": int(st.get("likeCount", 0) or 0),
        "comment_count": int(st.get("commentCount", 0) or 0),
    }


def video_stats(video_id: str) -> dict:
    """Vues d'une vidéo par ID. Retourne {} si introuvable."""
    data, err = _get("/videos", {
        "part": "statistics,snippet",
        "id": video_id,
    })
    if data is None:
        return {"video_id": video_id, "status": "fetch_failed", "error": err}
    stats = _parse_stats(data)
    stats["status"] = "ok" if stats else "not_found"
    return stats


def search(keywords: list[str], max_results: int = 8,
           freshness_days: int = 1) -> dict:
    """Recherche multi-sondes, triée par vues, avec preuves observées.

    Chaque sonde est envoyée séparément : concaténer des hashtags et des
    questions dans un seul ``q`` rend la recherche YouTube trop restrictive.
    Les résultats sont ensuite dédupliqués avant la récupération des stats.
    """
    probes = list(dict.fromkeys(k.strip() for k in keywords if k and k.strip()))[:12]
    if not probes:
        return {"status": "ok", "error": None, "query": "", "videos": []}
    search_rows = []
    errors = []
    for q in probes:
        data, err = _get("/search", {
            "part": "snippet",
            "q": q,
            "type": "video",
            "videoDuration": "short",
            "regionCode": "US",
            "relevanceLanguage": "en",
            "order": "viewCount",
            "maxResults": min(max_results, 8),
            "publishedAfter": f"{_days_ago_iso(freshness_days)}",
        })
        if data is None:
            errors.append(f"{q}: {err}")
            continue
        search_rows.extend((data or {}).get("items", []) or [])

    ids = list(dict.fromkeys(
        it.get("id", {}).get("videoId", "") for it in search_rows if it.get("id", {}).get("videoId")
    ))
    videos = []
    if ids:
        stats_data, stats_err = _get("/videos", {
            "part": "statistics,snippet,contentDetails",
            "id": ",".join(ids[:50]),
        })
        if stats_data is None:
            errors.append(f"stats: {stats_err}")
        for it in ((stats_data or {}).get("items", []) or []):
            sn = it.get("snippet", {})
            st = it.get("statistics", {})
            cd = it.get("contentDetails", {})
            title = sn.get("title", "")
            description = sn.get("description", "")
            hashtags = sorted(set(__import__("re").findall(r"#[A-Za-z0-9_]+", f"{title} {description}")))
            videos.append({
                "video_id": it.get("id"),
                "url": f"https://youtube.com/watch?v={it.get('id')}",
                "title": title,
                "description": description,
                "channel": sn.get("channelTitle", ""),
                "published_at": sn.get("publishedAt", ""),
                "duration": cd.get("duration", ""),
                "tags": sn.get("tags", []) or [],
                "hashtags": hashtags,
                "view_count": int(st.get("viewCount", 0) or 0),
                "like_count": int(st.get("likeCount", 0) or 0),
                "comment_count": int(st.get("commentCount", 0) or 0),
            })
    videos.sort(key=lambda v: v.get("view_count", 0), reverse=True)
    return {
        "status": "ok" if not errors or videos else "fetch_failed",
        "error": "; ".join(errors[:3]) if errors else None,
        "query": " | ".join(probes),
        "probes": probes,
        "videos": videos,
    }


def trending(max_results: int = 10, category_id: str | None = None) -> dict:
    """Vidéos tendances réelles (chart=mostPopular)."""
    params = {
        "part": "statistics,snippet",
        "chart": "mostPopular",
        "maxResults": max_results,
    }
    if category_id:
        params["videoCategoryId"] = category_id
    data, err = _get("/videos", params)
    if data is None:
        return {"status": "fetch_failed", "error": err, "videos": []}
    videos = []
    for it in ((data or {}).get("items", []) or []):
        sn = it.get("snippet", {})
        st = it.get("statistics", {})
        videos.append({
            "video_id": it.get("id"),
            "title": sn.get("title", ""),
            "channel": sn.get("channelTitle", ""),
            "published_at": sn.get("publishedAt", ""),
            "view_count": int(st.get("viewCount", 0) or 0),
            "like_count": int(st.get("likeCount", 0) or 0),
            "comment_count": int(st.get("commentCount", 0) or 0),
        })
    return {"status": "ok", "error": None, "videos": videos}


def scan(keywords: list[str], max_results: int = 8) -> dict:
    """Signal YouTube complet pour F00 : recherche + tendances globales."""
    if not _api_key_available():
        return {
            "signal": "vues_youtube",
            "status": "no_youtube_key",
            "error": f"clé absente: {SECRETS_PATH}",
            "search": {},
            "trending": {},
        }
    return {
        "signal": "vues_youtube",
        "status": "ok",
        "search": search(keywords, max_results=max_results),
        "trending": trending(max_results=8),
    }


def _days_ago_iso(days: int) -> str:
    import datetime
    d = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days)
    return d.strftime("%Y-%m-%dT%H:%M:%SZ")
