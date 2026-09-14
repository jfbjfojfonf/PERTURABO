"""
demon_scanner.py — Scan des Démon wild clipping (TikTok / Shorts / Reels)
Sondes commanditées via IN/scan_list.json (Warsmith fournit les URLs de
recherche explicites par plateforme). La plupart de ces pages sont
JS-rendered ou bloquées : le senseur documente la sonde, extrait ce qui
est mécaniquement possible, et flagge le reste pour lecture IRON.
Résultat archivé dans ARCHIVUM/demons/.
"""

import re

from whop_scanner import fetch, _visible_text

_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.S | re.I)
_VIEWS_RE = re.compile(r"(\d[\d\s.,]*)\s*(K|k|M|m)?\s*(vues|views)")


class DemonScanner:
    """Sonde les Démon wild clipping sur les plateformes commanditées."""

    def __init__(self, queries: list[dict]):
        self.queries = queries or []

    # ------------------------------------------------------------------
    def scan(self) -> dict:
        probes = []
        demons = []
        vision = []

        for q in self.queries:
            query = q.get("query", "")
            platform = q.get("platform", "inconnue")
            url = q.get("url", "")
            probe = {
                "query": query,
                "platform": platform,
                "url": url or "manquante",
                "status": "pending",
                "fetched_at": None,
            }
            if not url:
                probe["status"] = "skipped"
                probe["reason"] = "url de sonde manquante dans scan_list.json"
                vision.append(f"sonde demon '{query}' sans url — "
                              "le Warsmith doit fournir l'URL de recherche explicite")
                probes.append(probe)
                continue

            html, err = fetch(url)
            probe["fetched_at"] = None  # conservé pour stabilité du schéma
            if html is None:
                probe["status"] = "fetch_failed"
                probe["reason"] = err
                vision.append(f"sonde {platform} '{query}' bloquée/non fetchable "
                              f"({err}) — chasse IRON manuelle requise")
                probes.append(probe)
                continue

            text = _visible_text(html).lower()
            if len(text) < 200:
                probe["status"] = "js_rendered"
                probe["reason"] = "page coquille JS — contenu non extrait mécaniquement"
                vision.append(f"sonde {platform} '{query}' rendue par JS — "
                              "lecture IRON (playwright/selenium) requise")
            else:
                probe["status"] = "ok"
                title = _TITLE_RE.search(html)
                probe["title"] = title.group(1).strip()[:120] if title else None

            views = _VIEWS_RE.search(text)
            demons.append({
                "demon_name": probe.get("title") or query,
                "territory": platform,
                "platform": platform,
                "query_used": query,
                "evidence_url": url,
                "views": views.group(0).strip() if views else None,
                "status": probe["status"],
            })
            probes.append(probe)

        return {
            "scan_type": "demon_wild_clipping",
            "probes": probes,
            "demons_observed": demons,
            "requires_vision": vision,
            "note": "Démons wild = clip qui échappe au clipping commandité. "
                    "Le siège les observe, TYRANT décide.",
        }
