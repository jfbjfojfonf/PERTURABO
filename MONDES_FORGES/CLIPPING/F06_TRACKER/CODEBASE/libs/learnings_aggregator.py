"""
libs/learnings_aggregator.py — boucle learnings.json (F06)
==========================================================

À la fermeture de campagne, agrège les résultats des packs dans
`ARCHIVUM/learnings/learnings.json` en PRÉSERVANT les campagnes
précédentes (append/update, jamais d'écrasement).

  - cumulative_packs_executed  : somme cumulée (toutes campagnes)
  - eligible_for_weighting     : true seulement si >= 50 packs cumulés
    (hérésie sinon — ANGLESMITH lit ce flag)
  - angle_performance[]        : moyennes vues 24h + payout par
    combinaison (angle_family, emotion_mode, engagement_type,
    reframe_dim, platform, market) — clé composite
  - weight                     : 1.0 = neutre ; activation PROGRESSIVE
    quand eligible (référence = moyenne globale des payouts)
  - campaign_history[]         : une entrée par campagne fermée

Règle v1 (progressive) : weight = clamp(1 + 0.25 * (moy_grp / moy_glob - 1),
0.5, 2.0) si eligible, sinon 1.0 pour tous.
"""

import json
import os
from datetime import datetime, timezone

WEIGHT_THRESHOLD = 50

GROUP_KEYS = ["angle_family", "emotion_mode", "engagement_type",
              "reframe_dim", "platform", "market"]


class LearningsAggregator:
    def __init__(self, learnings_path: str):
        self._path = learnings_path

    # ------------------------------------------------------------------
    def _load(self) -> dict:
        if not os.path.exists(self._path):
            return {
                "cumulative_packs_executed": 0,
                "eligible_for_weighting": False,
                "angle_performance": [],
                "campaign_history": [],
            }
        with open(self._path, "r", encoding="utf-8-sig") as f:
            return json.load(f)

    # ------------------------------------------------------------------
    def aggregate(self, log: dict) -> dict:
        learnings = self._load()
        existing = {
            _composite_key(e): e
            for e in learnings.get("angle_performance", [])
        }

        groups = {}
        for pack in log.get("packs", []):
            key = _composite_key(pack)
            bucket = groups.setdefault(key, [])
            bucket.append(pack)

        global_payouts = [p.get("payout_observed") or 0 for p in log["packs"]]
        global_mean = (
            sum(global_payouts) / len(global_payouts) if global_payouts else 0.0)

        for key, packs in groups.items():
            sample = packs[0]
            mean_views = sum(p.get("views_24h") or 0 for p in packs) / len(packs)
            mean_payout = sum(p.get("payout_observed") or 0 for p in packs) / len(packs)

            entry = existing.get(key)
            if entry is None:
                entry = {k: sample.get(k) for k in GROUP_KEYS}
                entry.update({
                    "packs_count": 0,
                    "mean_views_24h": 0,
                    "mean_payout": 0,
                    "weight": 1.0,
                })
                existing[key] = entry

            entry["packs_count"] += len(packs)
            entry["mean_views_24h"] = round(mean_views, 1)
            entry["mean_payout"] = round(mean_payout, 2)

        learnings["angle_performance"] = list(existing.values())

        cumulative = learnings.get("cumulative_packs_executed", 0) + len(log["packs"])
        eligible = cumulative >= WEIGHT_THRESHOLD
        learnings["cumulative_packs_executed"] = cumulative
        learnings["eligible_for_weighting"] = eligible

        for entry in learnings["angle_performance"]:
            if eligible and global_mean > 0 and entry.get("packs_count", 0) > 0:
                ratio = entry["mean_payout"] / global_mean
                weight = 1.0 + 0.25 * (ratio - 1.0)
                entry["weight"] = round(max(0.5, min(2.0, weight)), 2)
            else:
                entry["weight"] = 1.0

        history = learnings.get("campaign_history", [])
        history.append({
            "campaign_id": log.get("campaign_id"),
            "closed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "packs_count": len(log["packs"]),
            "total_payout": round(sum(global_payouts), 2),
        })
        learnings["campaign_history"] = history
        return learnings


def _composite_key(entry: dict) -> tuple:
    return tuple(str(entry.get(k)) for k in GROUP_KEYS)
