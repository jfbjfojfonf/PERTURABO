"""
libs/omnis_watch_distributor.py — Expédition des packs vers OMNIS_WATCH
=======================================================================

À la Porte 4 validée, distribue les N production_pack.json vers OMNIS_WATCH.
Mécanismes supportés (v1) :
  - packs_index.json généré dans F05_PACKAGER/OUT/ (index des N packs)
  - URLs raw.githubusercontent.com imprimées pour que OMNIS_WATCH puisse fetch
  - Optionnel : git tag (si le repo est pushé et --git-tag fourni)

PERTURABO_BASE (référence OMNIS_WATCH dev1):
  https://raw.githubusercontent.com/kioka8877-ux/PERTURABO/main/MONDES_FORGES/CLIPPING/ARCHIVUM

Usage:
  from libs.omnis_watch_distributor import OmnisWatchDistributor
  d = OmnisWatchDistributor()
  d.distribute(siege_id, n_angles)
"""

import glob
import json
import os
import subprocess
from datetime import datetime, timezone

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_FORGE_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(_SCRIPT_DIR)))

RAW_BASE = "https://raw.githubusercontent.com/kioka8877-ux/PERTURABO/main/MONDES_FORGES/CLIPPING"


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class OmnisWatchDistributor:
    def __init__(self, forge_root: str = _FORGE_ROOT, raw_base: str = RAW_BASE):
        self.forge_root = forge_root
        self.raw_base = raw_base

    def distribute(self, siege_id: str, n_angles: int, git_tag: str = None) -> dict:
        packs_out = os.path.join(self.forge_root, "F05_PACKAGER", "OUT")
        packs = sorted(glob.glob(os.path.join(packs_out, "production_pack_*.json")))
        if not packs:
            raise FileNotFoundError("Aucun production_pack_*.json dans F05_PACKAGER/OUT/")

        index = {
            "siege_id": siege_id,
            "generated_at": now_iso(),
            "packs_count": len(packs),
            "packs": [],
        }
        for pack_path in packs:
            with open(pack_path, "r", encoding="utf-8") as f:
                pack = json.load(f)
            if pack.get("mode") == "logo":
                # Pack logo v2 : les angles sont dans videos[].
                angles = [v.get("angle_id") for v in pack.get("videos", [])
                          if v.get("angle_id")]
                angle_id = ",".join(angles) if angles else os.path.basename(pack_path)
            else:
                angle_id = pack.get("identite", {}).get("angle_id", os.path.basename(pack_path))
            index["packs"].append({
                "angle_id": angle_id,
                "file": os.path.basename(pack_path),
                "raw_url": f"{self.raw_base}/F05_PACKAGER/OUT/{os.path.basename(pack_path)}",
            })

        index_path = os.path.join(packs_out, "packs_index.json")
        with open(index_path, "w", encoding="utf-8") as f:
            json.dump(index, f, indent=2, ensure_ascii=False)

        print(f"[OMNIS_WATCH_DISTRIBUTOR] Index généré : {index_path}")
        for p in index["packs"]:
            print(f"  → {p['raw_url']}")

        if git_tag:
            try:
                subprocess.run(["git", "tag", git_tag], check=False,
                               cwd=self.forge_root, capture_output=True, text=True)
                subprocess.run(["git", "push", "origin", git_tag], check=False,
                               cwd=self.forge_root, capture_output=True, text=True)
                print(f"[OMNIS_WATCH_DISTRIBUTOR] Tag {git_tag} poussé.")
            except Exception as e:
                print(f"[OMNIS_WATCH_DISTRIBUTOR]  Git tag échoué: {e}")

        return index
