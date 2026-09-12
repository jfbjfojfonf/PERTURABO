"""
F01 SENTINEL — Module sentinel_web
Scrape n'importe quelle URL via Jina Reader → Markdown propre
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..', 'CORE'))

import httpx


JINA_BASE = "https://r.jina.ai/"


def scrape_url(url: str, timeout: int = 30) -> dict:
    jina_url = JINA_BASE + url
    try:
        resp = httpx.get(jina_url, timeout=timeout, follow_redirects=True,
                         headers={"Accept": "text/markdown"})
        resp.raise_for_status()
        return {"url": url, "content": resp.text, "status": "ok"}
    except httpx.HTTPStatusError as e:
        return {"url": url, "content": "", "status": "error", "error": str(e)}
    except Exception as e:
        return {"url": url, "content": "", "status": "error", "error": str(e)}


def scrape_urls(urls: list[str], timeout: int = 30) -> list[dict]:
    results = []
    for url in urls:
        results.append(scrape_url(url, timeout))
    return results
