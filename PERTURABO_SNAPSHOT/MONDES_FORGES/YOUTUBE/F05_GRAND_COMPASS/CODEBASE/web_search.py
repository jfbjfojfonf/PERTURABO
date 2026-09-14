"""
web_search.py — Recherche web pour valider les océans bleus
Utilise DuckDuckGo (gratuit, sans clé API).
"""

import requests
import re
from urllib.parse import quote


def search_web(query: str, max_results: int = 10) -> list:
    """
    Recherche web via DuckDuckGo HTML API (gratuit, sans clé).
    Retourne une liste de {"title", "url", "snippet"}.
    """
    url = f"https://html.duckduckgo.com/html/?q={quote(query)}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        results = []
        text = resp.text
        titles = re.findall(r'class="result__a"[^>]*>(.*?)</a>', text, re.DOTALL)
        snippets = re.findall(r'class="result__snippet"[^>]*>(.*?)</a>', text, re.DOTALL)
        links = re.findall(r'class="result__url"[^>]*href="(.*?)"', text)
        for i in range(min(max_results, len(titles))):
            results.append({
                "title": re.sub(r"<[^>]+>", "", titles[i]).strip(),
                "snippet": re.sub(r"<[^>]+>", "", snippets[i]).strip() if i < len(snippets) else "",
                "url": links[i] if i < len(links) else ""
            })
        return results
    except Exception as e:
        return [{"error": str(e)}]


def validate_blue_ocean(niche: str, concept: str) -> dict:
    """
    Valide si une niche est un océan bleu pour un concept donné.
    Recherche sur YouTube + web pour évaluer la concurrence.
    """
    # 1. Recherche YouTube
    yt_query = f"site:youtube.com {niche} {concept}"
    yt_results = search_web(yt_query, max_results=10)

    # 2. Recherche web générale
    web_query = f"{niche} {concept} youtube channel"
    web_results = search_web(web_query, max_results=10)

    # 3. Analyse de saturation
    yt_count = len([r for r in yt_results if "youtube.com" in r.get("url", "")])
    web_count = len(web_results)

    if yt_count <= 2:
        saturation = "OCÉAN BLEU — Très faible concurrence"
        score = 9
    elif yt_count <= 5:
        saturation = "OCÉAN BLEU LÉGER — Concurrence modérée"
        score = 6
    else:
        saturation = "OCÉAN ROUGE — Marché saturé"
        score = 3

    return {
        "niche": niche,
        "concept": concept,
        "youtube_results_count": yt_count,
        "web_results_count": web_count,
        "saturation_level": saturation,
        "blue_ocean_score": score,
        "youtube_results": yt_results[:5],
        "web_results": web_results[:5],
    }


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python web_search.py <niche> <concept>")
        sys.exit(1)
    import json
    report = validate_blue_ocean(sys.argv[1], sys.argv[2])
    print(json.dumps(report, ensure_ascii=False, indent=2))
