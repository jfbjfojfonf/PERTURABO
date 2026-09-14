"""
libs/duration_guard.py — Garde des durées par plateforme (F03_SOURCE_HUNTER)
============================================================================

Règle verrouillée : chaque segment suggéré doit rester dans la fourchette
[clip_min_duration, clip_max_duration] de la plateforme cible (profil
ARCHIVUM/platform_generator/{platform}_profile.md). Sortir de la fourchette
= hérésie (le segment ne sera pas un clip valide sur la plateforme).

En mode auto, si le profil plateforme est absent, on applique les défauts
déclarés du forge (DEFAULTS) — jamais de chiffre inventé au-delà.

Usage:
  from duration_guard import DurationGuard
  guard = DurationGuard(forge_root)
  lo, hi = guard.bounds("youtube")
  ok, msg = guard.validate(start_sec, end_sec, platform)
"""

import os
import re

# Défauts déclarés (plateformes du forge CLIPPING) — remplacés dès que le
# profil {platform}_profile.md est peuplé dans ARCHIVUM/platform_generator/
DEFAULTS = {
    "youtube": {"min": 15, "max": 45},
    "tiktok": {"min": 15, "max": 30},
    "instagram": {"min": 15, "max": 30},
}

_FALLBACK = {"min": 15, "max": 45}


class DurationGuard:
    def __init__(self, forge_root: str):
        self.platform_dir = os.path.join(forge_root, "ARCHIVUM", "platform_generator")

    def _profile(self, platform: str) -> str:
        path = os.path.join(self.platform_dir, f"{platform}_profile.md")
        if not os.path.exists(path):
            return ""
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()

    def bounds(self, platform: str) -> tuple[int, int]:
        """Fourchette [min, max] en secondes pour la plateforme."""
        base = DEFAULTS.get(platform, _FALLBACK)
        lo, hi = base["min"], base["max"]
        profile = self._profile(platform)
        for key in ("clip_min_duration", "min_duration", "min_sec"):
            m = re.search(rf"{key}\s*[:=]\s*(\d+)", profile, re.IGNORECASE)
            if m:
                lo = int(m.group(1))
                break
        for key in ("clip_max_duration", "max_duration", "max_sec"):
            m = re.search(rf"{key}\s*[:=]\s*(\d+)", profile, re.IGNORECASE)
            if m:
                hi = int(m.group(1))
                break
        return lo, hi

    def validate(self, start_sec, end_sec, platform: str) -> tuple[bool, str]:
        """Vérifie qu'une fenêtre [start, end] reste dans la fourchette."""
        lo, hi = self.bounds(platform)
        duration = float(end_sec) - float(start_sec)
        if duration < lo:
            return False, f"segment {duration:.0f}s < min {lo}s (plateforme {platform})"
        if duration > hi:
            return False, f"segment {duration:.0f}s > max {hi}s (plateforme {platform})"
        return True, ""
