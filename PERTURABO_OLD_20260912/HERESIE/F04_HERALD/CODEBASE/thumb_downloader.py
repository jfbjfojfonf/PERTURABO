"""
thumb_downloader.py — Télécharge la thumbnail d'une vidéo YouTube
Utilise l'URL maxresdefault depuis specimen.json.
"""

import os
import requests

# Path anchoring
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_F04_DIR = os.path.dirname(_SCRIPT_DIR)
_F04_IN = os.path.join(_F04_DIR, "IN")


def download_thumbnail(url: str, output_path: str = None) -> str:
    """
    Télécharge une image depuis une URL.
    Retourne le chemin du fichier téléchargé.
    """
    if output_path is None:
        output_path = os.path.join(_F04_IN, "thumbnail.jpg")

    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()

        with open(output_path, "wb") as f:
            f.write(resp.content)

        size_kb = len(resp.content) / 1024
        print(f"[THUMB] Téléchargée: {output_path} ({size_kb:.1f} KB)")
        return output_path

    except Exception as e:
        print(f"[THUMB] ❌ Erreur téléchargement: {e}")
        return None


def get_thumbnail_url_from_specimen(specimen_path: str = None) -> str:
    """
    Extrait l'URL de la thumbnail depuis specimen.json.
    """
    import json
    if specimen_path is None:
        specimen_path = os.path.join(_F04_IN, "specimen.json")
    if not os.path.exists(specimen_path):
        return None
    with open(specimen_path, "r", encoding="utf-8") as f:
        specimen = json.load(f)
    return specimen.get("thumbnail")


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python thumb_downloader.py <URL> [output_path]")
        sys.exit(1)
    path = download_thumbnail(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
    if path:
        print(f"OK: {path}")
