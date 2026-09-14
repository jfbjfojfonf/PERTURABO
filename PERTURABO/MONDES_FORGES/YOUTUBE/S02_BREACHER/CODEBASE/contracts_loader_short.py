"""
contracts_loader_short.py — Charge les contrats SHORT pour S02/S03/S04
Récupère : iron_prompt_short.md, skeleton_checklist_short.json,
           anti_bullshit.md, shorts_doctrine.md, shorts_rules.md
"""

import json
import os
from pathlib import Path

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_FRIGATE_DIR = os.path.dirname(_SCRIPT_DIR)
_PROJECT_ROOT = os.path.dirname(_FRIGATE_DIR)
_CONTRACTS_DIR = os.path.join(_PROJECT_ROOT, "CONTRACTS")
_ARCHIVUM_RULES = os.path.join(_PROJECT_ROOT, "ARCHIVUM", "rules")


def load_iron_prompt_short() -> str:
    path = os.path.join(_CONTRACTS_DIR, "iron_prompt_short.md")
    if not os.path.exists(path):
        return "Tu es l'IRON, le fer qui frappe entre les portes. Mode Short."
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def load_skeleton_checklist_short() -> dict:
    path = os.path.join(_CONTRACTS_DIR, "skeleton_checklist_short.json")
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_anti_bullshit() -> str:
    path = os.path.join(_CONTRACTS_DIR, "anti_bullshit.md")
    if not os.path.exists(path):
        return ""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def load_shorts_doctrine() -> str:
    path = os.path.join(_CONTRACTS_DIR, "shorts_doctrine.md")
    if not os.path.exists(path):
        return ""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def load_shorts_rules() -> str:
    path = os.path.join(_ARCHIVUM_RULES, "shorts_rules.md")
    if not os.path.exists(path):
        return ""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def load_all_short() -> dict:
    return {
        "iron_prompt_short": load_iron_prompt_short(),
        "skeleton_checklist_short": load_skeleton_checklist_short(),
        "anti_bullshit": load_anti_bullshit(),
        "shorts_doctrine": load_shorts_doctrine(),
        "shorts_rules": load_shorts_rules(),
        "meta": {
            "contracts_dir": _CONTRACTS_DIR,
            "rules_count": len(list(Path(_ARCHIVUM_RULES).glob("*.md"))) if os.path.exists(_ARCHIVUM_RULES) else 0,
        }
    }


if __name__ == "__main__":
    c = load_all_short()
    print(f"[CONTRACTS SHORT] Iron prompt: {len(c['iron_prompt_short'])} chars")
    print(f"[CONTRACTS SHORT] Checklist: {len(c['skeleton_checklist_short'])} keys")
    print(f"[CONTRACTS SHORT] Anti-bullshit: {len(c['anti_bullshit'])} chars")
    print(f"[CONTRACTS SHORT] Doctrine: {len(c['shorts_doctrine'])} chars")
    print(f"[CONTRACTS SHORT] Rules: {len(c['shorts_rules'])} chars")
