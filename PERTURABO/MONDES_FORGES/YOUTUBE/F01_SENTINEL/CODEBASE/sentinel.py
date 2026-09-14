"""
sentinel.py — F01_SENTINEL : La Reconnaissance de Fer
=====================================================

Wrapper orchestrateur de la frégate F01.
Capture le specimen : transcription + métadonnées enrichies + outlier score.

Flux interne :
  1. RECON.run(url)         → video_id, title, url, duration
  2. SCRIBE.get_transcript() → transcript + timestamps (avec fallbacks)
  3. enrich.enrich_video()   → view_count, description, thumbnail, tags, channel, subs
  4. Calcul Outlier Score = view_count / subscriber_count
  5. Merge → specimen.json (OUT)
  6. Check-in IW_CUSTOS.py

Usage:
  python sentinel.py --url "https://youtube.com/watch?v=XXXX"
  python sentinel.py --brief F01_SENTINEL/IN/brief.json
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

# Path anchoring
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_F01_DIR = os.path.dirname(_SCRIPT_DIR)
_PROJECT_ROOT = os.path.dirname(_F01_DIR)

# Import des libs (RECON, SCRIBE, FORGE copiés de youtube-transcriber)
sys.path.insert(0, os.path.join(_SCRIPT_DIR, "libs"))
from RECON import run as recon_run, is_video_url, is_channel_url
from SCRIBE import get_transcript, run as scribe_run
from FORGE import run as forge_run

# Import enrich (local)
sys.path.insert(0, _SCRIPT_DIR)
from enrich import enrich_video, enrich_channel, calculate_outlier_score


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def capture_specimen(url: str, languages: list[str] = None) -> dict:
    """
    Pipeline complet de F01_SENTINEL.
    Prend une URL YouTube, retourne le specimen complet.
    """
    if languages is None:
        languages = ["fr", "en", "en-US"]

    print("=" * 60)
    print("🛰️  F01_SENTINEL — La Reconnaissance de Fer")
    print("=" * 60)
    print(f"[F01] URL cible: {url}")

    fallback_triggered = False
    tools_used = []

    # === 1. RECON : lister la vidéo ===
    print("\n[F01] Phase 1: RECON — identification de la cible...")
    recon_result = recon_run(url)
    videos = recon_result.get("videos", [])
    if not videos:
        return {"status": "ECHEC", "error": "RECON: aucune vidéo trouvée", "specimen": None}
    video = videos[0]
    video_id = video["video_id"]
    tools_used.append("RECON")
    print(f"[F01] Cible identifiée: {video_id} — {video.get('title', 'N/A')}")

    # === 2. SCRIBE : transcription ===
    print("\n[F01] Phase 2: SCRIBE — extraction du transcript...")
    transcript_data = get_transcript(video_id, languages)
    transcript_status = transcript_data["status"]
    if transcript_status != "OK":
        fallback_triggered = True
        print(f"[F01] ⚠️ Transcript échoué: {transcript_data.get('error', 'unknown')}")
    else:
        print(f"[F01] Transcript: {len(transcript_data['transcript'])} segments")
    tools_used.append("SCRIBE")

    # Construire le texte complet concaténé
    transcript_text = ""
    if transcript_data["transcript"]:
        transcript_text = " ".join(
            seg.get("text", "").strip() for seg in transcript_data["transcript"]
        )

    # === 3. ENRICH : métadonnées enrichies ===
    print("\n[F01] Phase 3: ENRICH — métadonnées enrichies (yt-dlp --dump-json)...")
    enrich_result = enrich_video(url)
    enrich_data = {}
    if enrich_result["status"] == "OK":
        enrich_data = enrich_result["data"]
        tools_used.append("enrich")
        print(f"[F01] Vues: {enrich_data.get('view_count', 'N/A')}")
        print(f"[F01] Thumbnail: {enrich_data.get('thumbnail', 'N/A')}")
        print(f"[F01] Channel: {enrich_data.get('channel', 'N/A')}")
        print(f"[F01] Subscribers: {enrich_data.get('channel_follower_count', 'N/A')}")
    else:
        print(f"[F01] ⚠️ Enrich échoué: {enrich_result.get('error', 'unknown')}")

    # === 4. Outlier Score ===
    view_count = enrich_data.get("view_count")
    subscriber_count = enrich_data.get("channel_follower_count")
    outlier_score = calculate_outlier_score(view_count or 0, subscriber_count or 0)
    if outlier_score is not None:
        print(f"\n[F01] Outlier Score: {outlier_score}")
        if outlier_score > 10.0:
            print(f"[F01] 🔥 OUTLIER MASSIF — vidéo virale sur petite chaîne")
        elif outlier_score > 1.0:
            print(f"[F01] ⚡ Outlier positif — vidéo au-dessus de la moyenne de la chaîne")

    # === 5. Assemblage du specimen ===
    specimen = {
        "video_id": video_id,
        "video_url": url,
        "title": enrich_data.get("title") or video.get("title"),
        "description": enrich_data.get("description"),
        "upload_date": enrich_data.get("upload_date"),
        "duration": enrich_data.get("duration") or video.get("duration"),
        "view_count": view_count,
        "like_count": enrich_data.get("like_count"),
        "comment_count": enrich_data.get("comment_count"),
        "thumbnail": enrich_data.get("thumbnail"),
        "tags": enrich_data.get("tags", []),
        "categories": enrich_data.get("categories", []),
        "channel": {
            "name": enrich_data.get("channel"),
            "id": enrich_data.get("channel_id"),
            "url": enrich_data.get("channel_url"),
            "subscriber_count": subscriber_count,
        },
        "outlier_score": outlier_score,
        "transcript": {
            "text": transcript_text,
            "segments": transcript_data["transcript"],
            "language": languages[0] if transcript_data["transcript"] else None,
            "status": transcript_status,
            "error": transcript_data.get("error"),
            "segment_count": len(transcript_data["transcript"]),
        },
        "f01_meta": {
            "captured_at": now_iso(),
            "tools_used": tools_used,
            "fallback_triggered": fallback_triggered,
            "recon_meta": recon_result.get("meta", {}),
        }
    }

    print(f"\n[F01] ✅ Specimen assemblé — video_id: {video_id}")
    return {"status": "OK", "error": None, "specimen": specimen}


def save_specimen(specimen: dict, output_dir: str = None) -> str:
    """Sauvegarde le specimen en JSON dans F01_SENTINEL/OUT/."""
    if output_dir is None:
        output_dir = os.path.join(_F01_DIR, "OUT")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "specimen.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(specimen, f, ensure_ascii=False, indent=2)
    print(f"[F01] 💾 Specimen sauvegardé: {output_path}")
    return output_path


def check_in_iw_custos(output_path: str):
    """Signale à IW_CUSTOS.py que F01 a terminé."""
    custos_path = os.path.join(_PROJECT_ROOT, "IW_CUSTOS.py")
    if os.path.exists(custos_path):
        import subprocess
        result = subprocess.run(
            [sys.executable, custos_path, "--mode", "check-in", "--frigate", "F01", "--output", output_path],
            capture_output=True, text=True, timeout=30
        )
        print(f"[F01] IW_CUSTOS: {result.stdout.strip()}")
        if result.stderr:
            print(f"[F01] IW_CUSTOS stderr: {result.stderr.strip()}")
    else:
        print(f"[F01] ⚠️ IW_CUSTOS.py non trouvé — check-in ignoré")


def load_brief(brief_path: str) -> dict:
    """Charge un fichier brief.json depuis F01_SENTINEL/IN/."""
    with open(brief_path, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    parser = argparse.ArgumentParser(description="F01_SENTINEL — La Reconnaissance de Fer")
    parser.add_argument("--url", help="URL YouTube de la vidéo cible")
    parser.add_argument("--brief", help="Chemin vers un fichier brief.json")
    parser.add_argument("--languages", nargs="*", default=["fr", "en", "en-US"],
                        help="Langues préférées pour le transcript")
    parser.add_argument("--no-checkin", action="store_true",
                        help="Ne pas signaler à IW_CUSTOS.py")
    args = parser.parse_args()

    # Récupérer l'URL
    url = args.url
    if not url and args.brief:
        brief = load_brief(args.brief)
        url = brief.get("video_url") or brief.get("url")
    if not url:
        print("Usage: python sentinel.py --url <URL> ou --brief <brief.json>")
        sys.exit(1)

    # Capturer le specimen
    result = capture_specimen(url, languages=args.languages)

    if result["status"] != "OK":
        print(f"\n[F01] ❌ ÉCHEC: {result['error']}")
        sys.exit(1)

    # Sauvegarder
    output_path = save_specimen(result["specimen"])

    # Check-in IW_CUSTOS
    if not args.no_checkin:
        check_in_iw_custos(output_path)

    print(f"\n{'=' * 60}")
    print(f"🛰️  F01_SENTINEL — MISSION ACCOMPLIE")
    print(f"{'=' * 60}")
    print(f"Specimen: {output_path}")
    print(f"Video ID: {result['specimen']['video_id']}")
    print(f"Outlier Score: {result['specimen']['outlier_score']}")
    print(f"Transcript: {result['specimen']['transcript']['segment_count']} segments")


if __name__ == "__main__":
    main()
