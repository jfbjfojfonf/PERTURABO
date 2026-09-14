"""
libs/siege_initializer.py — Initialisation d'un siège CLIPPING
===============================================================

Vérifie les 4 inputs du Warsmith avant de déclencher liber_clipping.json.
Règles :
  - directive.md doit exister dans ARCHIVUM/campaign/
  - reference_clip.json doit exister dans ARCHIVUM/campaign/
  - platform ∈ {youtube, tiktok, instagram}
  - n_angles >= 1
  - Un siège déjà actif bloque le démarrage (campaign/ est singulier — hérésie sinon)

Usage:
  from libs.siege_initializer import SiegeInitializer
  init = SiegeInitializer()
  result = init.validate(directive_path, reference_clip_path, platform, market, n_angles)
"""

import json
import os
from datetime import datetime, timezone

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_FORGE_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(_SCRIPT_DIR)))

VALID_PLATFORMS = ["youtube", "tiktok", "instagram"]


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class SiegeInitializer:
    def __init__(self, forge_root: str = _FORGE_ROOT):
        self.forge_root = forge_root
        self.campaign_dir = os.path.join(forge_root, "ARCHIVUM", "campaign")

    def generate_siege_id(self) -> str:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        return f"siege_{ts}"

    def validate(self, directive_path: str, reference_clip_path: str,
                 platform_target: str, market_target: str, n_angles: int) -> dict:
        errors = []

        if not os.path.isabs(directive_path):
            directive_path = os.path.join(self.campaign_dir, os.path.basename(directive_path))
        if not os.path.isabs(reference_clip_path):
            reference_clip_path = os.path.join(self.campaign_dir, os.path.basename(reference_clip_path))

        if not os.path.exists(directive_path):
            errors.append(f"directive.md introuvable: {directive_path}")
        if not os.path.exists(reference_clip_path):
            errors.append(f"reference_clip.json introuvable: {reference_clip_path}")

        if platform_target not in VALID_PLATFORMS:
            errors.append(f"platform_target invalide '{platform_target}' — attendu: {VALID_PLATFORMS}")

        if not market_target:
            errors.append("market_target vide — requis (ex: us_young_english)")

        try:
            n = int(n_angles)
            if n < 1:
                errors.append(f"n_angles doit être >= 1 (reçu: {n})")
        except (TypeError, ValueError):
            errors.append(f"n_angles invalide: {n_angles}")

        if os.path.exists(os.path.join(self.forge_root, "liber_clipping.json")):
            with open(os.path.join(self.forge_root, "liber_clipping.json"), "r", encoding="utf-8") as f:
                existing = json.load(f)
            if existing.get("campaign_status") == "active":
                errors.append("Campagne déjà active — fermer le siège en cours avant "
                              "d'en démarrer un nouveau (campaign/ est singulier)")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "inputs": {
                "directive_path": directive_path,
                "reference_clip_path": reference_clip_path,
                "platform_target": platform_target,
                "market_target": market_target,
                "n_angles": int(n_angles) if errors else int(n_angles),
            },
        }
