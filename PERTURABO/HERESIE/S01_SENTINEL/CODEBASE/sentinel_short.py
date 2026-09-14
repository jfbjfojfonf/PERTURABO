"""
sentinel_short.py — S01_SENTINEL SHORT : La Reconnaissance de Fer (Shorts)
==========================================================================

Frégate de capture de specimen YouTube Short.
Récupère les métadonnées, la transcription et la première frame d'un Short.

ARCHITECTURE :
  Pas d'IA. Juste du code qui capture les données brutes.
  L'IRON prend le relais dans S02_BREACHER.

OUTPUTS :
  - specimen_short.json : métadonnées + transcript + first frame path + outlier score

Usage:
  python sentinel_short.py --url "https://youtube.com/shorts/XXXX"
  python sentinel_short.py --url "https://youtube.com/watch?v=XXXX"
  python sentinel_short.py --status
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

# Path anchoring
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_S01_DIR = os.path.dirname(_SCRIPT_DIR)
_PROJECT_ROOT = os.path.dirname(_S01_DIR)
_S01_IN = os.path.join(_S01_DIR, "IN")
_S01_OUT = os.path.join(_S01_DIR, "OUT")


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def extract_video_id(url: str) -> str:
    """Extrait l'ID vidéo d'une URL YouTube (Short ou Long)."""
    if "/shorts/" in url:
        return url.split("/shorts/")[1].split("?")[0].split("&")[0]
    if "watch?v=" in url:
        return url.split("watch?v=")[1].split("&")[0]
    if "youtu.be/" in url:
        return url.split("youtu.be/")[1].split("?")[0].split("&")[0]
    return url


def fetch_metadata(video_id: str) -> dict:
    """Récupère les métadonnées via yt-dlp --dump-json."""
    import subprocess

    url = f"https://www.youtube.com/watch?v={video_id}"
    try:
        result = subprocess.run(
            ["yt-dlp", "--dump-json", "--no-warnings", url],
            capture_output=True, text=True, timeout=60
        )
        if result.returncode != 0:
            print(f"[S01] ⚠️ yt-dlp error: {result.stderr[:200]}")
            return {}

        data = json.loads(result.stdout)

        return {
            "video_id": video_id,
            "video_url": url,
            "title": data.get("title", ""),
            "description": data.get("description", ""),
            "upload_date": data.get("upload_date", ""),
            "duration": data.get("duration", 0),
            "view_count": data.get("view_count", 0),
            "like_count": data.get("like_count", 0),
            "thumbnail": data.get("thumbnail", ""),
            "tags": data.get("tags", []),
            "channel": {
                "name": data.get("channel", ""),
                "id": data.get("channel_id", ""),
                "url": data.get("channel_url", ""),
                "subscriber_count": data.get("channel_follower_count", 0),
            },
        }
    except Exception as e:
        print(f"[S01] ❌ fetch_metadata error: {e}")
        return {}


def fetch_transcript(video_id: str) -> dict:
    """Récupère la transcription via youtube-transcript-api."""
    try:
        from youtube_transcript_api import YouTubeTranscriptApi

        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        if not transcript_list:
            return {"text": "", "segments": [], "language": "unknown", "status": "NO_TRANSCRIPT"}

        full_text = " ".join([seg["text"] for seg in transcript_list])
        return {
            "text": full_text,
            "segments": transcript_list,
            "segment_count": len(transcript_list),
            "language": "auto",
            "status": "OK"
        }
    except Exception as e:
        print(f"[S01] ⚠️ Transcript error: {e}")
        return {"text": "", "segments": [], "language": "unknown", "status": f"ERROR: {str(e)[:100]}"}


def download_first_frame(video_id: str, output_path: str = None) -> str:
    """Télécharge la thumbnail/first frame via yt-dlp."""
    import subprocess

    if output_path is None:
        output_path = os.path.join(_S01_OUT, "first_frame.jpg")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    url = f"https://www.youtube.com/watch?v={video_id}"
    try:
        subprocess.run(
            ["yt-dlp", "--write-thumbnail", "--skip-download",
             "-o", output_path.replace(".jpg", ".%(ext)s"), url],
            capture_output=True, text=True, timeout=30
        )

        # Find the actual downloaded file
        base = output_path.replace(".jpg", "")
        for ext in [".jpg", ".webp", ".png"]:
            if os.path.exists(base + ext):
                if ext != ".jpg":
                    os.rename(base + ext, output_path)
                return output_path

        # Fallback: use thumbnail URL
        return None
    except Exception as e:
        print(f"[S01] ⚠️ First frame error: {e}")
        return None


def calculate_outlier_score(view_count: int, subscriber_count: int) -> float:
    """Calcule l'Outlier Score Shorts-specific."""
    if subscriber_count == 0:
        return 0.0
    return round(view_count / subscriber_count, 2)


def is_short(duration: int) -> bool:
    """Vérifie si la vidéo est un Short (≤ 60s)."""
    return duration <= 60


def capture_specimen(url: str) -> dict:
    """Capture complète du specimen Short."""
    print(f"\n{'='*60}")
    print(f"S01_SENTINEL SHORT — Capture du specimen")
    print(f"{'='*60}\n")

    video_id = extract_video_id(url)
    print(f"[S01] Video ID: {video_id}")

    # 1. Métadonnées
    print(f"[S01] Récupération métadonnées (yt-dlp)...")
    metadata = fetch_metadata(video_id)
    if not metadata:
        print(f"[S01] ❌ Impossible de récupérer les métadonnées")
        return None

    duration = metadata.get("duration", 0)
    is_short_video = is_short(duration)
    print(f"[S01] Titre: {metadata['title']}")
    print(f"[S01] Durée: {duration}s ({'SHORT ✅' if is_short_video else 'LONG ⚠️'})")
    print(f"[S01] Vues: {metadata['view_count']:,}")
    print(f"[S01] Likes: {metadata['like_count']:,}")
    print(f"[S01] Chaîne: {metadata['channel']['name']} ({metadata['channel']['subscriber_count']:,} subs)")

    # 2. Transcript
    print(f"\n[S01] Récupération transcript (youtube-transcript-api)...")
    transcript = fetch_transcript(video_id)
    print(f"[S01] Transcript: {transcript['status']} ({transcript.get('segment_count', 0)} segments)")

    # 3. First frame
    print(f"\n[S01] Téléchargement first frame (yt-dlp)...")
    first_frame_path = download_first_frame(video_id)
    print(f"[S01] First frame: {'✅' if first_frame_path else '❌'}")

    # 4. Outlier Score
    outlier = calculate_outlier_score(
        metadata["view_count"],
        metadata["channel"]["subscriber_count"]
    )
    print(f"[S01] Outlier Score: {outlier}")

    # 5. Assembler specimen_short.json
    specimen = {
        **metadata,
        "is_short": is_short_video,
        "outlier_score": outlier,
        "transcript": transcript,
        "first_frame": first_frame_path,
        "s01_meta": {
            "captured_at": now_iso(),
            "tools_used": ["yt-dlp", "youtube-transcript-api"],
            "note": "yt-dlp view_count for Shorts = ~50% of page views (engaged views vs reely views)"
        }
    }

    # 6. Sauvegarder
    os.makedirs(_S01_OUT, exist_ok=True)
    output_path = os.path.join(_S01_OUT, "specimen_short.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(specimen, f, ensure_ascii=False, indent=2)

    print(f"\n[S01] ✅ specimen_short.json sauvegardé: {output_path}")
    print(f"[S01] Taille: {os.path.getsize(output_path):,} bytes")

    return specimen


def cmd_status(args):
    """Affiche l'état de S01."""
    print(f"\nS01_SENTINEL SHORT — Statut")
    print(f"{'='*40}")

    specimen_path = os.path.join(_S01_OUT, "specimen_short.json")
    frame_path = os.path.join(_S01_OUT, "first_frame.jpg")

    print(f"  Specimen capturé : {'✅' if os.path.exists(specimen_path) else '❌'}")
    print(f"  First frame      : {'✅' if os.path.exists(frame_path) else '❌'}")

    if os.path.exists(specimen_path):
        with open(specimen_path, "r") as f:
            data = json.load(f)
        print(f"  Titre            : {data.get('title', 'N/A')}")
        print(f"  Durée            : {data.get('duration', 0)}s")
        print(f"  Outlier Score    : {data.get('outlier_score', 'N/A')}")
        print(f"  Transcript       : {data.get('transcript', {}).get('status', 'N/A')}")


def main():
    parser = argparse.ArgumentParser(description="S01_SENTINEL SHORT — Capture de specimen Short")
    subparsers = parser.add_subparsers(dest="command")

    p_capture = subparsers.add_parser("capture", help="Capturer un Short")
    p_capture.add_argument("--url", required=True, help="URL du Short YouTube")
    p_capture.set_defaults(func=lambda a: capture_specimen(a.url))

    p_status = subparsers.add_parser("status", help="État de S01")
    p_status.set_defaults(func=cmd_status)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
