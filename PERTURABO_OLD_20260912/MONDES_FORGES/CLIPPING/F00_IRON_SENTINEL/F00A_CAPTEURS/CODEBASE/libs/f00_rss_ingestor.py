"""
rss_ingestor.py — Senseur RSS Google News (F00_CAPTEURS)
========================================================
Ingère les articles frais d'une niche depuis Google News RSS (sans clé),
filtre par fenêtre de fraîcheur (5h = brûlant, 24h = frais), et extrait
pour chaque article : titre, source, lien, date + heures d'âge.

Ce senseur donne SIGNAL 1 (fraîcheur) + SIGNAL 4 (couverture médias :
un sujet mentionné par N médias différents est plus chaud).
"""

import datetime
import re
import urllib.error
import urllib.parse
import urllib.request
from xml.etree import ElementTree

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 " \
     "(KHTML, like Gecko) Chrome/125.0 Safari/537.36"

_RSS_NS = {"a": "http://www.w3.org/2005/Atom"}

# Durées (heures) acceptées pour une requête. Fenêtre "brûlant" = 5h,
# "frais" = 24h. Tout article plus vieux est rejeté (horodatage strict).
WINDOW_HOURS = {"brulant": 5, "frais": 24}

# Combien de mots-clés maximaux par requête Google News.
MAX_KEYWORDS = 6


def fetch(url: str, timeout: int = 20):
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


def build_url(keywords: list[str], lang: str = "en") -> str:
    """URL Google News RSS pour une recherche mots-clés."""
    q = " ".join(keywords[:MAX_KEYWORDS])
    params = {
        "q": q,
        "hl": lang,
        "gl": "US",
        "ceid": "US:en",
    }
    return "https://news.google.com/rss/search?" + urllib.parse.urlencode(params)


def _parse_datetime(raw: str) -> datetime.datetime | None:
    """Parse une date RFC 2822 (format Google News)."""
    if not raw:
        return None
    try:
        return datetime.datetime.strptime(raw.strip(),
                                          "%a, %d %b %Y %H:%M:%S %Z") \
            .replace(tzinfo=datetime.timezone.utc)
    except ValueError:
        try:
            return datetime.datetime.fromisoformat(raw.strip())
        except ValueError:
            return None


def _parse_entries(xml_text: str) -> list[dict]:
    """Extrait les items du flux (RSS 2.0 ou Atom). Retourne [{title, link, source, pub_at}]."""
    entries = []
    try:
        root = ElementTree.fromstring(xml_text)
    except ElementTree.ParseError:
        return entries

    # RSS 2.0 : <rss><channel><item>...</item></channel></rss>
    items = root.findall(".//item")
    if items:
        for item in items:
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            pub_raw = (item.findtext("pubDate") or "").strip()
            src_el = item.find("source")
            source = (src_el.text or "").strip() if src_el is not None else ""
            pub_at = _parse_datetime(pub_raw)
            if title:
                entries.append({
                    "title": title,
                    "link": link,
                    "source": source,
                    "pub_raw": pub_raw,
                    "pub_at": pub_at.isoformat() if pub_at else None,
                })
        return entries

    # Atom : <feed><entry>...</entry></feed>
    for item in root.findall(".//a:entry", _RSS_NS):
        title_el = item.find("a:title", _RSS_NS)
        link_el = item.find("a:link", _RSS_NS)
        pub_el = item.find("a:published", _RSS_NS)
        src_el = item.find("a:source/a:title", _RSS_NS)
        title = (title_el.text or "").strip() if title_el is not None else ""
        link = (link_el.get("href") or "") if link_el is not None else ""
        pub_raw = (pub_el.text or "") if pub_el is not None else ""
        source = (src_el.text or "").strip() if src_el is not None else ""
        pub_at = _parse_datetime(pub_raw)
        if title:
            entries.append({
                "title": title,
                "link": link,
                "source": source,
                "pub_raw": pub_raw,
                "pub_at": pub_at.isoformat() if pub_at else None,
            })
    return entries


def scan(keywords: list[str], freshness: str = "frais",
         max_items: int = 30, lang: str = "en") -> dict:
    """Scan Google News pour une niche.

    Retourne :
      {
        "signal": "fraicheur_et_couverture",
        "window_hours": 24,
        "keywords": [...],
        "fetched_articles": N,
        "fresh_articles": [ {title, source, link, age_hours}, ... ],
        "coverage": { "<titre normalisé>": {count, sources: [...]} },
        "status": "ok" | "fetch_failed",
        "error": "...",
      }
    """
    window = WINDOW_HOURS.get(freshness, 24)
    url = build_url(keywords, lang)
    xml_text, err = fetch(url)

    if xml_text is None:
        return {
            "signal": "fraicheur_et_couverture",
            "window_hours": window,
            "keywords": keywords,
            "fetched_articles": 0,
            "fresh_articles": [],
            "coverage": {},
            "status": "fetch_failed",
            "error": err,
        }

    entries = _parse_entries(xml_text)
    now = datetime.datetime.now(datetime.timezone.utc)

    fresh = []
    for e in entries:
        if not e.get("pub_at"):
            continue
        pub = datetime.datetime.fromisoformat(e["pub_at"])
        age_h = (now - pub).total_seconds() / 3600
        if age_h < 0:
            age_h = 0
        if age_h > window:
            continue
        fresh.append({
            "title": e["title"],
            "source": e["source"],
            "link": e["link"],
            "age_hours": round(age_h, 1),
        })

    fresh = fresh[:max_items]

    # Couverture : même sujet (normalisé) vu par combien de médias ?
    coverage = {}
    seen = set()
    for a in fresh:
        key = _normalize_title(a["title"])
        if not key or key in seen:
            continue
        seen.add(key)
        coverage[key] = {
            "count": sum(1 for b in fresh if _normalize_title(b["title"]) == key),
            "sources": sorted({b["source"] for b in fresh
                               if _normalize_title(b["title"]) == key}),
        }

    return {
        "signal": "fraicheur_et_couverture",
        "window_hours": window,
        "keywords": keywords,
        "fetched_articles": len(entries),
        "fresh_articles": fresh,
        "coverage": coverage,
        "status": "ok",
        "error": None,
    }


def _normalize_title(title: str) -> str:
    """Normalise un titre pour détecter la couverture multi-médias."""
    t = title.lower()
    t = re.sub(r"\b(the|a|an|of|in|on|for|to|and|vs|is|are|'s)\b", " ", t)
    t = re.sub(r"[^a-z0-9 ]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    # garde les 6 premiers mots significatifs
    return " ".join(t.split()[:6])
