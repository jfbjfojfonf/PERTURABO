"""
iron_sentinel.py — CAPTEURS : Le Fer qui Veille
=================================================

Sweep principal des Capteurs. Scanne les chaînes concurrentes,
capture les nouvelles vidéos, récupère les transcriptions,
et nourrit l'ARCHIVUM automatiquement.

Lancé par GitHub Actions (iron_sentinel.yml) tous les jours à 2h du matin.
Peut aussi être lancé manuellement.

Usage:
  python iron_sentinel.py --channels CAPTEURS/IN/monitored_channels.json
  python iron_sentinel.py --channels CAPTEURS/IN/monitored_channels.json --limit 3
"""

import argparse
import json
import os
import sys
import subprocess
import time
from datetime import datetime, timezone

# Path anchoring
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_CAPTEURS_DIR = os.path.dirname(_SCRIPT_DIR)
_PROJECT_ROOT = os.path.dirname(_CAPTEURS_DIR)
_CAPTEURS_IN = os.path.join(_CAPTEURS_DIR, "IN")
_CAPTEURS_OUT = os.path.join(_CAPTEURS_DIR, "OUT")
_CAPTEURS_SIGNALS = os.path.join(_CAPTEURS_OUT, "signals")
_ARCHIVUM_TRANSCRIPTS = os.path.join(_PROJECT_ROOT, "ARCHIVUM", "transcripts")


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_channels(channels_path: str) -> dict:
    """Charge la liste des chaînes à surveiller."""
    with open(channels_path, "r", encoding="utf-8") as f:
        return json.load(f)


def list_channel_videos(channel_url: str, limit: int = 10) -> list:
    """
    Liste les vidéos récentes d'une chaîne via yt-dlp --flat-playlist.
    Retourne une liste de {video_id, title, url, duration}.
    """
    cmd = [
        "yt-dlp",
        "--flat-playlist",
        "--print", "%(id)s\t%(title)s\t%(url)s\t%(duration)s\t%(view_count)s",
        "--no-warnings",
        "--playlist-end", str(limit),
        channel_url,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        videos = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) >= 3:
                videos.append({
                    "video_id": parts[0],
                    "title": parts[1],
                    "url": parts[2],
                    "duration": float(parts[3]) if len(parts) > 3 and parts[3] != "NA" else None,
                    "view_count": int(parts[4]) if len(parts) > 4 and parts[4] != "NA" else None,
                })
        return videos
    except Exception as e:
        print(f"[CAPT] ⚠️ Erreur listage {channel_url}: {e}")
        return []


def get_video_metadata(video_url: str) -> dict:
    """Récupère les métadonnées enrichies d'une vidéo via yt-dlp --dump-json."""
    cmd = [
        "yt-dlp",
        "--dump-json",
        "--no-download",
        "--no-warnings",
        "--no-playlist",
        video_url,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            return {}
        data = json.loads(result.stdout)
        return {
            "title": data.get("title"),
            "view_count": data.get("view_count"),
            "channel": data.get("channel"),
            "channel_id": data.get("channel_id"),
            "channel_url": data.get("channel_url"),
            "channel_follower_count": data.get("channel_follower_count"),
            "thumbnail": data.get("thumbnail"),
            "upload_date": data.get("upload_date"),
            "duration": data.get("duration"),
        }
    except Exception:
        return {}


def get_transcript(video_id: str, languages: list = None) -> dict:
    """
    Récupère la transcription via youtube-transcript-api.
    Fallback: yt-dlp --write-subs.
    """
    if languages is None:
        languages = ["fr", "en", "en-US"]

    # Tentative 1: youtube-transcript-api
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        api = YouTubeTranscriptApi()
        fetched = api.fetch(video_id, languages=languages)
        transcript = [
            {"start": s.start, "text": s.text, "duration": s.duration}
            for s in fetched.snippets
        ]
        if transcript:
            return {"transcript": transcript, "status": "OK", "error": None}
    except Exception as e:
        print(f"[CAPT] ⚠️ transcript-api échoué pour {video_id}: {str(e)[:80]}")

    # Tentative 2: yt-dlp
    try:
        import tempfile
        url = f"https://www.youtube.com/watch?v={video_id}"
        with tempfile.TemporaryDirectory() as tmpdir:
            outtmpl = os.path.join(tmpdir, "sub")
            cmd = [
                "yt-dlp", "--write-subs", "--write-auto-subs",
                "--sub-lang", ",".join(languages),
                "--sub-format", "json3",
                "--skip-download", "--no-warnings",
                "-o", outtmpl, url,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            sub_files = [f for f in os.listdir(tmpdir) if f.endswith(".json3")]
            if not sub_files:
                sub_files = [f for f in os.listdir(tmpdir) if f.endswith(".vtt")]
            if not sub_files:
                return {"transcript": [], "status": "ECHEC", "error": "Aucun sous-titre"}

            sub_path = os.path.join(tmpdir, sub_files[0])
            if sub_path.endswith(".json3"):
                with open(sub_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                transcript = []
                for event in data.get("events", []):
                    if "segs" not in event:
                        continue
                    text = "".join(seg.get("utf8", "") for seg in event["segs"]).strip()
                    if text:
                        transcript.append({
                            "start": event.get("tStartMs", 0) / 1000.0,
                            "text": text,
                            "duration": event.get("dDurationMs", 2000) / 1000.0,
                        })
                if transcript:
                    return {"transcript": transcript, "status": "OK", "error": None}
    except Exception as e:
        print(f"[CAPT] ⚠️ yt-dlp fallback échoué pour {video_id}: {str(e)[:80]}")

    return {"transcript": [], "status": "ECHEC", "error": "Tous les fallbacks ont échoué"}


def calculate_outlier_score(view_count: int, subscriber_count: int) -> float | None:
    """Calcule l'Outlier Score = view_count / subscriber_count."""
    if not view_count or not subscriber_count or subscriber_count == 0:
        return None
    return round(view_count / subscriber_count, 2)


def is_new_video(video_id: str) -> bool:
    """Vérifie si une vidéo est déjà dans l'ARCHIVUM."""
    path = os.path.join(_ARCHIVUM_TRANSCRIPTS, f"{video_id}.json")
    return not os.path.exists(path)


def archive_transcript(video_id: str, channel_name: str, metadata: dict,
                       transcript_data: dict, outlier_score: float | None) -> str:
    """Archive la transcription dans ARCHIVUM/transcripts/."""
    os.makedirs(_ARCHIVUM_TRANSCRIPTS, exist_ok=True)
    path = os.path.join(_ARCHIVUM_TRANSCRIPTS, f"{video_id}.json")

    # Texte complet concaténé
    transcript_text = ""
    if transcript_data["transcript"]:
        transcript_text = " ".join(
            seg.get("text", "").strip() for seg in transcript_data["transcript"]
        )

    data = {
        "video_id": video_id,
        "title": metadata.get("title"),
        "channel": metadata.get("channel", channel_name),
        "channel_id": metadata.get("channel_id"),
        "channel_url": metadata.get("channel_url"),
        "subscriber_count": metadata.get("channel_follower_count"),
        "view_count": metadata.get("view_count"),
        "outlier_score": outlier_score,
        "thumbnail": metadata.get("thumbnail"),
        "upload_date": metadata.get("upload_date"),
        "duration": metadata.get("duration"),
        "transcript": {
            "text": transcript_text,
            "segments": transcript_data["transcript"],
            "status": transcript_data["status"],
            "segment_count": len(transcript_data["transcript"]),
        },
        "captured_at": now_iso(),
        "captured_by": "CAPTEURS",
    }

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return path


def run_sweep(channels_path: str, limit: int = 5, delay: float = 3.0):
    """
    Sweep principal des Capteurs.
    Scanne les chaînes, capture les nouvelles vidéos, archive les transcriptions.
    """
    sweep_id = f"capt_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    print(f"\n{'═' * 60}")
    print(f"🛰️  CAPTEURS — Iron Sentinel Sweep")
    print(f"{'═' * 60}")
    print(f"[CAPT] Sweep ID: {sweep_id}")

    # 1. Charger les chaînes
    channels_data = load_channels(channels_path)
    channels = channels_data.get("channels", [])
    print(f"[CAPT] Chaînes à surveiller: {len(channels)}")

    all_signals = []
    new_transcripts = 0
    total_videos_scanned = 0

    for ch in channels:
        ch_name = ch.get("name", "Inconnu")
        ch_url = ch.get("url", "")
        ch_category = ch.get("category", "unknown")

        print(f"\n[CAPT] Scan: {ch_name} ({ch_category})")

        # 2. Lister les vidéos récentes
        videos = list_channel_videos(ch_url, limit=limit)
        print(f"[CAPT]   {len(videos)} vidéos récentes trouvées")

        for video in videos:
            vid_id = video.get("video_id")
            if not vid_id:
                continue

            total_videos_scanned += 1

            # 3. Vérifier si déjà archivé
            if not is_new_video(vid_id):
                print(f"[CAPT]   ⏭️ {vid_id} déjà archivé")
                continue

            print(f"[CAPT]   🆕 {vid_id} — {video.get('title', 'N/A')[:50]}")

            # 4. Métadonnées enrichies
            metadata = get_video_metadata(video.get("url", f"https://www.youtube.com/watch?v={vid_id}"))

            # 5. Outlier Score
            view_count = metadata.get("view_count") or video.get("view_count")
            subs = metadata.get("channel_follower_count")
            outlier = calculate_outlier_score(view_count or 0, subs or 0)

            if outlier is not None:
                if outlier > 10.0:
                    print(f"[CAPT]   🔥 OUTLIER MASSIF: {outlier}")
                elif outlier > 3.0:
                    print(f"[CAPT]   ⚡ Outlier positif: {outlier}")
                else:
                    print(f"[CAPT]   Outlier: {outlier}")

            # 6. Transcription
            transcript_data = get_transcript(vid_id)
            if transcript_data["status"] == "OK":
                archive_path = archive_transcript(vid_id, ch_name, metadata, transcript_data, outlier)
                new_transcripts += 1
                print(f"[CAPT]   💾 Archivé: {archive_path}")
            else:
                print(f"[CAPT]   ⚠️ Transcription échouée: {transcript_data.get('error', 'unknown')}")

            # 7. Signal
            signal_level = None
            if outlier is not None:
                if outlier > 10.0:
                    signal_level = "ROUGE"
                elif outlier > 3.0:
                    signal_level = "JAUNE"

            if signal_level:
                all_signals.append({
                    "channel": ch_name,
                    "video_id": vid_id,
                    "title": metadata.get("title") or video.get("title"),
                    "view_count": view_count,
                    "subscriber_count": subs,
                    "outlier_score": outlier,
                    "signal_level": signal_level,
                    "transcript_stored": f"ARCHIVUM/transcripts/{vid_id}.json" if transcript_data["status"] == "OK" else None,
                })

            # Délai anti rate-limit
            time.sleep(delay)

    # 8. Générer le rapport de sweep
    sweep_report = {
        "sweep_id": sweep_id,
        "sweep_date": now_iso(),
        "channels_scanned": len(channels),
        "videos_scanned": total_videos_scanned,
        "new_videos_found": new_transcripts,
        "new_transcripts_archived": new_transcripts,
        "signals": all_signals,
        "signals_count": len(all_signals),
    }

    # 9. Sauvegarder le rapport
    os.makedirs(_CAPTEURS_SIGNALS, exist_ok=True)
    report_path = os.path.join(_CAPTEURS_SIGNALS, f"{sweep_id}.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(sweep_report, f, ensure_ascii=False, indent=2)
    print(f"\n[CAPT] 📊 Rapport de sweep: {report_path}")
    print(f"[CAPT] Signaux: {len(all_signals)} ({sum(1 for s in all_signals if s['signal_level'] == 'ROUGE')} rouges, {sum(1 for s in all_signals if s['signal_level'] == 'JAUNE')} jaunes)")
    print(f"[CAPT] Nouveaux transcripts archivés: {new_transcripts}")

    # 10. Mettre à jour last_sweep
    channels_data["last_sweep"] = now_iso()
    with open(channels_path, "w", encoding="utf-8") as f:
        json.dump(channels_data, f, ensure_ascii=False, indent=2)

    print(f"\n{'═' * 60}")
    print(f"🛰️  CAPTEURS — SWEEP TERMINÉ")
    print(f"{'═' * 60}")

    return sweep_report


def main():
    parser = argparse.ArgumentParser(description="CAPTEURS — Iron Sentinel Sweep")
    parser.add_argument("--channels", default=None,
                        help="Chemin vers monitored_channels.json")
    parser.add_argument("--limit", type=int, default=5,
                        help="Nombre max de vidéos récentes par chaîne")
    parser.add_argument("--delay", type=float, default=3.0,
                        help="Délai entre les vidéos (anti rate-limit)")
    args = parser.parse_args()

    channels_path = args.channels or os.path.join(_CAPTEURS_IN, "monitored_channels.json")
    if not os.path.exists(channels_path):
        print(f"[CAPT] ❌ Fichier chaînes introuvable: {channels_path}")
        sys.exit(1)

    run_sweep(channels_path, limit=args.limit, delay=args.delay)


if __name__ == "__main__":
    main()
