"""
libs/demon_archivist.py — Écrit les Démons dans ARCHIVUM/demons/ (TYRANT prospectif)
===================================================================================

Après l'éclaircissement, écrit un fichier par Démon : ARCHIVUM/demons/<demon_id>.json.
Ces fichiers sont lus par F02_TYRANT_CAMP pour proposer des océans bleus
sur les campagnes futures.

Usage:
  from demon_archivist import DemonArchivist
  archivist = DemonArchivist(forge_root)
  written = archivist.archive(eclaircissement)
"""

import json
import os


class DemonArchivist:
    def __init__(self, forge_root: str):
        self.forge_root = forge_root
        self.demons_dir = os.path.join(forge_root, "ARCHIVUM", "demons")

    def _slug(self, text: str, idx: int) -> str:
        import re
        slug = re.sub(r"[^a-z0-9]+", "_", (text or "").lower()).strip("_")
        return f"{slug or 'demon'}_{idx}"

    def archive(self, eclaircissement: dict) -> list[str]:
        os.makedirs(self.demons_dir, exist_ok=True)
        written = []
        for idx, demon in enumerate(eclaircissement.get("demons_identified", []), start=1):
            demon_id = demon.get("demon_id") or self._slug(demon.get("demon_url"), idx)
            demon["demon_id"] = demon_id
            path = os.path.join(self.demons_dir, f"{demon_id}.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(demon, f, indent=2, ensure_ascii=False)
            written.append(path)
        return written
