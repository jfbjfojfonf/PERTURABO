"""
libs/learnings_weight.py — Ponderation des angles par learnings (ANGLESMITH)
===========================================================================

Poids nul (neutre = 1.0) si < 50 packs executes dans learnings.json.
Activation progressive ensuite : chaque angle_family est pondere selon
sa performance reelle dans angle_performance.json.

Usage:
  from learnings_weight import LearningsWeight
  lw = LearningsWeight(forge_root)
  weight, eligible = lw.weight_for_family("reframing")
"""

import json
import os


class LearningsWeight:
    def __init__(self, forge_root: str):
        self.forge_root = forge_root
        self._learnings = None
        self._performance = None

    def _load_learnings(self) -> dict:
        if self._learnings is None:
            path = os.path.join(self.forge_root, "ARCHIVUM", "learnings", "learnings.json")
            self._learnings = {}
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    self._learnings = json.load(f) or {}
        return self._learnings

    def _load_performance(self) -> dict:
        if self._performance is None:
            path = os.path.join(self.forge_root, "ARCHIVUM", "angles", "angle_performance.json")
            self._performance = {}
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    self._performance = json.load(f) or {}
        return self._performance

    def eligible(self) -> bool:
        learnings = self._load_learnings()
        return bool(learnings.get("eligible_for_weighting")) or \
            int(learnings.get("cumulative_packs_executed", 0) or 0) >= 50

    def weight_for_family(self, angle_family: str) -> float:
        """Retourne le poids (1.0 neutre) pour une famille d'angle."""
        if not self.eligible():
            return 1.0
        perf = self._load_performance()
        for entry in perf.get("angle_performance", []) or []:
            if entry.get("angle_family") == angle_family:
                w = entry.get("weight")
                if isinstance(w, (int, float)) and w > 0:
                    return float(w)
        return 1.0
