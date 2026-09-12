"""
libs/reference_style_extractor.py — ADN style du clip de référence
==================================================================

Extrait le bloc `reference_style` du production_pack : pacing, energy_level,
cut_density, color_palette, text_treatment. C'est la MATIÈRE PREMIÈRE BRUTE
observée sur le clip de référence — OMNIS_WATCH applique ses presets coloring
en plus. PERTURABO ne décide jamais du style final (note const du schéma).

Ordre de résolution :
  1. ARCHIVUM/campaign/reference_style.json   (l'IRON/l'opérateur l'a écrit
     après vision du clip de référence)      -> observed: true
  2. reference_clip.json → bloc "reference_style" -> observed: true
  3. Sinon : valeurs par défaut honnêtes      -> observed: false
     + prompt de vision IRON écrit dans IN/reference_style_prompt.json
     (la vision pixel + interprétation IRON reste le chemin idéal)

Le schéma exige reference_style.note == const fixé — le flag "observed"
est un champ additionnel (additionalProperties autorisé) qui permet à
F05 et au Warsmith de savoir si l'ADN est réel ou par défaut.
"""

import json
import os

NOTE_CONST = ("OMNIS_WATCH applique ses presets coloring en plus - "
              "PERTURABO transmet seulement l'ADN observe du clip de reference.")

DEFAULTS = {
    "pacing": "non observe (defaut)",
    "energy_level": "modere",
    "cut_density": 0,
    "color_palette": ["non_observe"],
    "text_treatment": "non observe (defaut)",
}

REQUIRED = ["pacing", "energy_level", "cut_density", "color_palette", "text_treatment"]


class ReferenceStyleExtractor:
    def __init__(self, archivum_dir: str, in_dir: str):
        self._archivum = archivum_dir
        self._in_dir = in_dir

    # ------------------------------------------------------------------
    def extract(self) -> dict:
        style = self._from_campaign_file()
        if style is not None:
            return self._finalize(style, observed=True)

        style = self._from_reference_clip()
        if style is not None:
            return self._finalize(style, observed=True)

        self._write_vision_prompt()
        return self._finalize(dict(DEFAULTS), observed=False)

    # ------------------------------------------------------------------
    def _from_campaign_file(self) -> dict | None:
        path = os.path.join(self._archivum, "campaign", "reference_style.json")
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8-sig") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            return None
        return data if self._has_required(data) else None

    def _from_reference_clip(self) -> dict | None:
        path = os.path.join(self._archivum, "campaign", "reference_clip.json")
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8-sig") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            return None
        style = data.get("reference_style")
        if not isinstance(style, dict) or not self._has_required(style):
            return None
        style.pop("url", None)
        return style

    def _has_required(self, style: dict) -> bool:
        return all(key in style for key in REQUIRED)

    def _finalize(self, style: dict, observed: bool) -> dict:
        if "observed" not in style:
            style["observed"] = observed
        style["note"] = NOTE_CONST
        return style

    # ------------------------------------------------------------------
    def _write_vision_prompt(self):
        ref_clip = os.path.join(self._archivum, "campaign", "reference_clip.json")
        url = ""
        if os.path.exists(ref_clip):
            try:
                with open(ref_clip, "r", encoding="utf-8") as f:
                    url = json.load(f).get("url", "")
            except (json.JSONDecodeError, OSError):
                pass
        prompt = {
            "mission": "Vision du clip de référence (F05_PACKAGER) — décrire "
                       "l'ADN STYLE brut pour reference_style.json. "
                       "PERTURABO ne décide jamais du style final — il observe "
                       "et transmet la matière première à OMNIS_WATCH.",
            "clip_reference": url or "URL à fournir",
            "taches": [
                "pacing : rythme perçu (string)",
                "energy_level : calme | modere | intense | frenetique",
                "cut_density : nb de coupes par minute (number)",
                "color_palette : couleurs dominantes (array de strings)",
                "text_treatment : style des sous-titres/texte affiché (string)",
            ],
            "output_attendu": "ARCHIVUM/campaign/reference_style.json "
                              "(les 5 clés REQUIRED + observed: true)",
            "note": "Une seule source de vérité : le clip de référence fourni "
                    "par la campagne. Ne pas inventer si non visible.",
        }
        os.makedirs(self._in_dir, exist_ok=True)
        with open(os.path.join(self._in_dir, "reference_style_prompt.json"),
                  "w", encoding="utf-8") as f:
            json.dump(prompt, f, indent=2, ensure_ascii=False)
