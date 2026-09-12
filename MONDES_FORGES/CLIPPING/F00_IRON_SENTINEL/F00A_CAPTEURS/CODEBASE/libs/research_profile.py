"""Profils de recherche contextualisés pour F00_CAPTEURS.

Le profil est additif : les anciennes options --freshness restent valides.
La première version cible YouTube Shorts, le marché US et la niche meme.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HorizonSpec:
    key: str
    window_hours: int
    trend_days: int
    reddit_timeframe: str
    weights: dict[str, float]


HORIZONS = {
    "2h": HorizonSpec("2h", 2, 1, "hour", {
        "vues_youtube": 0.40, "tendance": 0.10, "fraicheur": 0.35,
        "demande": 0.05, "reddit": 0.10,
    }),
    "6h": HorizonSpec("6h", 6, 1, "day", {
        "vues_youtube": 0.35, "tendance": 0.15, "fraicheur": 0.30,
        "demande": 0.10, "reddit": 0.10,
    }),
    "12h": HorizonSpec("12h", 12, 1, "day", {
        "vues_youtube": 0.32, "tendance": 0.18, "fraicheur": 0.25,
        "demande": 0.12, "reddit": 0.13,
    }),
    "24h": HorizonSpec("24h", 24, 2, "day", {
        "vues_youtube": 0.30, "tendance": 0.20, "fraicheur": 0.20,
        "demande": 0.15, "reddit": 0.15,
    }),
    "3d": HorizonSpec("3d", 72, 3, "week", {
        "vues_youtube": 0.27, "tendance": 0.28, "fraicheur": 0.15,
        "demande": 0.18, "reddit": 0.12,
    }),
    "7d": HorizonSpec("7d", 168, 7, "week", {
        "vues_youtube": 0.25, "tendance": 0.30, "fraicheur": 0.10,
        "demande": 0.20, "reddit": 0.15,
    }),
    "30d": HorizonSpec("30d", 720, 30, "month", {
        "vues_youtube": 0.20, "tendance": 0.25, "fraicheur": 0.05,
        "demande": 0.25, "reddit": 0.25,
    }),
}

LEGACY_HORIZONS = {
    "brulant": HorizonSpec("legacy_brulant", 5, 7, "day", {
        "vues_youtube": 0.30, "tendance": 0.25, "fraicheur": 0.20,
        "demande": 0.15, "couverture": 0.10,
    }),
    "frais": HorizonSpec("legacy_frais", 24, 7, "week", {
        "vues_youtube": 0.30, "tendance": 0.25, "fraicheur": 0.20,
        "demande": 0.15, "couverture": 0.10,
    }),
}


def build_profile(*, horizon: str | None, platform: str | None,
                  market: str | None, niche: str | None,
                  niche_mode: str | None, mode: str | None,
                  freshness: str) -> dict:
    """Construit un profil sérialisable et garde le mode legacy explicite."""
    if horizon:
        if horizon not in HORIZONS:
            raise ValueError(f"horizon inconnu: {horizon} (2h|6h|12h|24h|3d|7d|30d)")
        spec = HORIZONS[horizon]
        legacy = False
    else:
        spec = LEGACY_HORIZONS.get(freshness, LEGACY_HORIZONS["brulant"])
        horizon = "6h" if freshness == "brulant" else "24h"
        legacy = True
    return {
        "horizon": horizon,
        "profile_id": f"{platform or 'youtube_shorts'}:{market or 'us_young_english'}:{niche_mode or mode or 'general'}:{horizon}",
        "platform": platform or "youtube_shorts",
        "market": market or "us_young_english",
        "niche": niche or "hot",
        "niche_mode": niche_mode or mode or "general",
        "mode": mode or "informatif",
        "window_hours": spec.window_hours,
        "trend_days": spec.trend_days,
        "reddit_timeframe": spec.reddit_timeframe,
        "weights": spec.weights,
        "legacy_compat": legacy,
    }


def profile_for_scoring(profile: dict) -> dict:
    """Normalise un profil externe avant injection dans le scoreur."""
    horizon = profile.get("horizon", "24h")
    if horizon in HORIZONS:
        spec = HORIZONS[horizon]
        return {**profile, "weights": profile.get("weights") or spec.weights,
                "window_hours": profile.get("window_hours", spec.window_hours)}
    return profile
