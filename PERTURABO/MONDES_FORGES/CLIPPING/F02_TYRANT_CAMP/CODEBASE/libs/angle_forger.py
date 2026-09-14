"""
libs/angle_forger.py — Forge combinatoire des N angles (ANGLESMITH)
===================================================================

ANGLESMITH forge N angles repartis sur 2 zones :
  - X angles directs (territoire dominant du Demon, verdict.demon_analysis)
  - Y angles ocean bleu (re-ciblage non sature, MEME source, depth <= 1)

Chaque angle combine 4 axes : angle_family, emotion_mode,
engagement_type, reframe_dim.

Regle anti-cannibale : 2 angles trop proches = fusion ou kill.
2 axes differenciants minimum entre chaque angle.

Usage:
  from angle_forger import AngleForger
  forger = AngleForger()
  angles = forger.forge(n=10, campaign_id=..., verdict=...)
  angles = forger.forge(n=5, campaign_id=..., verdict=...,
                        spin_humour="<sens humour operateur>")
"""

_AXES = {
    "angle_family": ["reframing", "emotion", "engagement", "structural"],
    "emotion_mode": ["tension", "joie", "inspiration", "outrage", "admiration"],
    "engagement_type": ["question", "confirmation", "assertion", "cliffhanger"],
    "reframe_dim": [
        "victime_vers_survivant",
        "anonyme_vers_incroyable",
        "banal_vers_suspect",
        "fait_vers_absurde",
        "echec_vers_lecon",
        "seul_vers_communaute",
        "cache_vers_revele",
        "ordinaire_vers_extraordinaire",
    ],
}

# Registre humour-compatible quand un spin humour operateur est fourni
_HUMOUR_EMOTIONS = ["joie", "tension"]
_HUMOUR_REFRAMES = ["fait_vers_absurde", "banal_vers_suspect"]

_MIN_DIFFERENT_AXES = 2

# Mode MEME : emotions pop-culture (regle anti-spam : 2 max par emotion)
_MEME_EMOTIONS = [
    "poignant", "drole", "choc", "tendu", "emerveille",
    "nostalgique", "absurde", "fier", "indigne", "tendre",
]
# Registre MEME humour-compatible quand un spin humour operateur est fourni
_HUMOUR_MEME_EMOTIONS = [
    "drole", "absurde", "choc", "ironique", "tendu",
    "nostalgique", "emerveille", "fier",
]
_MEME_REFRAFES = [
    "ordinaire_vers_extraordinaire",
    "echec_vers_lecon",
    "fait_vers_absurde",
    "banal_vers_suspect",
    "cache_vers_revele",
    "seul_vers_communaute",
]
_MEME_DURATION_DEFAULT = (5, 7)


class AngleForger:
    def __init__(self):
        self._axis_names = list(_AXES.keys())

    def _axes_different(self, a: dict, b: dict) -> int:
        return sum(1 for ax in self._axis_names if a.get(ax) != b.get(ax))

    def _anti_cannibale(self, angles: list[dict], candidate: dict) -> bool:
        """True si le candidat respecte 2 axes differenciants vs tous les autres."""
        for existing in angles:
            if self._axes_different(existing, candidate) < _MIN_DIFFERENT_AXES:
                return False
        return True

    def forge(self, n: int, campaign_id: str, verdict: dict = None,
              spin_humour: str = None) -> list[dict]:
        """Forge N angles uniques (anti-cannibale) avec zones direct/ocean bleu.
        spin_humour : si fourni, les angles sont declines dans un registre
        humour-compatible (joie/tension, absurde/suspect) et portent le champ
        humour_spin pour tracabilite."""
        verdict = verdict or {}
        demon = verdict.get("demon_analysis", {})
        oceans = demon.get("blue_ocean_unlocked", [])
        oceans = [o for o in oceans if str(o.get("blue_ocean_depth", 1)) == "1"]

        humour = bool(spin_humour)
        emotions = _HUMOUR_EMOTIONS if humour else _AXES["emotion_mode"]
        reframes = _HUMOUR_REFRAMES if humour else _AXES["reframe_dim"]

        n_blue = min(len(oceans), max(0, n // 3)) if oceans else 0
        n_direct = n - n_blue

        angles = []
        idx = 1

        # Zone direct : territoire dominant du Demon
        for family in _AXES["angle_family"]:
            for emotion in emotions:
                for engagement in _AXES["engagement_type"]:
                    for reframe in reframes:
                        if idx > n_direct:
                            break
                        candidate = {
                            "angle_id": f"A{idx:02d}",
                            "angle_family": family,
                            "emotion_mode": emotion,
                            "engagement_type": engagement,
                            "reframe_dim": reframe,
                            "zone": "direct",
                            "blue_ocean_reframe_applied": False,
                            "blue_ocean_depth": None,
                            "territory": demon.get("dominant_emotion"),
                            "weight": 1.0,
                        }
                        if humour:
                            candidate["humour_spin"] = spin_humour
                        if self._anti_cannibale(angles, candidate):
                            angles.append(candidate)
                            idx += 1
                        if idx > n_direct:
                            break
                    if idx > n_direct:
                        break
                if idx > n_direct:
                    break
            if idx > n_direct:
                break

        # Zone ocean bleu : re-ciblage 1 couche sur MEME source
        for territory in oceans:
            if idx > n:
                break
            if idx > n_blue + n_direct:
                break
            for family in ["reframing", "emotion"]:
                if idx > n:
                    break
                for engagement in ["question", "assertion"]:
                    if idx > n:
                        break
                    candidate = {
                        "angle_id": f"A{idx:02d}",
                        "angle_family": family,
                        "emotion_mode": (demon.get("dominant_emotion") or
                                         ("joie" if humour else "tension")),
                        "engagement_type": engagement,
                        "reframe_dim": "banal_vers_suspect",
                        "zone": "blue_ocean",
                        "blue_ocean_reframe_applied": True,
                        "blue_ocean_depth": 1,
                        "territory": territory.get("territory"),
                        "territory_rationale": territory.get("rationale"),
                        "weight": 1.0,
                    }
                    if humour:
                        candidate["humour_spin"] = spin_humour
                    if self._anti_cannibale(angles, candidate):
                        angles.append(candidate)
                        idx += 1

        return angles[:n]

    # ------------------------------------------------------------------
    def forge_meme(self, n: int, campaign_id: str,
                   keyword: str, virality: dict = None,
                   spin_humour: str = None) -> list[dict]:
        """Mode MEME : 5 angles forgés sur les stats réelles du scan F00
        (jamais sur un clip téléchargé). Chaque angle porte :
          - emotion        : emotion pop-culture (anti-spam, 2 max par emotion)
          - duration_sec_range : fourchette (défaut 5-7s)
          - meme_hook      : direction du fake post (A->B) suggérée
          - humour_spin    : si spin_humour fourni, les angles déclinent la
                             direction humouristique du Warsmith (traçabilité)
        Règle anti-spam : une même emotion au maximum 2 angles sur les 5."""
        virality = virality or {}
        # Calibration durée depuis la fourchette demandée (ou défaut 5-7s)
        dur = virality.get("duration_range_sec") or {}
        if isinstance(dur, (list, tuple)):
            dur = {"min": dur[0], "max": dur[1]}
        dur_lo = int(dur.get("min") or _MEME_DURATION_DEFAULT[0])
        dur_hi = int(dur.get("max") or _MEME_DURATION_DEFAULT[1])

        humour = bool(spin_humour)
        # Registre humour-compatible si spin fourni (anti-spam : 2 max quand même)
        emotions = (_HUMOUR_MEME_EMOTIONS if humour else list(_MEME_EMOTIONS))
        angles = []
        idx = 1
        emotion_count: dict[str, int] = {}

        for family in ["reframing", "emotion", "engagement"]:
            for reframe in _MEME_REFRAFES:
                if idx > n:
                    break
                for engagement in ["question", "assertion", "cliffhanger"]:
                    if idx > n:
                        break
                    # Choix d'émotion : priorité aux moins utilisées,
                    # jamais plus de 2 angles avec la même emotion
                    available = [e for e in emotions
                                 if emotion_count.get(e, 0) < 2]
                    if not available:
                        available = [e for e, c in emotion_count.items()
                                     if c < 2]
                    emotion = available[(idx - 1) % len(available)] \
                        if available else emotions[0]
                    emotion_count[emotion] = emotion_count.get(emotion, 0) + 1

                    candidate = {
                        "angle_id": f"A{idx:02d}",
                        "angle_family": family,
                        "emotion_mode": emotion,
                        "emotion": emotion,
                        "engagement_type": engagement,
                        "reframe_dim": reframe,
                        "zone": "direct",
                        "keyword": keyword,
                        "duration_sec_range": {"min": dur_lo, "max": dur_hi},
                        "meme_hook": _meme_hook(reframe, emotion),
                        "weight": 1.0,
                    }
                    if humour:
                        candidate["humour_spin"] = spin_humour
                    if self._anti_cannibale(angles, candidate):
                        angles.append(candidate)
                        idx += 1
                if idx > n:
                    break
            if idx > n:
                break

        return angles[:n]


def _meme_hook(reframe: str, emotion: str) -> str:
    """Direction de fake post A->B suggérée pour le reframe/émotion."""
    hooks = {
        "ordinaire_vers_extraordinaire": "[sujet] at school: -> [sujet] at home:",
        "echec_vers_lecon": "[sujet] fails: -> [sujet] learns:",
        "fait_vers_absurde": "[sujet] said it: -> [sujet] actually did it:",
        "banal_vers_suspect": "[sujet] looks normal: -> [sujet] is NOT normal:",
        "cache_vers_revele": "[sujet] before: -> [sujet] after:",
        "seul_vers_communaute": "[sujet] alone: -> [sujet] with everyone:",
    }
    base = hooks.get(reframe,
                     "[sujet] at [A]: -> [sujet] at [B]:")
    return f"{base} (emotion: {emotion})"
