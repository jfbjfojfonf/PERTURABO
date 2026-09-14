"""
libs/blue_ocean_finder.py — Identification des océans bleus (F02_TYRANT_CAMP)
=============================================================================

Lit ARCHIVUM/demons/<demon_id>.json (Démons cartographiés par TYRANT prospectif)
et propose les territoires adjacents non saturés pour une campagne.

Règles strictes (TRACKING F02) :
  - Profondeur océan bleu : 1 couche maximum (hérésie au-delà)
  - Saturation : territoire marqué "low" ou "medium" = éligible ; "high" = rejeté
  - Le re-ciblage ne change pas la source — il change l'angle d'attaque narratif

Usage:
  from blue_ocean_finder import BlueOceanFinder
  finder = BlueOceanFinder()
  oceans = finder.find_for_campaign(demons_dir, dominant_emotion=None)
"""

import json
import os

VALID_DEPTHS = {1}
ELIGIBLE_SATURATION = {"low", "medium"}


class BlueOceanFinder:
    def __init__(self, forge_root: str):
        self.forge_root = forge_root
        self.demons_dir = os.path.join(forge_root, "ARCHIVUM", "demons")

    def load_demons(self) -> list[dict]:
        """Charge tous les ARCHIVUM/demons/<demon_id>.json existants."""
        if not os.path.isdir(self.demons_dir):
            return []
        demons = []
        for fn in sorted(os.listdir(self.demons_dir)):
            if not fn.endswith(".json"):
                continue
            path = os.path.join(self.demons_dir, fn)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    demon = json.load(f)
                demon["_file"] = fn
                demons.append(demon)
            except (json.JSONDecodeError, OSError):
                continue
        return demons

    def find_for_campaign(self, demon_id: str = None, dominant_emotion: str = None) -> list[dict]:
        """
        Retourne les blue_ocean_unlocked éligibles (1 couche, saturation low/medium).
        Filtre sur demon_id si fourni, sinon sur dominant_emotion.
        """
        demons = self.load_demons()
        if not demons:
            return []

        candidates = []
        for demon in demons:
            if demon_id and demon.get("demon_id") != demon_id:
                continue
            if dominant_emotion and demon.get("dominant_emotion") != dominant_emotion:
                continue
            for ocean in demon.get("blue_ocean_unlocked", []):
                depth = ocean.get("blue_ocean_depth")
                if depth not in VALID_DEPTHS:
                    continue  # profondeur > 1 = hérésie, on ne propose jamais
                if ocean.get("estimated_saturation") not in ELIGIBLE_SATURATION:
                    continue  # high = rejeté
                candidates.append({
                    "territory": ocean.get("territory"),
                    "rationale": ocean.get("rationale"),
                    "estimated_saturation": ocean.get("estimated_saturation"),
                    "blue_ocean_depth": depth,
                    "from_demon": demon.get("demon_id"),
                })
        return candidates
