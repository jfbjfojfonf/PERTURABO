"""
trends_ingestor.py — Senseur Google Trends (F00_CAPTEURS)
=========================================================
SIGNAL 2 (tendance) : deux canaux sans clé.

  1. pytrends (si installé) : courbe d'intérêt par mot-clé sur 7 jours
     -> croissance = end/start. is_trending si >= 2.0 (doublé).
  2. Google Trends RSS global (trending/rss?geo=US) : les requêtes qui
     explosent en ce moment + approx_traffic (500+, 1000+, ...).

Best-effort : si pytrends est absent ou rate-limité, on retombe sur le
RSS global et on flagge le canal utilisé.
"""

import re
import urllib.error
import urllib.parse
import urllib.request
from xml.etree import ElementTree

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 " \
     "(KHTML, like Gecko) Chrome/125.0 Safari/537.36"

TRENDS_RSS_URL = "https://trends.google.com/trending/rss?geo=US"
_TREND_TRAFFIC_RE = re.compile(r"(\d+)(?:\.?\d*)([KMB])?")

GROWTH_THRESHOLD = 2.0  # intérêt doublé sur 7 jours = trending


def fetch(url: str, timeout: int = 20):
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


def _parse_trending_rss(xml_text: str) -> list[dict]:
    """Extrait les requêtes en hausse du RSS Google Trends."""
    out = []
    try:
        root = ElementTree.fromstring(xml_text)
    except ElementTree.ParseError:
        return out
    for item in root.findall(".//item"):
        title = (item.findtext("title") or "").strip()
        traffic_raw = ""
        for child in item:
            if child.tag.endswith("}approx_traffic"):
                traffic_raw = (child.text or "").strip()
        if not title:
            continue
        m = _TREND_TRAFFIC_RE.search(traffic_raw)
        traffic = None
        if m:
            val = float(m.group(1))
            if m.group(2) == "K":
                val *= 1000
            elif m.group(2) == "M":
                val *= 1_000_000
            traffic = int(val)
        out.append({"query": title, "approx_traffic": traffic,
                    "approx_traffic_raw": traffic_raw})
    return out


def scan_global_trending(max_items: int = 25) -> dict:
    """Les requêtes en hausse en ce moment (US)."""
    xml_text, err = fetch(TRENDS_RSS_URL)
    if xml_text is None:
        return {"status": "fetch_failed", "error": err, "trending": []}
    return {
        "status": "ok",
        "error": None,
        "trending": _parse_trending_rss(xml_text)[:max_items],
    }


def scan_keyword(keywords: list[str]) -> dict:
    """Courbe d'intérêt pytrends pour chaque mot-clé (best-effort).

    Retourne par mot-clé : {keyword, series_sample, first, last,
    growth_multiplier, is_trending, note}. En cas d'échec (module absent,
    rate limit, etc.) : status per_keyword "unavailable".
    """
    results = {}
    try:
        from pytrends.request import TrendReq
    except ImportError:
        return {
            "status": "pytrends_absent",
            "note": "pytrends non installé — ajouter à requirements_capteurs.txt",
            "keywords": {k: {"is_trending": None, "growth_multiplier": None,
                             "note": "pytrends absent"} for k in keywords},
        }

    try:
        pt = TrendReq(hl="en-US", tz=360, timeout=(10, 25),
                      retries=1, backoff_factor=0.5)
        for kw in keywords[:5]:  # limite 5 mots-clés pour le quota pytrends
            try:
                pt.build_payload([kw], cat=0, timeframe="now 7-d",
                                 geo="", gprop="")
                df = pt.interest_over_time()
                if df.empty or kw not in df.columns:
                    results[kw] = {"is_trending": None,
                                   "growth_multiplier": None,
                                   "note": "pas de données"}
                    continue
                s = df[kw]
                first = float(s.iloc[0])
                last = float(s.iloc[-1])
                growth = (last / first) if first > 0 else (last if last > 0 else 0)
                results[kw] = {
                    "is_trending": growth >= GROWTH_THRESHOLD,
                    "growth_multiplier": round(growth, 2),
                    "first": int(first),
                    "last": int(last),
                    "series_sample": [int(x) for x in s.values[::10]],
                    "note": None,
                }
            except Exception as e:  # noqa: BLE001 — best-effort
                results[kw] = {"is_trending": None,
                               "growth_multiplier": None,
                               "note": f"échec pytrends: {str(e)[:80]}"}
        return {"status": "ok", "note": None, "keywords": results}
    except Exception as e:  # noqa: BLE001
        return {"status": "error", "note": f"pytrends global: {str(e)[:100]}",
                "keywords": {k: {"is_trending": None, "growth_multiplier": None,
                                 "note": "pytrends error"} for k in keywords}}


def scan(keywords: list[str], max_items: int = 25) -> dict:
    """Signal tendance complet : RSS global + courbe par mot-clé."""
    global_rss = scan_global_trending(max_items)
    keyword_curves = scan_keyword(keywords)
    return {
        "signal": "tendance",
        "global_trending_rss": global_rss,
        "keyword_curves": keyword_curves,
    }
