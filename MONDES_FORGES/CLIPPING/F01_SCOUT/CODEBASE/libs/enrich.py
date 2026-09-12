"""
libs/enrich.py — Enrichissement métadonnées des assets (F01_SCOUT)
==================================================================

Enrichit les assets avec yt-dlp --dump-json quand disponible.
Fonctionne en mode "dry" (sans yt-dlp) pour les assets non-vidéo (podcast, doc)
ou quand yt-dlp n'est pas installé — le squelette reste exploitable par l'IRON.

Usage:
  from enrich import enrich_asset
  enriched = enrich_asset(asset, yt_dlp_available=True)
"""

import json
import os
import subprocess
from datetime import datetime, timezone


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def yt_dlp_available() -> bool:
    try:
        result = subprocess.run(["yt-dlp", "--version"], capture_output=True, text=True, timeout=15)
        return result.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def enrich_asset(asset: dict, use_yt_dlp: bool = None) -> dict:
    """Enrichit un asset avec yt-dlp --dump-json (vidéo) ou en mode dry."""
    if use_yt_dlp is None:
        use_yt_dlp = yt_dlp_available() and asset.get("type") in ("video_long", "stream")

    enriched = dict(asset)
    enriched["metrics_extracted"] = {}
    enriched["enriched_at"] = now_iso()

    if not use_yt_dlp:
        return enriched

    try:
        result = subprocess.run(
            ["yt-dlp", "--dump-json", "--no-warnings", "--skip-download",
             "--no-playlist", asset["url"]],
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode != 0:
            enriched["metrics_extracted"]["yt_dlp_error"] = (result.stderr or "").strip()[:500]
            return enriched
        data = json.loads(result.stdout)
        enriched["duration_sec"] = data.get("duration")
        enriched["title"] = data.get("title")
        enriched["channel"] = data.get("channel")
        enriched["thumbnail"] = data.get("thumbnail")
        enriched["metrics_extracted"] = {
            "view_count": data.get("view_count"),
            "like_count": data.get("like_count"),
            "comment_count": data.get("comment_count"),
            "upload_date": data.get("upload_date"),
            "channel_follower_count": data.get("channel_follower_count"),
            "channel_id": data.get("channel_id"),
        }
    except (OSError, json.JSONDecodeError, subprocess.TimeoutExpired) as e:
        enriched["metrics_extracted"]["yt_dlp_error"] = str(e)[:500]

    return enriched


def compute_outlier_score(view_count, baseline) -> float | None:
    """outlier_score = view_count / baseline (channel_shorts_baseline ou subs)."""
    try:
        v = int(view_count or 0)
        b = int(baseline or 0)
    except (TypeError, ValueError):
        return None
    if b <= 0:
        return None
    return round(v / b, 2)
