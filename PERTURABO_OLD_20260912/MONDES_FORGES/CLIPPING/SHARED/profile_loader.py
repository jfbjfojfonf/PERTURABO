"""
profile_loader.py — Resolution du profil CLIPPING actif (whop ou logo)
======================================================================
Lu par les fregates qui dependent du profil (F00_CAPTEURS sites config, F05
schema_validator, F02 criteres verdict, F04 doctrine/systemprompt).

Le profil actif est decide au demarrage du siege (IW_CUSTOS --init-siege
--mode whop|logo) et ecrit dans liber_clipping.json (champ "mode").

Usage:
    from profile_loader import load_profile
    prof = load_profile()              # lit liber.mode (defaut "whop")
    schema_path = prof.resolve("pack_schema")
    sites_example = prof.resolve("capteurs_sites_example")
    doctrine = prof.resolve("copywriting_doctrine")
"""

import json
import os

_FORGE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIBER_PATH = os.path.join(_FORGE_ROOT, "liber_clipping.json")
PROFILES_DIR = os.path.join(_FORGE_ROOT, "PROFILES")
DEFAULT_MODE = "whop"


class Profile:
    def __init__(self, mode: str, manifest: dict):
        self.mode = mode
        self.manifest = manifest

    def resolve(self, key: str) -> str:
        """Retourne le chemin absolu d'une ressource du profil."""
        rel = self.manifest.get(key)
        if rel is None:
            raise KeyError(f"cle '{key}' absente du manifest profil '{self.mode}'")
        if os.path.isabs(rel):
            return rel
        # contracts_dir et pack_schema/doctrine/etc peuvent etre relatifs
        if key in ("pack_schema", "copywriting_doctrine",
                   "copywriter_systemprompt", "capteurs_sites_example"):
            base = self.manifest.get("contracts_dir", "CONTRACTS")
            return os.path.normpath(os.path.join(_FORGE_ROOT, base, rel))
        if key == "contracts_dir":
            return os.path.normpath(os.path.join(_FORGE_ROOT, rel))
        return os.path.normpath(os.path.join(_FORGE_ROOT, rel))

    @property
    def contracts_dir(self) -> str:
        return self.resolve("contracts_dir")

    @property
    def pack_nature(self) -> str:
        return self.manifest.get("pack_nature", "texte")

    @property
    def pack_shape(self) -> str:
        return self.manifest.get("pack_shape", "whop_reward")

    def rules_paths(self) -> list[str]:
        return [os.path.normpath(os.path.join(self.contracts_dir, r))
                for r in self.manifest.get("rules", [])]


def load_liber_mode() -> str:
    if not os.path.exists(LIBER_PATH):
        return DEFAULT_MODE
    try:
        with open(LIBER_PATH, "r", encoding="utf-8-sig") as f:
            return (json.load(f) or {}).get("mode") or DEFAULT_MODE
    except Exception:
        return DEFAULT_MODE


def load_profile(mode: str = None) -> Profile:
    if mode is None:
        mode = load_liber_mode()
    manifest_path = os.path.join(PROFILES_DIR, mode, "manifest.json")
    if not os.path.exists(manifest_path):
        raise FileNotFoundError(
            f"profil '{mode}' introuvable (manque {manifest_path}). "
            f"Profils disponibles: whop, logo.")
    with open(manifest_path, "r", encoding="utf-8-sig") as f:
        manifest = json.load(f)
    return Profile(mode, manifest)


def set_liber_mode(mode: str):
    """ фикс locks le mode dans le liber (utilise par IW_CUSTOS --init-siege)."""
    if not os.path.exists(LIBER_PATH):
        raise FileNotFoundError("liber_clipping.json introuvable")
    with open(LIBER_PATH, "r", encoding="utf-8-sig") as f:
        liber = json.load(f)
    if mode not in ("whop", "logo"):
        raise ValueError(f"mode inconnu: {mode} (attendu: whop|logo)")
    liber["mode"] = mode
    with open(LIBER_PATH, "w", encoding="utf-8") as f:
        json.dump(liber, f, indent=2, ensure_ascii=False)