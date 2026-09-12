"""
libs/scribe.py — Transcription des vidéos longues (F01_SCOUT)
==============================================================

Extrait le transcript d'une vidéo via youtube-transcript-api (fallback)
ou yt-dlp (sous-titres auto). Sauvegarde dans ARCHIVUM/campaign/.

En mode "dry" (dépendances absentes), retourne un transcript vide
avec status "UNAVAILABLE" — l'IRON pourra quand même analyser le
specimen via les métadonnées.

Usage:
  from scribe import get_transcript
  result = get_transcript(url, video_id, dest_dir)
"""

import json
import os
import re
import subprocess
from datetime import datetime, timezone


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _extract_video_id(url: str) -> str | None:
    m = re.search(r"(?:v=|youtu\.be/|shorts/)([A-Za-z0-9_-]{11})", url)
    return m.group(1) if m else None


def get_transcript(url: str, dest_dir: str, languages: list[str] = None) -> dict:
    """Tente la transcription (youtube-transcript-api -> yt-dlp -> dry)."""
    if languages is None:
        languages = ["en", "en-US", "fr"]

    video_id = _extract_video_id(url)
    if not video_id:
        return {"status": "UNAVAILABLE", "error": "video_id non extrait", "transcript": []}

    transcript = None
    error = None

    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        api = YouTubeTranscriptApi()
        try:
            transcript = api.fetch(video_id, languages=languages)
        except Exception:
            transcript = api.fetch(video_id)
        transcript = [
            {"start": float(seg.start), "duration": float(seg.duration), "text": seg.text}
            for seg in transcript
        ]
    except ImportError:
        error = "youtube-transcript-api non installé"
    except Exception as e:
        error = f"youtube-transcript-api échoué: {e}"

    if not transcript and not error:
        try:
            result = subprocess.run(
                ["yt-dlp", "--skip-download", "--no-warnings", "--write-auto-subs",
                 "--sub-langs", "en.*,fr.*", "--sub-format", "json3",
                 "--write-subs", "-o", os.path.join(dest_dir, "subs", "%(id)s"),
                 url],
                capture_output=True, text=True, timeout=300,
            )
            if result.returncode == 0:
                subs_path = os.path.join(dest_dir, "subs", f"{video_id}.en.json3")
                if os.path.exists(subs_path):
                    with open(subs_path, "r", encoding="utf-8") as f:
                        raw = json.load(f)
                    events = raw.get("events", [])
                    transcript = [
                        {"start": e.get("tStartMs", 0) / 1000.0,
                         "duration": (e.get("dDurationMs", 0) / 1000.0),
                         "text": "".join(seg.get("utf8", "") for seg in e.get("segs", []))}
                        for e in events if e.get("segs")
                    ]
        except (OSError, subprocess.TimeoutExpired) as e:
            if not error:
                error = f"yt-dlp subs échoué: {e}"
        except Exception as e:
            if not error:
                error = f"subs échoué: {e}"

    if not transcript:
        return {"status": "UNAVAILABLE", "error": error, "transcript": []}

    os.makedirs(dest_dir, exist_ok=True)
    out_path = os.path.join(dest_dir, f"transcript_{video_id}.json")
    payload = {
        "video_id": video_id,
        "url": url,
        "transcribed_at": now_iso(),
        "segments": transcript,
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    return {"status": "OK", "error": None, "transcript": transcript, "path": out_path}
