"""
libs/channel_performance_updater.py — perfs par compte (F06)
============================================================

Met à jour `ARCHIVUM/channels/<account_slug>/performance.json` à chaque
événement : pack posté (--post), vues relevées (--views), payout
enregistré (--payout).

Structure :
  {
    "account_slug": "...",
    "packs": [
      {"campaign_id", "angle_id", "posted_at", "views_1h", "views_24h", "payout"}
    ],
    "totals": {"packs_count", "views_24h_total", "payout_total"}
  }

Le dossier du compte est créé s'il n'existe pas (le Warsmith crée ses
comptes au fil du temps).
"""

import json
import os


class ChannelPerformanceUpdater:
    def __init__(self, channels_dir: str):
        self._channels = channels_dir

    # ------------------------------------------------------------------
    def _path(self, slug: str) -> str:
        slug = slug.strip()
        return os.path.join(self._channels, slug, "performance.json")

    def _load(self, slug: str) -> dict:
        path = self._path(slug)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8-sig") as f:
                return json.load(f)
        return {
            "account_slug": slug,
            "packs": [],
            "totals": {"packs_count": 0, "views_24h_total": 0, "payout_total": 0},
        }

    def _save(self, slug: str, data: dict):
        path = self._path(slug)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _find(self, data: dict, angle_id: str) -> dict | None:
        for pack in data["packs"]:
            if pack.get("angle_id") == angle_id:
                return pack
        return None

    # ------------------------------------------------------------------
    def record_pack(self, slug: str, campaign_id: str, angle_id: str,
                    posted_at: str):
        if not slug or not slug.strip():
            return
        data = self._load(slug)
        entry = self._find(data, angle_id)
        if entry is None:
            entry = {
                "campaign_id": campaign_id,
                "angle_id": angle_id,
                "posted_at": posted_at,
                "views_1h": None,
                "views_24h": None,
                "payout": None,
            }
            data["packs"].append(entry)
            data["totals"]["packs_count"] = len(data["packs"])
        self._save(slug, data)

    def update_views(self, slug: str, angle_id: str, views_1h: int, views_24h: int):
        if not slug or not slug.strip():
            return
        data = self._load(slug)
        entry = self._find(data, angle_id)
        if entry is None:
            return
        entry["views_1h"] = views_1h
        entry["views_24h"] = views_24h
        data["totals"]["views_24h_total"] = sum(
            p.get("views_24h") or 0 for p in data["packs"])
        self._save(slug, data)

    def update_payout(self, slug: str, angle_id: str, payout: float):
        if not slug or not slug.strip():
            return
        data = self._load(slug)
        entry = self._find(data, angle_id)
        if entry is None:
            return
        entry["payout"] = payout
        data["totals"]["payout_total"] = sum(
            p.get("payout") or 0 for p in data["packs"])
        self._save(slug, data)
