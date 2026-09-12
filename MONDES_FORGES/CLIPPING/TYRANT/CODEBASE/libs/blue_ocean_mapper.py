"""
libs/blue_ocean_mapper.py — Cartographie océans bleus 1 couche (TYRANT prospectif)
=================================================================================

Depuis l'émotion dominante d'un Démon, propose des territoires adjacents
non saturés — TOUJOURS à depth=1 (jamais 2 couches, hérésie).

La cartographie est un cadre de départ : l'IRON affinera avec le scraping.
Les territoires proposés restent sur la même forme narrative que le Démon.

Usage:
  from blue_ocean_mapper import BlueOceanMapper
  mapper = BlueOceanMapper()
  oceans = mapper.map_for_emotion("drame")
"""

_MAP = {
    "drame": [
        {"territory": "maladie & diagnostic", "rationale": "même forme narrative drame, récit personnel vécu",
         "estimated_saturation": "medium", "blue_ocean_depth": 1},
        {"territory": "perte & deuil", "rationale": "drame intime non saturé sur la source",
         "estimated_saturation": "low", "blue_ocean_depth": 1},
    ],
    "joie": [
        {"territory": "petites victoires du quotidien", "rationale": "joie mainstream, angle sous-exploité",
         "estimated_saturation": "low", "blue_ocean_depth": 1},
    ],
    "outrage": [
        {"territory": "injustices du système", "rationale": "outrage re-ciblé sur des faits non saturés",
         "estimated_saturation": "medium", "blue_ocean_depth": 1},
    ],
    "inspiration": [
        {"territory": "comebacks anonymes", "rationale": "inspiration hors figures connues",
         "estimated_saturation": "low", "blue_ocean_depth": 1},
    ],
    "peur": [
        {"territory": "dangers invisibles du quotidien", "rationale": "peur mainstream, angle adjacent",
         "estimated_saturation": "medium", "blue_ocean_depth": 1},
    ],
    "admiration": [
        {"territory": "maîtres anonymes", "rationale": "admiration des artisans inconnus",
         "estimated_saturation": "low", "blue_ocean_depth": 1},
    ],
    "humour": [
        {"territory": "absurde du quotidien", "rationale": "humour re-ciblé sur des situations banales",
         "estimated_saturation": "medium", "blue_ocean_depth": 1},
    ],
}


class BlueOceanMapper:
    def map_for_emotion(self, emotion: str | None) -> list[dict]:
        if not emotion:
            return []
        return [dict(o) for o in _MAP.get(emotion, [])]

    def enforce_max_depth(self, oceans: list[dict]) -> list[dict]:
        """Garantit depth <= 1 partout (hérésie sinon)."""
        for o in oceans:
            if o.get("blue_ocean_depth", 1) != 1:
                o["blue_ocean_depth"] = 1
                o["_depth_clamped"] = True
        return oceans
