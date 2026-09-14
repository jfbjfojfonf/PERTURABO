"""
sentinel_web.py — Capture web via Jina Reader
Convertit n'importe quelle URL en markdown propre. Aucune clé requise.
"""

import requests
from typing import Optional

JINA_BASE = "https://r.jina.ai/"


def fetch_url(url: str, timeout: int = 30) -> Optional[str]:
    jina_url = f"{JINA_BASE}{url}"
    try:
        resp = requests.get(
            jina_url,
            timeout=timeout,
            headers={"Accept": "text/plain", "User-Agent": "PERTURABO-SENTINEL/1.0"}
        )
        resp.raise_for_status()
        content = resp.text.strip()
        return content if len(content) >= 100 else None
    except requests.RequestException as e:
        print(f"[sentinel_web] Erreur fetch {url}: {e}")
        return None


def fetch_multiple(urls: list, timeout: int = 30) -> dict:
    """Récupère plusieurs URLs. Retourne {url: contenu}."""
    results = {}
    for url in urls:
        print(f"[sentinel_web] Fetching: {url}")
        results[url] = fetch_url(url, timeout)
    return results
