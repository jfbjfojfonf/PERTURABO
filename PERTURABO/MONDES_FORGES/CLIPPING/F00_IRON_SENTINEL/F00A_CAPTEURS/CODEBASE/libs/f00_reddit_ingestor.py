"""
reddit_ingestor.py — Senseur Reddit (F00_CAPTEURS, mode meme)
=============================================================
SIGNAL Reddit (ce qui est viral/discuté US) via le flux public JSON
(https://www.reddit.com/search.json?q=...&t=week&sort=top) sans clé.

Best-effort : si Reddit bloque (403/429), status fetch_failed — jamais
de levée. Les données renvoyées sont réelles (titre, sous-reddit, score,
commentaires, lien).
"""

import json
import re
import urllib.error
import urllib.parse
import urllib.request

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 " \
     "(KHTML, like Gecko) Chrome/125.0 Safari/537.36"

SEARCH_URL = "https://www.reddit.com/search.json"

TENSION_WORDS = ("why", "who", "what", "vs", "record", "worst", "best",
                 "crazy", "epic", "unreal", "steal", "respect", "awkward")


def _fetch(url: str, timeout: int = 20):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace"), None
    except urllib.error.HTTPError as e:
        return None, f"http_{e.code}"
    except urllib.error.URLError as e:
        return None, f"network_{e.reason}"
    except TimeoutError:
        return None, "timeout"


def _clean_selftext(text: str) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()[:300]


def scan(keywords: list[str], max_items: int = 10,
         timeframe: str = "week") -> dict:
    """Recherche Reddit triée par top sur la période.

    Retourne :
      {
        "signal": "reddit_viralite",
        "status": "ok" | "fetch_failed",
        "error": "...",
        "keywords": [...],
        "posts": [ {title, subreddit, score, num_comments, url, selftext}, ... ],
        "top_subreddits": [...],
        "demand_score": 0..100,
      }
    """
    q = " ".join(keywords[:6])
    params = urllib.parse.urlencode({
        "q": q, "sort": "top", "t": timeframe,
        "limit": max_items, "restrict_sr": "",
    })
    raw, err = _fetch(f"{SEARCH_URL}?{params}")
    if raw is None:
        return {
            "signal": "reddit_viralite", "status": "fetch_failed",
            "error": err, "keywords": keywords, "posts": [],
            "top_subreddits": [], "demand_score": None,
        }

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {
            "signal": "reddit_viralite", "status": "fetch_failed",
            "error": "json_decode", "keywords": keywords, "posts": [],
            "top_subreddits": [], "demand_score": None,
        }

    children = (data.get("data") or {}).get("children", []) or []
    posts = []
    for ch in children:
        p = ch.get("data") or {}
        if not p.get("title"):
            continue
        posts.append({
            "title": p.get("title", ""),
            "subreddit": p.get("subreddit", ""),
            "score": int(p.get("score", 0) or 0),
            "num_comments": int(p.get("num_comments", 0) or 0),
            "url": p.get("url", ""),
            "permalink": f"https://reddit.com{p.get('permalink', '')}",
            "selftext": _clean_selftext(p.get("selftext", "")),
            "created_utc": p.get("created_utc"),
        })

    top_subs = {}
    for p in posts:
        sub = p.get("subreddit") or "?"
        top_subs.setdefault(sub, {"posts": 0, "total_score": 0})
        top_subs[sub]["posts"] += 1
        top_subs[sub]["total_score"] += p.get("score", 0) or 0
    top_subreddits = sorted(
        top_subs.items(), key=lambda kv: kv[1]["total_score"], reverse=True)[:5]
    top_subreddits = [{"subreddit": s, **v} for s, v in top_subreddits]

    corpus = " ".join(p.get("title", "") for p in posts).lower()
    tension = sum(1 for w in TENSION_WORDS if w in corpus)
    demand = min(100, len(posts) * 8 + tension * 5)

    return {
        "signal": "reddit_viralite", "status": "ok", "error": None,
        "keywords": keywords, "posts": posts,
        "top_subreddits": top_subreddits, "demand_score": demand,
    }
