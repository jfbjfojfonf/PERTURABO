"""
clipping_ecosystem_scanner.py — Senseur des sites clipping commandités
Ne scanne QUE les sites listés par le Warsmith dans
IN/clipping_sites_to_scrap.json (en plus de Whop, défaut système).
Extrait : titre, campagnes Whop référencées, payouts observés, outils AI
mentionnés. Sites non listés -> jamais touchés (hérésie gardée en amont).
"""

import re

from whop_scanner import fetch, _visible_text

_WHOP_LINK_RE = re.compile(r"whop\.com/[a-zA-Z0-9_\-]+")
_PAYOUT_RE = re.compile(r"\$\s?\d+(?:[.,]\d+)?")
_TOOLS = {
    "gpt": ["gpt", "openai", "chatgpt"],
    "claude": ["claude", "anthropic"],
    "playwright": ["playwright"],
    "selenium": ["selenium"],
    "premiere": ["premiere", "after effects", "capcut"],
}


def _extract(html: str) -> dict:
    text = _visible_text(html).lower()
    title = re.search(r"<title[^>]*>(.*?)</title>", html, re.S | re.I)
    return {
        "title": (title.group(1).strip()[:120] if title else "non_extrait"),
        "whop_campaigns_referenced": len(set(_WHOP_LINK_RE.findall(html))),
        "payouts_observed": _PAYOUT_RE.findall(text)[:8],
        "ai_tools_mentioned": sorted(t for t, keys in _TOOLS.items()
                                     if any(k in text for k in keys)),
    }


class ClippingEcosystemScanner:
    """Scanne les sites clipping commandités par le Warsmith."""

    def __init__(self, sites: list[dict]):
        self.sites = sites or []

    # ------------------------------------------------------------------
    def scan(self) -> dict:
        scanned = []
        for site in self.sites:
            url = site.get("url", "")
            entry = {
                "site": site.get("name", url),
                "url": url,
                "scrape_method": site.get("scrape_method", "requests"),
                "rate_limit_sec": site.get("rate_limit_sec", 2),
                "status": "pending",
                "data_extracted": None,
                "requires_vision": [],
            }
            if not url:
                entry["status"] = "skipped"
                entry["requires_vision"].append("url manquante dans la config")
                scanned.append(entry)
                continue

            html, err = fetch(url)
            if html is None:
                entry["status"] = "fetch_failed"
                entry["fetch_reason"] = err
                entry["requires_vision"].append(
                    f"site {site.get('name')} non fetchable ({err}) — "
                    "lecture IRON manuelle requise")
            else:
                entry["status"] = "ok"
                entry["data_extracted"] = _extract(html)

            scanned.append(entry)

        tools = sorted({t for s in scanned
                        for t in (s.get("data_extracted") or {})
                        .get("ai_tools_mentioned", [])})
        payouts = [p for s in scanned
                   for p in (s.get("data_extracted") or {}).get("payouts_observed", [])]

        return {
            "scanned_sites": scanned,
            "tools_mentioned": tools,
            "payouts_observed": payouts[:8],
            "competitors_observed": [],
            "angles_already_used_on_this_campaign": [],
        }
