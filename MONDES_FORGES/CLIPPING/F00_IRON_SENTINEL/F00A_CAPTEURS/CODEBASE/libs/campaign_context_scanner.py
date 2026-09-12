"""
campaign_context_scanner.py — Perception de la campagne dans l'écosystème
Scanne les sources de contexte commanditées (recherche X, Reddit, YouTube,
etc. — fournies par le Warsmith dans campaign_to_observe.json) pour
détecter : qui a déjà clipé la campagne (compétiteurs), quels angles sont
déjà utilisés, et les résultats observés (vues, payout rapporté).
Best-effort : sources inaccessibles -> flaggées requires_vision.
"""

import re

from whop_scanner import fetch, _visible_text

_VIEWS_RE = re.compile(r"(\d[\d\s.,]*)\s*(K|k|M|m)?\s*(vues|views)?")
_ANGLE_HINT_RE = re.compile(
    r"(hook|angle|hook_type|tension|joie|admiration|outrage|inspiration|"
    r"money|argent|revenu|aibless|ai-bless)", re.I)


class CampaignContextScanner:
    """Perception de la campagne à travers les sources de contexte."""

    def __init__(self, campaign_url: str, niche: str, sources: list[str]):
        self.campaign_url = campaign_url
        self.niche = niche
        self.sources = sources or []

    # ------------------------------------------------------------------
    def scan(self) -> dict:
        competitors = []
        angles = []
        vision = []
        sources_status = []

        for url in self.sources:
            html, err = fetch(url)
            sources_status.append({
                "source": url,
                "status": "ok" if html else "fetch_failed",
                "mentions_of_campaign": 0,
            })
            if html is None:
                vision.append(f"source contexte {url} non fetchable ({err}) — "
                              "lecture IRON requise pour la perception compétiteurs")
                competitors.append({
                    "clipper_name": "inconnu",
                    "platform": url.split("/")[2] if "//" in url else url,
                    "angle_used": None,
                    "views": None,
                    "payout_reported": None,
                    "result": "non_estime",
                    "evidence_url": url,
                })
                continue

            text = _visible_text(html).lower()
            hints = set(_ANGLE_HINT_RE.findall(text))
            sources_status[-1]["mentions_of_campaign"] = text.count("whop") + text.count(
                self.niche.lower())

            links = re.findall(r'<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>', html, re.S | re.I)
            for href, label in links[:15]:
                label_text = _visible_text(label).lower()
                if not label_text or "whop" not in (href + label_text):
                    continue
                views = _VIEWS_RE.search(label_text)
                angle = _angle_guess(label_text, hints)
                comp_name = re.sub(r"\s+", " ", label_text)[:60] or None
                competitors.append({
                    "clipper_name": comp_name,
                    "platform": url.split("/")[2] if "//" in url else url,
                    "angle_used": angle,
                    "views": int(views.group(1).replace(" ", "").replace(",", ""))
                             if views and views.group(1).strip().isdigit() else None,
                    "payout_reported": None,
                    "result": "high" if views and views.group(1) else "medium",
                    "evidence_url": url,
                })

            if not competitors:
                vision.append(f"aucun lien campagne détecté sur {url} — "
                              "compétiteurs à confirmer par lecture IRON")

        dedup = {}
        for c in competitors:
            key = (c["platform"], c["clipper_name"])
            if key not in dedup:
                dedup[key] = c
        competitors = list(dedup.values())

        for c in competitors:
            if c.get("angle_used"):
                angles.append({
                    "angle": c["angle_used"],
                    "competitor": c["clipper_name"] or "inconnu",
                    "result": c.get("result", "non_estime"),
                    "evidence_url": c.get("evidence_url"),
                })

        return {
            "sources_scanned": sources_status,
            "competitors_observed": competitors,
            "angles_already_used": angles,
            "requires_vision": vision,
        }


def _angle_guess(label_text: str, hints: set) -> str | None:
    if not hints:
        return None
    if "tension" in hints or "outrage" in hints:
        return "tension/outrage"
    if "admiration" in hints:
        return "admiration"
    if "joie" in hints or "inspiration" in hints:
        return "joie/inspiration"
    if "money" in hints or "argent" in hints or "revenu" in hints:
        return "money"
    if "aibless" in hints or "ai-bless" in hints:
        return "aibless"
    return None
