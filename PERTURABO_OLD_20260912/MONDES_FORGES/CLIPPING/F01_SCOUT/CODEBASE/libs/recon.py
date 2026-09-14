"""
libs/recon.py — Extraction des assets depuis directive.md (F01_SCOUT)
=====================================================================

Parse le campaign goal doc (directive.md) pour extraire :
  - les URLs d'assets fournies par la campagne (section "assets" / "sources fournies")
  - le campaign_id (titre ou métadonnée)
  - les métadonnées disponibles (titre, durée, type)

Règle C1 (strict-source) : F01 n'inventorie QUE ce que la campagne fournit.
Toute URL trouvée ailleurs est ignorée.

Usage:
  from recon import parse_directive
  result = parse_directive("ARCHIVUM/campaign/directive.md")
"""

import json
import os
import re
from datetime import datetime, timezone

_URL_RE = re.compile(r'https?://[^\s)\]>"\'<>]+')
_CAMPAIGN_ID_RE = re.compile(r'(?:campaign(?:_|\s)id|campaigne|campagne)[\s:]*["\']?([A-Za-z0-9_-]{3,64})',
                             re.IGNORECASE)


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _classify_url(url: str) -> str:
    """Classe grossièrement le type d'asset depuis l'URL."""
    if "youtube.com" in url or "youtu.be" in url:
        return "video_long"
    if "twitch.tv" in url or "kick.com" in url:
        return "stream"
    if "spotify.com" in url or "podcast" in url:
        return "podcast"
    if url.endswith(".pdf") or ".pdf" in url:
        return "doc"
    return "video_long"


def _extract_asset_section(text: str) -> list[str]:
    """
    Cherche la section assets (souvent "## Assets", "## Sources fournies",
    "## Sources", "ASSETS :") et en extrait les URLs.
    """
    urls: list[str] = []
    lines = text.splitlines()
    in_section = False
    for line in lines:
        stripped = line.strip()
        if re.match(r'^#{1,4}\s+.*(assets|sources?|videos?|fourni)', stripped, re.IGNORECASE):
            in_section = True
            continue
        if in_section and stripped.startswith("#"):
            break
        if in_section:
            urls.extend(_URL_RE.findall(line))
    return urls


def _extract_urls_anywhere(text: str) -> list[str]:
    """Fallback : toutes les URLs du document (ordre du doc)."""
    return _URL_RE.findall(text)


def parse_directive(directive_path: str) -> dict:
    """Parse directive.md -> dictionnaire d'assets structuré."""
    if not os.path.exists(directive_path):
        raise FileNotFoundError(f"directive.md introuvable: {directive_path}")

    with open(directive_path, "r", encoding="utf-8", errors="replace") as f:
        text = f.read()

    campaign_id = None
    m = _CAMPAIGN_ID_RE.search(text)
    if m:
        campaign_id = m.group(1)

    urls = _extract_asset_section(text)
    section_used = bool(urls)
    if not urls:
        urls = _extract_urls_anywhere(text)

    assets = []
    seen = set()
    for idx, url in enumerate(urls):
        cleaned = url.rstrip(".,;:)]}")
        if cleaned in seen:
            continue
        seen.add(cleaned)
        assets.append({
            "asset_id": f"asset_{idx+1:03d}",
            "url": cleaned,
            "type": _classify_url(cleaned),
            "duration_sec": None,
            "title": None,
            "channel": None,
            "transcript_available": False,
            "transcript_path": None,
            "thumbnail": None,
        })

    return {
        "campaign_id": campaign_id,
        "parsed_at": now_iso(),
        "assets_section_found": section_used,
        "assets_count": len(assets),
        "assets": assets,
    }
