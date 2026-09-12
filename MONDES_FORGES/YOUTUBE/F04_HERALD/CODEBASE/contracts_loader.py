"""
contracts_loader.py — Charge les contrats et l'ARCHIVUM pour F04_HERALD
Récupère : iron_prompt.md, anti_bullshit.md, skeleton_checklist.json (thumbnail part), rules/
"""

import json
import os
from pathlib import Path

# Path anchoring
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_F04_DIR = os.path.dirname(_SCRIPT_DIR)
_PROJECT_ROOT = os.path.dirname(_F04_DIR)
_CONTRACTS_DIR = os.path.join(_PROJECT_ROOT, "CONTRACTS")
_ARCHIVUM_RULES = os.path.join(_PROJECT_ROOT, "ARCHIVUM", "rules")


def load_iron_prompt() -> str:
    """Charge iron_prompt.md — le contrat de l'Exécuteur (l'IRON)."""
    path = os.path.join(_CONTRACTS_DIR, "iron_prompt.md")
    if not os.path.exists(path):
        path = os.path.join(_CONTRACTS_DIR, "system_prompt.md")
        if not os.path.exists(path):
            return "Tu es un expert en psychologie de l'image YouTube."
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def load_anti_bullshit() -> str:
    """Charge anti_bullshit.md — le filtre des fausses règles d'or."""
    path = os.path.join(_CONTRACTS_DIR, "anti_bullshit.md")
    if not os.path.exists(path):
        return ""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def load_thumbnail_checklist() -> list:
    """
    Charge la partie thumbnail du skeleton_checklist.json.
    Retourne la liste des éléments du squelette visuel.
    """
    path = os.path.join(_CONTRACTS_DIR, "skeleton_checklist.json")
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("thumbnail_skeleton_elements", [])


def load_archivum_rules() -> str:
    """Charge les règles de la Mémoire Impériale depuis ARCHIVUM/rules/."""
    if not os.path.exists(_ARCHIVUM_RULES):
        return "[ARCHIVUM] Aucune règle trouvée."

    rules = []
    for f in sorted(Path(_ARCHIVUM_RULES).glob("*.md")):
        content = f.read_text(encoding="utf-8").strip()
        if content:
            rules.append(f"--- {f.name} ---\n{content}")

    if not rules:
        return "[ARCHIVUM] Aucune règle .md trouvée dans rules/."

    return "\n\n".join(rules)


def load_all() -> dict:
    """Charge tous les contrats et l'ARCHIVUM en un seul appel."""
    return {
        "iron_prompt": load_iron_prompt(),
        "anti_bullshit": load_anti_bullshit(),
        "thumbnail_checklist": load_thumbnail_checklist(),
        "archivum_rules": load_archivum_rules(),
        "meta": {
            "contracts_dir": _CONTRACTS_DIR,
            "rules_count": len(list(Path(_ARCHIVUM_RULES).glob("*.md"))) if os.path.exists(_ARCHIVUM_RULES) else 0,
        }
    }


if __name__ == "__main__":
    contracts = load_all()
    print(f"[CONTRACTS] Iron prompt: {len(contracts['iron_prompt'])} caractères")
    print(f"[CONTRACTS] Anti-bullshit: {len(contracts['anti_bullshit'])} caractères")
    print(f"[CONTRACTS] Thumbnail checklist: {len(contracts['thumbnail_checklist'])} éléments")
    print(f"[CONTRACTS] Rules: {contracts['meta']['rules_count']} fichiers")
