"""
enrich.py — Couche d'enrichissement métadonnées pour F01_SENTINEL
Récupère les métadonnées complètes d'une vidéo via yt-dlp --dump-json.
Ce que RECON ne récupère pas : view_count, description, upload_date,
thumbnail, tags, channel_id, channel_url, subscriber_count.
"""

import subprocess
import json
import sys
import os

# Path anchoring — permet d'appeler depuis n'importe où
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(_SCRIPT_DIR)))


def enrich_video(video_url: str) -> dict:
    """
    Récupère les métadonnées enrichies d'une vidéo via yt-dlp --dump-json.
    Retourne un dict avec toutes les métadonnées nécessaires à PERTURABO.
    """
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
            return {
                "status": "ECHEC",
                "error": f"yt-dlp --dump-json error: {result.stderr[:300]}",
                "data": None
            }

        data = json.loads(result.stdout)

        return {
            "status": "OK",
            "error": None,
            "data": {
                "title": data.get("title"),
                "description": data.get("description"),
                "view_count": data.get("view_count"),
                "duration": data.get("duration"),
                "upload_date": data.get("upload_date"),
                "channel_id": data.get("channel_id"),
                "channel": data.get("channel"),
                "channel_url": data.get("channel_url"),
                "thumbnail": data.get("thumbnail"),
                "tags": data.get("tags", []),
                "categories": data.get("categories", []),
                "availability": data.get("availability"),
                "age_limit": data.get("age_limit"),
                "like_count": data.get("like_count"),
                "comment_count": data.get("comment_count"),
                "channel_follower_count": data.get("channel_follower_count"),
            }
        }

    except json.JSONDecodeError as e:
        return {
            "status": "ECHEC",
            "error": f"JSON parse error: {str(e)}",
            "data": None
        }
    except Exception as e:
        return {
            "status": "ECHEC",
            "error": str(e),
            "data": None
        }


def enrich_channel(channel_url: str) -> dict:
    """
    Récupère les statistiques d'une chaîne via yt-dlp.
    Retourne {channel, channel_id, channel_url, subscriber_count}.
    """
    cmd = [
        "yt-dlp",
        "--dump-json",
        "--no-download",
        "--no-warnings",
        "--playlist-items", "1",
        channel_url,
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

        if result.returncode != 0:
            return {
                "status": "ECHEC",
                "error": f"yt-dlp channel error: {result.stderr[:300]}",
                "data": None
            }

        data = json.loads(result.stdout)

        return {
            "status": "OK",
            "error": None,
            "data": {
                "channel": data.get("channel"),
                "channel_id": data.get("channel_id"),
                "channel_url": data.get("channel_url"),
                "channel_follower_count": data.get("channel_follower_count"),
            }
        }

    except Exception as e:
        return {
            "status": "ECHEC",
            "error": str(e),
            "data": None
        }


def calculate_outlier_score(view_count: int, subscriber_count: int) -> float | None:
    """
    Calcule l'Outlier Score = view_count / subscriber_count.
    Un score > 1.0 indique une vidéo qui a explosé par rapport à la taille de la chaîne.
    Un score > 10.0 indique un outlier massif (vidéo virale sur petite chaîne).
    """
    if not view_count or not subscriber_count or subscriber_count == 0:
        return None
    return round(view_count / subscriber_count, 2)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python enrich.py <URL_YOUTUBE>")
        sys.exit(1)

    url = sys.argv[1]
    print(f"[ENRICH] Récupération des métadonnées pour: {url}")

    result = enrich_video(url)
    if result["status"] == "OK":
        data = result["data"]
        print(f"\n[ENRICH] Titre: {data['title']}")
        print(f"[ENRICH] Vues: {data['view_count']}")
        print(f"[ENRICH] Thumbnail: {data['thumbnail']}")
        print(f"[ENRICH] Channel: {data['channel']}")
        print(f"[ENRICH] Subscribers: {data.get('channel_follower_count', 'N/A')}")

        subs = data.get("channel_follower_count")
        if subs and data.get("view_count"):
            score = calculate_outlier_score(data["view_count"], subs)
            print(f"[ENRICH] Outlier Score: {score}")
    else:
        print(f"[ENRICH] ERREUR: {result['error']}")
