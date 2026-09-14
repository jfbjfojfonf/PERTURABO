"""
libs/transcript_loader.py — Chargement des transcripts des assets (F03_SOURCE_HUNTER)
=====================================================================================

Charge les transcripts produits par F01_SCOUT (libs/scribe.py) depuis
ARCHIVUM/campaign/transcripts/ et les associe aux assets du specimen.

Convention de nommage F01 : ARCHIVUM/campaign/transcripts/transcript_<video_id>.json
(chaque transcript : {video_id, url, transcribed_at, segments[{start, duration, text}]})

Usage:
  from transcript_loader import TranscriptLoader
  loader = TranscriptLoader(campaign_dir)
  segments = loader.segments_for_asset(asset)
"""

import json
import os
import re


def _extract_video_id(url: str) -> str | None:
    if not url:
        return None
    m = re.search(r"(?:v=|youtu\.be/|shorts/)([A-Za-z0-9_-]{11})", url)
    return m.group(1) if m else None


class TranscriptLoader:
    """Charge et indexe les transcripts de la campagne (strict-source)."""

    def __init__(self, campaign_dir: str):
        self.transcripts_dir = os.path.join(campaign_dir, "transcripts")
        self._index = None

    def _build_index(self) -> dict:
        """Index video_id -> chemin transcript (scan 1 seule fois)."""
        if self._index is not None:
            return self._index
        index = {}
        if os.path.isdir(self.transcripts_dir):
            for name in os.listdir(self.transcripts_dir):
                m = re.match(r"transcript_([A-Za-z0-9_-]{11})\.json$", name)
                if m:
                    index[m.group(1)] = os.path.join(self.transcripts_dir, name)
        self._index = index
        return index

    def available(self) -> bool:
        return bool(self._build_index())

    def transcript_for_asset(self, asset: dict) -> dict | None:
        """Transcript complet de l'asset (None si indisponible)."""
        video_id = _extract_video_id(asset.get("url") or "")
        if not video_id:
            return None
        path = self._build_index().get(video_id)
        if not path:
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return None

    def segments_for_asset(self, asset: dict) -> list[dict]:
        """Segments [start, duration, text] du transcript (vide si absents)."""
        transcript = self.transcript_for_asset(asset)
        if not transcript:
            return []
        return transcript.get("segments", [])
