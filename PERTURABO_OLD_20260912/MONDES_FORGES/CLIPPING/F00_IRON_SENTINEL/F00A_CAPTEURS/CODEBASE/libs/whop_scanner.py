"""
whop_scanner.py — Senseur Whop (page campagne + Discover)
Best-effort mécanique (stdlib urllib) : statut, budget, CPM, guidelines,
assets. Tout ce qui n'est pas quantifiable mécaniquement est flaggé
requires_vision pour lecture IRON par le Warsmith.
"""

import re
import urllib.error
import urllib.request

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 " \
     "(KHTML, like Gecko) Chrome/125.0 Safari/537.36"
_TEXT_RE = re.compile(r"<[^>]+>", re.S)
_STATUS_KEYWORDS = {
    "active": ["active", "ouvert", "open", "live", "en cours"],
    "ending_soon": ["ending soon", "se termine", "bientôt", "closes in"],
    "closed": ["closed", "terminé", "fermé", "completed", "inactive"],
}
_CPM_RE = re.compile(r"(\$?\s?\d+(?:[.,]\d+)?)\s*(?:cpm|CPM)")
_BUDGET_RE = re.compile(r"(?:budget|reste|remaining|left)\D{0,30}\$?\s?\d+(?:[.,]\d+)?", re.I)
_ASSET_KEYS = ["creative", "clip", "asset", "video", "script", "hook"]
_EMOTION_HITS = ["tension", "joie", "inspiration", "outrage", "admiration"]


def fetch(url: str, timeout: int = 15):
    """Retourne (html, error_reason). Jamais de levée."""

    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace"), None
    except urllib.error.HTTPError as e:
        return None, f"http_{e.code}"
    except urllib.error.URLError as e:
        return None, f"network_{e.reason}"
    except TimeoutError:
        return None, "timeout"


def _visible_text(html: str) -> str:
    return re.sub(r"\s+", " ", _TEXT_RE.sub(" ", html)).strip()[:12000]


class WhopScanner:
    """Scanne la page campagne Whop + la page Discover."""

    def __init__(self, campaign_url: str, whop_discover_url: str):
        self.campaign_url = campaign_url
        self.whop_discover_url = whop_discover_url

    # ------------------------------------------------------------------
    def scan(self) -> dict:
        html, err = fetch(self.campaign_url)
        if html is None:
            return {
                "campaign_url": self.campaign_url,
                "campaign_status": "non_accessible",
                "fetch_reason": err,
                "campaign_budget_remaining_estimate": "inconnu",
                "cpm_expected": "inconnu",
                "campaign_guidelines": "inaccessibles",
                "campaign_assets_published": [],
                "requires_vision": [
                    "page campagne non fetchable mécaniquement — lecture IRON "
                    "manuelle requise par le Warsmith"
                ],
            }

        text = _visible_text(html).lower()
        status = "active"
        for key, words in _STATUS_KEYWORDS.items():
            if any(w in text for w in words):
                status = key
                break

        cpm = _CPM_RE.search(text)
        budget = _BUDGET_RE.search(text)
        assets = [k for k in _ASSET_KEYS if k in text]

        discover_html, discover_err = fetch(self.whop_discover_url)
        discover_ok = discover_html is not None
        discover_hits = 0
        if discover_ok:
            discover_hits = len(re.findall(r"whop\.com/[a-zA-Z0-9_\-]+", discover_html))

        vision = []
        if not discover_ok:
            vision.append(f"Discover ({self.whop_discover_url}) non fetchable "
                          f"({discover_err or 'inconnue'}) — à lire par l'IRON")
        if cpm is None or budget is None:
            vision.append("budget/CPM non extraits mécaniquement — lecture IRON de "
                          "la page campagne requise")

        return {
            "campaign_url": self.campaign_url,
            "fetch_status": "ok" if html else "failed",
            "campaign_status": status,
            "campaign_budget_remaining_estimate": (
                budget.group(0).strip()[:80] if budget else "inconnu"),
            "cpm_expected": cpm.group(0).strip() if cpm else "inconnu",
            "campaign_guidelines": "extraites (présence de règles)" if "guideline" in text
                                  or "règle" in text else "inconnues",
            "campaign_assets_published": assets,
            "discover_scan": {
                "url": self.whop_discover_url,
                "status": "ok" if discover_ok else "failed",
                "campaigns_listed": discover_hits,
            },
            "requires_vision": vision,
        }
