"""
libs/gate_validator.py — Vérification des outputs attendus à chaque Porte
=========================================================================

Avant de laisser le Warsmith valider une porte, l'Orchestrateur vérifie
que les artefacts attendus sont présents (gate_validator.py).

Porte 1 : F01_SCOUT/OUT/source_specimen.json + F02_TYRANT_CAMP/OUT/campaign_verdict.json
Porte 2 : F02_TYRANT_CAMP/OUT/angles.json (ou ANGLESMITH/OUT/angles.json)
Porte 3 : F03_SOURCE_HUNTER/OUT/source_specimen_*.json (N) + F04_COPYWRITER/OUT/text_payload_*.json (N)
Porte 4 : F05_PACKAGER/OUT/production_pack_*.json (N)

Usage:
  from libs.gate_validator import GateValidator
  v = GateValidator()
  ok, missing = v.validate_porte(1, n_angles=10)
"""

import glob
import json
import os

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_FORGE_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(_SCRIPT_DIR)))

FREGATE_OUT = {
    "F01": os.path.join(_FORGE_ROOT, "F01_SCOUT", "OUT"),
    "F02": os.path.join(_FORGE_ROOT, "F02_TYRANT_CAMP", "OUT"),
    "ANGLESMITH": os.path.join(_FORGE_ROOT, "ANGLESMITH", "OUT"),
    "F03": os.path.join(_FORGE_ROOT, "F03_SOURCE_HUNTER", "OUT"),
    "F04": os.path.join(_FORGE_ROOT, "F04_COPYWRITER", "OUT"),
    "F05": os.path.join(_FORGE_ROOT, "F05_PACKAGER", "OUT"),
    "F06": os.path.join(_FORGE_ROOT, "F06_TRACKER", "OUT"),
}


class GateValidator:
    def __init__(self, forge_root: str = _FORGE_ROOT):
        self.forge_root = forge_root
        self.out_dirs = {k: os.path.join(forge_root, *v.replace(_FORGE_ROOT, "").strip(os.sep).split(os.sep))
                         if v else None for k, v in FREGATE_OUT.items()}

    def _mode(self) -> str:
        """Profil actif (whop | logo) — lu depuis liber_clipping.json."""
        try:
            path = os.path.join(self.forge_root, "liber_clipping.json")
            with open(path, "r", encoding="utf-8") as f:
                return (json.load(f).get("mode") or "whop").lower()
        except (OSError, json.JSONDecodeError):
            return "whop"

    def _sub_mode(self) -> str:
        """Sous-mode (meme | humour | informatif) — le mode meme est signalé par
        ARCHIVUM/campaign/keyword.txt (doctrine F01/F03 SKIP)."""
        kw_path = os.path.join(self.forge_root, "ARCHIVUM", "campaign", "keyword.txt")
        if os.path.exists(kw_path):
            try:
                with open(kw_path, "r", encoding="utf-8") as f:
                    if f.read().strip():
                        return "meme"
            except OSError:
                pass
        return ""

    def _resolve(self, rel: str) -> str:
        return os.path.join(self.forge_root, rel)

    def validate_porte(self, gate_id, n_angles: int = None) -> tuple[bool, list[str]]:
        gate_id = str(gate_id)
        missing = []
        sub_mode = self._sub_mode()

        if gate_id == "1":
            # Mode meme : F01/F02 SKIP — le scan F00 meme_virality_*.json suffit.
            if sub_mode == "meme":
                if not glob.glob(self._resolve("F00_CAPTEURS/OUT/meme_virality_*.json")):
                    missing.append("F00_CAPTEURS/OUT/meme_virality_<keyword>.json")
            else:
                for rel in [
                    "F01_SCOUT/OUT/source_specimen.json",
                    "F02_TYRANT_CAMP/OUT/campaign_verdict.json",
                ]:
                    if not os.path.exists(self._resolve(rel)):
                        missing.append(rel)

        elif gate_id == "2":
            candidates = [
                "F02_TYRANT_CAMP/OUT/angles.json",
                "ANGLESMITH/OUT/angles.json",
            ]
            if not any(os.path.exists(self._resolve(c)) for c in candidates):
                missing.append("angles.json (ANGLESMITH ou F02_TYRANT_CAMP)")

        elif gate_id == "3":
            n = n_angles or 0
            # Mode LOGO : pas de F03 (le clip vient du Warsmith) — seuls les
            # text_payloads F04 sont requis. Mode whop : F03 + F04 requis.
            if self._mode() != "logo":
                for i in range(1, n + 1):
                    if not glob.glob(self._resolve("F03_SOURCE_HUNTER/OUT/source_specimen_*.json")):
                        missing.append("F03_SOURCE_HUNTER/OUT/source_specimen_<angle>.json")
                        break
            for i in range(1, n + 1):
                if not glob.glob(self._resolve("F04_COPYWRITER/OUT/text_payload_*.json")):
                    missing.append("F04_COPYWRITER/OUT/text_payload_<angle>.json")
                    break

        elif gate_id == "4":
            packs = glob.glob(self._resolve("F05_PACKAGER/OUT/production_pack_*.json"))
            if not packs:
                missing.append("F05_PACKAGER/OUT/production_pack_<angle>.json")
            else:
                # Mode LOGO : schéma logo ; sinon schéma whop canonique.
                if self._mode() == "logo":
                    schema_path = self._resolve(
                        "PROFILES/logo/CONTRACTS/production_pack_schema_logo.json")
                else:
                    schema_path = self._resolve("CONTRACTS/production_pack_schema.json")
                for pack in packs:
                    if not self._validate_pack_against_schema(pack, schema_path):
                        missing.append(f"{os.path.basename(pack)} — schéma invalide")

        else:
            missing.append(f"Porte inconnue: {gate_id}")

        return (len(missing) == 0, missing)

    def _validate_pack_against_schema(self, pack_path: str, schema_path: str) -> bool:
        """Validation minimale (présence des blocs requis) — pas une lib jsonschema."""
        try:
            with open(pack_path, "r", encoding="utf-8") as f:
                pack = json.load(f)
            with open(schema_path, "r", encoding="utf-8") as f:
                schema = json.load(f)
            required = schema.get("required", [])
            return all(k in pack for k in required)
        except (json.JSONDecodeError, OSError):
            return False

    def fregate_out_dir(self, code: str) -> str:
        return FREGATE_OUT.get(code)
