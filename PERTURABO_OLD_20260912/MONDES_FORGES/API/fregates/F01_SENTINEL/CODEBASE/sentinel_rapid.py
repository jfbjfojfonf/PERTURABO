"""
F01 SENTINEL — Module sentinel_rapid
Scrape les listings RapidAPI d'une catégorie via Jina Reader + parsing
"""
import re
import httpx

JINA_BASE = "https://r.jina.ai/"
RAPIDAPI_BASE = "https://rapidapi.com"


def scrape_category(category_slug: str, max_pages: int = 3) -> list[dict]:
    """Scrape les APIs d'une catégorie RapidAPI."""
    results = []
    for page in range(1, max_pages + 1):
        url = f"{RAPIDAPI_BASE}/category/{category_slug}?page={page}"
        md = _fetch_jina(url)
        if not md:
            break
        apis = _parse_api_listings(md)
        if not apis:
            break
        results.extend(apis)
    return results


def scrape_api_detail(api_slug: str) -> dict:
    """Scrape la page détail d'une API (pricing, endpoints, reviews)."""
    url = f"{RAPIDAPI_BASE}/api/{api_slug}"
    md = _fetch_jina(url)
    if not md:
        return {"slug": api_slug, "status": "error"}
    return _parse_api_detail(md, api_slug)


def _fetch_jina(url: str) -> str:
    try:
        resp = httpx.get(JINA_BASE + url, timeout=30, follow_redirects=True,
                         headers={"Accept": "text/markdown"})
        resp.raise_for_status()
        return resp.text
    except Exception:
        return ""


def _parse_api_listings(markdown: str) -> list[dict]:
    """Extrait noms et slugs depuis le Markdown de la page catégorie."""
    apis = []
    # Pattern : liens API dans les listings RapidAPI
    patterns = [
        r'\[([^\]]+)\]\(https://rapidapi\.com/([^/]+)/api/([^\s\)]+)\)',
        r'##\s+(.+)',
    ]
    for pat in patterns:
        matches = re.findall(pat, markdown)
        for m in matches[:20]:
            if isinstance(m, tuple) and len(m) >= 3:
                apis.append({"name": m[0].strip(), "provider": m[1], "slug": m[2].strip(")")})
    return apis[:20]


def _parse_api_detail(markdown: str, slug: str) -> dict:
    """Extrait pricing, latence, score, endpoints depuis le Markdown détail."""
    detail = {"slug": slug, "status": "ok", "pricing_tiers": [], "endpoints": [], "raw_excerpt": ""}

    # Extraire tarifs
    price_matches = re.findall(r'\$\s*(\d+(?:\.\d+)?)\s*/\s*(?:month|mo)', markdown, re.IGNORECASE)
    detail["pricing_tiers"] = [float(p) for p in price_matches[:5]]

    # Extraire latence mentionnée
    lat_match = re.search(r'(\d+)\s*ms', markdown)
    if lat_match:
        detail["latency_ms"] = int(lat_match.group(1))

    # Extraire endpoints mentionnés
    ep_matches = re.findall(r'(?:GET|POST|PUT|DELETE)\s+(/[^\s\)]+)', markdown)
    detail["endpoints"] = ep_matches[:10]

    # Extrait brut pour l'Oracle
    detail["raw_excerpt"] = markdown[:3000]

    return detail
