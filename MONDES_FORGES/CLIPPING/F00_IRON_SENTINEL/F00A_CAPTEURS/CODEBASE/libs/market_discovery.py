"""Moteur F00 de découverte de marché, avec barrières de production.

Règle centrale : un signal externe n'est jamais un candidat. Un candidat doit
être un contenu YouTube observé, pertinent pour le Démon/marché, compatible
avec la niche meme et suffisamment prouvé. Les résultats insuffisants restent
les signaux rejetés ou les observations, jamais des candidats artificiels.
"""
from __future__ import annotations

import hashlib
import re
from collections import Counter
from datetime import datetime, timezone
from typing import Callable

HORIZONS = {
    "2h": {"hours": 2, "timeframe": "day", "freshness": "brulant"},
    "6h": {"hours": 6, "timeframe": "day", "freshness": "brulant"},
    "12h": {"hours": 12, "timeframe": "day", "freshness": "frais"},
    "24h": {"hours": 24, "timeframe": "day", "freshness": "frais"},
    "3d": {"hours": 72, "timeframe": "week", "freshness": "frais"},
    "7d": {"hours": 168, "timeframe": "week", "freshness": "frais"},
    "30d": {"hours": 720, "timeframe": "month", "freshness": "frais"},
}

STOPWORDS = {
    "people", "living", "in", "the", "us", "usa", "united", "states",
    "interested", "who", "like", "likes", "playing", "play", "game",
    "fans", "audience", "and", "for", "with", "from", "youtube", "shorts",
    "age", "years", "year", "old", "residents", "interested", "target",
}
BLOCKED = {
    "election", "president", "politics", "political", "abortion", "war",
    "terrorism", "terrorist", "shooting", "racial", "religion", "violence",
    "death", "tragedy", "medical", "health", "diagnosis", "vaccine",
}
MEME_TERMS = {
    "meme", "memes", "funny", "humor", "humour", "comedy", "reaction",
    "reactions", "lol", "lmao", "wtf", "hilarious", "absurd", "cursed",
    "fails", "fail", "funniest", "skit", "parody", "satire", "pov",
    "bro", "caught", "exposed", "sus", "impostor", "troll", "rage",
    "edit", "clip", "clips", "viral", "challenge", "joke", "jokes",
    "awkward", "cringe", "plot", "twist", "be-like", "when", "daily",
}


def _tokens(text: str) -> list[str]:
    return [x.lower() for x in re.findall(r"[A-Za-z0-9][A-Za-z0-9'_-]{2,}", text or "")]


def _meaningful_tokens(text: str) -> set[str]:
    return {w for w in _tokens(text) if w not in STOPWORDS and len(w) >= 3}


def build_probe_queries(
    market: str,
    reference_channels: list[str] | None = None,
    reference_hashtags: list[str] | None = None,
    demon_hashtags: list[str] | None = None,
) -> list[str]:
    """Construit des sondes naturelles ; aucune sonde ne devient une preuve."""
    words = [w for w in _tokens(market) if w not in STOPWORDS]
    handles = re.findall(r"@([A-Za-z0-9_]{2,})", market or "")
    queries: list[str] = []
    # Les hashtags observés sont les ancres de territoire : ils passent avant
    # les variantes génériques afin de ne pas noyer la niche meme.
    for tag in (reference_hashtags or []) + (demon_hashtags or []):
        clean = tag.strip()
        if clean:
            queries.extend([clean, f"{clean} meme"])
    for channel in (reference_channels or []) + handles:
        clean = channel.lstrip("@").strip()
        if clean:
            queries.extend([f"@{clean}", f"{clean} meme", f"{clean} funny", f"{clean} Shorts"])
    if words:
        queries.extend([" ".join(words), " ".join(words) + " meme", " ".join(words) + " Shorts"])
    if not queries:
        queries.append(market.strip())
    return list(dict.fromkeys(q for q in queries if q.strip()))[:20]


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", " ", (text or "").lower()).strip()


def _candidate_key(text: str) -> str:
    words = [w for w in _norm(text).split() if w not in STOPWORDS]
    return " ".join(words[:10])


def _evidence_url(item: dict) -> str | None:
    return item.get("url") or item.get("permalink") or item.get("source_url")


def _youtube_items(yt: dict) -> list[dict]:
    """Retourne uniquement les résultats de recherche, jamais le trending global."""
    return list((yt.get("search") or {}).get("videos") or [])


def _is_meme_text(text: str, item: dict | None = None) -> bool:
    haystack = " ".join(
        [text or "", (item or {}).get("description", ""), " ".join((item or {}).get("hashtags", []) or [])]
    ).lower()
    words = set(_tokens(haystack))
    return bool(words & MEME_TERMS) or any(token in haystack for token in ("#meme", "#funny", "#comedy", "#reaction"))


def _extract_observed_candidates(probe_queries: list[str], yt: dict, sugg: dict,
                                 reddit: dict, trends: dict) -> list[dict]:
    """Crée des candidats uniquement à partir de vidéos YouTube observées.

    Suggest, Reddit et Trends enrichissent les preuves quand ils recoupent un
    titre YouTube ; ils ne peuvent plus créer un candidat à eux seuls.
    """
    videos = []
    for video in _youtube_items(yt):
        title = (video.get("title") or "").strip()
        if title:
            videos.append(video)
    raw = []
    for video in videos:
        key = _candidate_key(video.get("title", ""))
        if not key:
            continue
        raw.append({"text": video["title"], "kind": "youtube", "item": video, "key": key})

    def related_count(text: str, source_items: list[dict], field: str) -> int:
        wanted = _meaningful_tokens(text)
        count = 0
        for item in source_items:
            candidate_text = str(item.get(field, ""))
            if wanted and len(wanted & _meaningful_tokens(candidate_text)) >= 1:
                count += 1
        return count

    suggestions = [v for group in (sugg.get("keywords") or []) for v in (group.get("suggestions") or [])]
    reddit_items = list(reddit.get("posts") or [])
    trends_items = list((trends.get("global_trending_rss") or {}).get("trending") or [])
    grouped: dict[str, list[dict]] = {}
    for entry in raw:
        grouped.setdefault(entry["key"], []).append(entry)

    candidates = []
    for key, entries in grouped.items():
        youtube = [e["item"] for e in entries]
        views = [int(v.get("view_count", 0) or 0) for v in youtube]
        channels = {v.get("channel", "") for v in youtube if v.get("channel")}
        title = max((v.get("title", "") for v in youtube), key=len)
        urls = list(dict.fromkeys(u for u in (_evidence_url(v) for v in youtube) if u))
        suggestion_count = related_count(title, [{"value": x} for x in suggestions], "value")
        reddit_count = related_count(title, reddit_items, "title")
        trend_count = related_count(title, trends_items, "query")
        candidates.append({
            "candidate_id": "CAND-" + hashlib.sha1(key.encode()).hexdigest()[:8],
            "keyword": title[:120],
            "normalized_key": key,
            "evidence_urls": urls[:12],
            "evidence_types": ["youtube"] + (["suggest"] if suggestion_count else []) + (["reddit"] if reddit_count else []) + (["trends"] if trend_count else []),
            "youtube_video_count": len(youtube),
            "youtube_top_views": max(views or [0]),
            "youtube_total_views": sum(views),
            "reddit_post_count": reddit_count,
            "reddit_comments": 0,
            "suggestion_count": suggestion_count,
            "trend_count": trend_count,
            "channel_count": len(channels),
            "channel_names": sorted(channels),
            "observed_hashtags": sorted({tag for video in youtube for tag in (video.get("hashtags", []) or [])}),
            "observed_tags": sorted({tag for video in youtube for tag in (video.get("tags", []) or [])}),
            "observed": True,
            "meme_observed": _is_meme_text(title, youtube[0]),
        })
    return candidates


def _demon_map(yt: dict) -> list[dict]:
    videos = _youtube_items(yt)
    relevant = [v for v in videos if _is_meme_text(v.get("title", ""), v)]
    channels = Counter(v.get("channel") for v in relevant if v.get("channel"))
    demons = []
    for channel, count in channels.most_common(10):
        related = [v for v in relevant if v.get("channel") == channel]
        views = sum(int(v.get("view_count", 0) or 0) for v in related)
        if count < 2:
            continue
        demons.append({
            "demon_id": "DEMON-" + hashlib.sha1(channel.encode()).hexdigest()[:8],
            "type": "creator_or_channel",
            "identity": channel,
            "territory": [v.get("title", "") for v in related[:5]],
            "evidence_urls": [f"https://youtube.com/watch?v={v.get('video_id')}" for v in related if v.get("video_id")],
            "observed_video_count": count,
            "observed_views": views,
            "pressure_score": min(100, count * 12 + (views // 100000)),
            "status": "observed",
        })
    return demons


def _score_candidate(c: dict, horizon: str, demons: list[dict], market: str, reference_terms: str = "") -> dict:
    views_score = min(100, c["youtube_top_views"] / 10000)
    demand_score = min(100, c["suggestion_count"] * 15 + c["reddit_post_count"] * 10 + c.get("trend_count", 0) * 5)
    evidence_score = min(100, 35 + c["youtube_video_count"] * 15 + (15 if c["suggestion_count"] else 0) + (15 if c["reddit_post_count"] else 0))
    demon_pressure = min(100, c["channel_count"] * 15 + c["youtube_video_count"] * 8)
    saturation = min(100, demon_pressure * 0.7 + c["youtube_video_count"] * 5)
    market_terms = _meaningful_tokens(f"{market} {reference_terms}")
    title_terms = _meaningful_tokens(c["keyword"])
    handle_terms = {x.lower() for x in re.findall(r"@([A-Za-z0-9_]{2,})", market or "")}
    channel_names = {str(name).lower() for name in c.get("channel_names", [])}
    channel_match = any(handle in _norm(name).split() or handle in _norm(name) for handle in handle_terms for name in channel_names)
    anchor_hit = bool((market_terms - handle_terms) & title_terms) or bool(handle_terms & title_terms) or channel_match
    us_score = 70 if any(x in market.lower() for x in ("us", "usa", "united states", "american")) else 50
    meme_gate = bool(c.get("meme_observed"))
    relevance_gate = bool(anchor_hit)
    blue_score = max(0, min(100, demand_score * .35 + evidence_score * .30 + (100 - saturation) * .20 + (20 if relevance_gate else 0)))
    red_score = min(100, demand_score * .35 + views_score * .35 + demon_pressure * .20 + (10 if relevance_gate else 0))
    fit = 75 if meme_gate else 0
    confidence = min(100, evidence_score * .55 + (25 if c["evidence_urls"] else 0) + (20 if c["youtube_video_count"] else 0))
    if not meme_gate or not c["youtube_video_count"] or not relevance_gate or confidence < 55:
        camp = "desert"
    else:
        camp = "red" if red_score >= blue_score and demand_score >= 35 else ("blue" if blue_score >= 35 else "desert")
    c.update({
        "scores": {"demand": round(demand_score, 1), "youtube": round(views_score, 1), "us_native": us_score,
                   "demon_pressure": round(demon_pressure, 1), "saturation": round(saturation, 1),
                   "blue_ocean": round(blue_score, 1), "red_ocean": round(red_score, 1),
                   "meme_fit": fit, "confidence": round(confidence, 1)},
        "gates": {"meme": "pass" if meme_gate else "block", "youtube_evidence": "pass" if c["youtube_video_count"] else "block",
                  "market_relevance": "pass" if relevance_gate else "block", "confidence": "pass" if confidence >= 55 else "block"},
        "ocean": camp,
        "horizon": horizon,
        "source_status": "observed_only",
        "safety_gate": "block" if set(_tokens(c["keyword"])) & BLOCKED else "pass",
        "decision": "warsmith_review",
    })
    return c


def _deduplicate(candidates: list[dict]) -> tuple[list[dict], list[dict]]:
    kept, removed = [], []
    seen = {}
    for c in sorted(candidates, key=lambda x: (x.get("youtube_total_views", 0), len(x.get("evidence_types", []))), reverse=True):
        key = c["normalized_key"]
        if key in seen:
            c["status"] = "duplicate"
            c["duplicate_of"] = seen[key]
            removed.append(c)
        else:
            c["status"] = "unique"
            seen[key] = c["candidate_id"]
            kept.append(c)
    return kept, removed


def discover_market(market: str, platform: str, horizon: str, *,
                    rss_scan: Callable, trends_scan: Callable,
                    youtube_scan: Callable, suggestions_scan: Callable,
                    reddit_scan: Callable, max_items: int = 10,
                    probe_queries: list[str] | None = None,
                    question_plan: list[dict] | None = None,
                    reference_channels: list[str] | None = None,
                    reference_hashtags: list[str] | None = None,
                    demon_hashtags: list[str] | None = None) -> dict:
    if not market.strip():
        raise ValueError("market requis")
    if platform != "youtube_shorts":
        raise ValueError("plateforme non supportée: youtube_shorts uniquement")
    if horizon not in HORIZONS:
        raise ValueError("horizon requis: 2h|6h|12h|24h|3d|7d|30d")
    spec = HORIZONS[horizon]
    probes = list(dict.fromkeys(probe_queries or build_probe_queries(market, reference_channels, reference_hashtags, demon_hashtags)))[:20]
    if not probes:
        raise ValueError("aucune requête de prospection valide")
    rss = rss_scan(probes, freshness=spec["freshness"], max_items=max_items)
    trends = trends_scan(probes)
    yt = youtube_scan(probes, max_results=20)
    sugg = suggestions_scan(probes)
    reddit = reddit_scan(probes, max_items=max_items, timeframe=spec["timeframe"])
    demons = _demon_map(yt)
    raw = _extract_observed_candidates(probes, yt, sugg, reddit, trends)
    generic_anchor_terms = {"funny", "funnymemes", "meme", "memes", "shorts"}
    contextual_terms = [t for t in (reference_hashtags or []) + (demon_hashtags or [])
                        if _norm(t).strip() not in generic_anchor_terms]
    reference_terms = " ".join(contextual_terms)
    scored = [_score_candidate(c, horizon, demons, market, reference_terms) for c in raw]
    unique, removed = _deduplicate(scored)
    eligible = [c for c in unique if c["safety_gate"] == "pass" and c["ocean"] != "desert"]
    rejected = [c for c in unique if c not in eligible]
    eligible.sort(key=lambda c: max(c["scores"]["red_ocean"], c["scores"]["blue_ocean"]), reverse=True)
    for index, c in enumerate(eligible[:30], 1):
        c["rank"] = index
    red = [c for c in eligible[:30] if c["ocean"] == "red"]
    blue = [c for c in eligible[:30] if c["ocean"] == "blue"]
    return {
        "discovery_id": "DISC-" + hashlib.sha1(f"{market}|{platform}|{horizon}".encode()).hexdigest()[:10],
        "discovered_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "market_input": {"market": market, "platform": platform, "horizon": horizon, "language": "en-US", "production_niche": "meme"},
        "research_profile": {"horizon_hours": spec["hours"], "probe_queries": probes, "candidate_limit": 30, "candidate_policy": "observed_youtube_meme_only"},
        "demon_map": demons,
        "candidate_clusters": {"unique_count": len(unique), "removed_duplicates": removed, "rejected_signals": rejected},
        "candidates": eligible[:30],
        "red_candidates": red,
        "blue_candidates": blue,
        "availability": {"requested": 30, "observed_eligible": len(eligible), "rejected": len(rejected), "invented": 0, "quota_filled": len(eligible) >= 30},
        "signal_payload": {"rss": rss, "trends": trends, "youtube": yt, "suggestions": sugg, "reddit": reddit},
        "validation": {"state": "warsmith_review", "premium_used": bool(question_plan), "anti_invention": "pass", "next_frigate_blocked": True},
        "question_plan": question_plan or [],
    }


def build_packs(candidates: list[dict], max_packs: int = 5) -> list[dict]:
    """Propose des paires distinctes avec une ancre et un contraste partagé."""
    packs = []
    for anchor in candidates:
        for contrast in candidates:
            if anchor["candidate_id"] >= contrast["candidate_id"]:
                continue
            if anchor.get("normalized_key") == contrast.get("normalized_key"):
                continue
            shared = set(anchor.get("normalized_key", "").split()) & set(contrast.get("normalized_key", "").split())
            if not shared or anchor.get("ocean") == contrast.get("ocean") == "desert":
                continue
            packs.append({
                "pack_id": "PACK-" + hashlib.sha1((anchor["candidate_id"] + contrast["candidate_id"]).encode()).hexdigest()[:8],
                "words": [anchor["keyword"], contrast["keyword"]],
                "anchor_candidate_id": anchor["candidate_id"],
                "contrast_candidate_id": contrast["candidate_id"],
                "ocean_mix": [anchor.get("ocean"), contrast.get("ocean")],
                "anti_cannibalization": "pending_review",
                "decision": "warsmith_review",
            })
            if len(packs) >= max_packs:
                return packs
    return packs


def allocate_angles(candidates: list[dict], total: int, blue: int | None = None,
                    red: int | None = None) -> dict:
    if total < 1:
        raise ValueError("total angles doit être positif")
    blue_available = sum(1 for c in candidates if c.get("ocean") == "blue")
    red_available = sum(1 for c in candidates if c.get("ocean") == "red")
    if blue is None and red is None:
        blue = total // 2
        red = total - blue
    elif blue is None:
        red = red or 0
        blue = total - red
    elif red is None:
        blue = blue or 0
        red = total - blue
    if blue + red != total:
        raise ValueError("allocation angles incohérente")
    return {
        "requested_total": total, "requested_blue": blue, "requested_red": red,
        "available_blue_candidates": blue_available, "available_red_candidates": red_available,
        "status": "pass" if blue <= blue_available and red <= red_available else "insufficient_candidates",
        "decision": "warsmith_review",
    }
