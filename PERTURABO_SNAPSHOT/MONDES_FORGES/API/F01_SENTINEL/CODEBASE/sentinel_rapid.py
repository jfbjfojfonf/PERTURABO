"""
sentinel_rapid.py — Scraping RapidAPI via Jina Reader
Capture les listings d'une catégorie : popularité, latence, pricing.
"""

import importlib.util
from pathlib import Path
from typing import Optional

RAPIDAPI_BASE = "https://rapidapi.com"

CATEGORY_SLUGS = {
    "data": "Data",
    "tools": "Tools",
    "communication": "Communication",
    "financial": "Financial",
    "social": "Social",
    "location": "Location",
    "sports": "Sports",
    "text": "Text Analysis",
    "media": "Media",
    "machine-learning": "Machine Learning",
    "scraping": "Data",
    "linkedin": "Data",
    "email": "Tools",
}


def _load_web():
    spec = importlib.util.spec_from_file_location(
        "sentinel_web", Path(__file__).parent / "sentinel_web.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def scrape_category(category: str) -> Optional[str]:
    slug = CATEGORY_SLUGS.get(category.lower(), category.replace(" ", "%20"))
    url = f"{RAPIDAPI_BASE}/category/{slug}"
    print(f"[sentinel_rapid] Scraping category: {url}")
    return _load_web().fetch_url(url, timeout=45)


def scrape_search(query: str) -> Optional[str]:
    url = f"{RAPIDAPI_BASE}/search/{query.replace(' ', '%20')}"
    print(f"[sentinel_rapid] Scraping search: {url}")
    return _load_web().fetch_url(url, timeout=45)


def get_top_apis_raw(category_hint: Optional[str] = None) -> dict:
    """
    Capture les données brutes de RapidAPI.
    Retourne markdown brut — sera parsé par l'Oracle dans sentinel.py --finalize.
    """
    raw_data = {}

    if category_hint:
        content = scrape_category(category_hint)
        if content:
            raw_data["category_page"] = {
                "category": category_hint,
                "raw_markdown": content[:8000]
            }
        search_content = scrape_search(category_hint)
        if search_content:
            raw_data["search_results"] = {
                "query": category_hint,
                "raw_markdown": search_content[:8000]
            }
    else:
        # Mode ENCLENCHE : scan 3 catégories à fort volume
        for cat in ["data", "tools", "scraping"]:
            content = scrape_category(cat)
            if content:
                raw_data[f"category_{cat}"] = {
                    "category": cat,
                    "raw_markdown": content[:5000]
                }

    return raw_data
