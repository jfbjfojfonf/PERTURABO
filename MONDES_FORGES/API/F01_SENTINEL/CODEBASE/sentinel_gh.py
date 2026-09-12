"""
sentinel_gh.py — GitHub API
Mesure l'adoption réelle d'une API par les agents de codage.
"""

import os
import requests
from typing import Optional

GITHUB_API = "https://api.github.com"


def _headers() -> dict:
    h = {"Accept": "application/vnd.github.v3+json"}
    token = os.getenv("GITHUB_TOKEN", "")
    if token:
        h["Authorization"] = f"token {token}"
    return h


def search_wrappers(api_name: str, rapidapi_host: str = "") -> dict:
    """Cherche les repos qui utilisent cette API. Retourne wrappers + top repos."""
    queries = []
    if rapidapi_host:
        queries.append(f'"{rapidapi_host}"')
    queries.append(f'"{api_name}" rapidapi')

    total_count = 0
    repos = []

    for q in queries[:2]:
        try:
            resp = requests.get(
                f"{GITHUB_API}/search/repositories",
                params={"q": q, "sort": "stars", "per_page": 5},
                headers=_headers(),
                timeout=15
            )
            if resp.status_code == 200:
                data = resp.json()
                total_count = max(total_count, data.get("total_count", 0))
                for item in data.get("items", []):
                    repos.append({
                        "name": item["full_name"],
                        "stars": item["stargazers_count"],
                        "updated_at": item["updated_at"],
                        "description": item.get("description", ""),
                        "url": item["html_url"]
                    })
            elif resp.status_code == 403:
                print("[sentinel_gh] Rate limit. Définir GITHUB_TOKEN pour 5000 req/h.")
                break
        except Exception as e:
            print(f"[sentinel_gh] Erreur: {e}")

    seen = set()
    unique = []
    for r in repos:
        if r["name"] not in seen:
            seen.add(r["name"])
            unique.append(r)

    return {
        "total_wrappers": total_count,
        "top_repos": unique[:10],
        "total_stars": sum(r["stars"] for r in unique),
        "authenticated": bool(os.getenv("GITHUB_TOKEN"))
    }


def code_usage_count(rapidapi_host: str) -> int:
    """Nombre de fichiers requirements.txt qui référencent ce host."""
    if not rapidapi_host:
        return 0
    try:
        resp = requests.get(
            f"{GITHUB_API}/search/code",
            params={"q": f"{rapidapi_host} filename:requirements.txt", "per_page": 1},
            headers=_headers(),
            timeout=15
        )
        if resp.status_code == 200:
            return resp.json().get("total_count", 0)
    except Exception:
        pass
    return 0
