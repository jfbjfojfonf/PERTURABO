"""
libs/fit_scorer.py — Score fit plateforme × marché × niche (F02_TYRANT_CAMP)
============================================================================

Score sur 0-10 le fit campagne/plateforme et campagne/marché, à partir
des profils disponibles dans ARCHIVUM/platform_generator/ et
ARCHIVUM/market_generator/ (fichiers .md) + cartographie F00_CAPTEURS si présente.

Le scoring en mode auto est indicatif — l'IRON affinera en Phase 2.
Chaque assertion doit rester tracée (aucun chiffre inventé, hérésie "verdict sans preuve").

Usage:
  from fit_scorer import FitScorer
  scorer = FitScorer(forge_root)
  result = scorer.score(platform_target, market_target, cartographie=None)
"""

import os
import re


class FitScorer:
    def __init__(self, forge_root: str):
        self.forge_root = forge_root
        self.platform_dir = os.path.join(forge_root, "ARCHIVUM", "platform_generator")
        self.market_dir = os.path.join(forge_root, "ARCHIVUM", "market_generator")

    def _read_profile(self, d: str, slug: str) -> str:
        """Lit le profil {slug}.md dans le dossier donné (vide si absent)."""
        path = os.path.join(d, f"{slug}.md")
        if not os.path.exists(path):
            return ""
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()

    def score(self, platform_target: str, market_target: str,
              cartographie: dict = None) -> dict:
        platform_profile = self._read_profile(self.platform_dir, f"{platform_target}_profile")
        market_profile = self._read_profile(self.market_dir, f"{market_target}")

        # Scores de base : neutres si profils absents (à remplir par le Warsmith)
        platform_fit = 5
        market_fit = 5

        # Indices simples depuis les profils (l'IRON affine)
        if platform_profile:
            if re.search(r"shorts|short-form", platform_profile, re.IGNORECASE):
                platform_fit += 1
            if re.search(r"clipping|clip", platform_profile, re.IGNORECASE):
                platform_fit += 1
            platform_fit = min(platform_fit, 10)

        if market_profile:
            market_fit = 6  # profil marché présent = fit présumé bon
            if re.search(r"young|jeune|gen.?z", market_profile, re.IGNORECASE):
                market_fit += 1
            market_fit = min(market_fit, 10)

        saturation = "unknown"
        cpm_expected = None
        budget_remaining = None

        if cartographie:
            whop = cartographie.get("whop_scan", {})
            cpm_expected = whop.get("cpm_expected")
            budget_remaining = whop.get("campaign_budget_remaining_estimate")
            percep = cartographie.get("niche_perception", {})
            saturated = percep.get("saturated_angles", [])
            unsat = percep.get("undersaturated_angles", [])
            if unsat and not saturated:
                saturation = "low"
            elif saturated and not unsat:
                saturation = "high"
            else:
                saturation = "medium"

        return {
            "campaign_fit_platform": platform_fit,
            "campaign_fit_market": market_fit,
            "campaign_budget_remaining": budget_remaining,
            "cpm_expected": cpm_expected,
            "saturation_level": saturation,
            "evidence": {
                "platform_profile_present": bool(platform_profile),
                "market_profile_present": bool(market_profile),
                "cartographie_present": bool(cartographie),
            },
        }
