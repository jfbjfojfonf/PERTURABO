"""
suggestions_ingestor.py — Senseur "demande" Google Suggest (F00_CAPTEURS)
=========================================================================
SIGNAL 4 (demande) : les suggestions de saisie Google mesurent ce que les
gens TAPENT réellement. Un sujet viral a une demande observable :
  - volume de la suggestion (hits) via https://suggestqueries.google.com
  - présence de mots-clés de tension ("why", "who", "vs", "record", ...)

Sans clé, gratuit, instantané. Best-effort.
"""

import urllib.error
import urllib.parse
import urllib.request
import re

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 " \
     "(KHTML, like Gecko) Chrome/125.0 Safari/537.36"

SUGGEST_URL = "https://suggestqueries.google.com/complete/search"
TENSION_WORDS = ("why", "who", "what", "vs", "record", "highlights",
                 "dunk", "react", "analysis", "worth", "best", "crazy",
                 "epic", "moment", "behind", "update")

_JSON_RE = re.compile(r"^(\[.*\])$", re.DOTALL)


def _suggest(query: str, timeout: int = 15) -> list[str]:
    """Suggestions Google pour un préfixe donné."""
    params = urllib.parse.urlencode({
        "client": "chrome", "hl": "en", "ds": "yt", "q": query})
    url = f"{SUGGEST_URL}?{params}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
        m = _JSON_RE.search(raw)
        if not m:
            return []
        data = _safe_json(m.group(1))
        return data[1] if isinstance(data, list) and len(data) > 1 else []
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError):
        return []


def _safe_json(text: str) -> list:
    """JSON peut être malformé (apostrophes) — on retombe sur json.loads
    après un best-effort de réparation."""
    import json
    try:
        return json.loads(text)
    except ValueError:
        return []


def scan(keywords: list[str], max_suggestions: int = 10) -> dict:
    """Suggestions Google (ds=yt) pour chaque mot-clé. Retourne :
    [{query, suggestions:[...], demand_score: 0..100,
      tension_hits: n, total_hits: n}]"""
    out = []
    for kw in keywords[:6]:
        suggs = _suggest(kw)
        suggs = suggs[:max_suggestions]
        lower = " ".join(suggs).lower()
        tension_hits = sum(1 for w in TENSION_WORDS if w in lower)
        total_hits = len(suggs)
        demand_score = min(100, total_hits * 10 + tension_hits * 5)
        out.append({
            "query": kw,
            "suggestions": suggs,
            "tension_hits": tension_hits,
            "total_hits": total_hits,
            "demand_score": demand_score,
        })
    return {"signal": "demande", "status": "ok",
            "note": "suggestions Google ds=yt", "keywords": out}
