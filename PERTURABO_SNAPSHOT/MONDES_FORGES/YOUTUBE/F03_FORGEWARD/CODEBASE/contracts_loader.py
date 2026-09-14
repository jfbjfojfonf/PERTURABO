"""
contracts_loader.py — Charge les contrats et l'ARCHIVUM pour F03_FORGEWARD
Récupère : system_prompt.md, anti_bullshit.md, iron_prompt.md, rules/
"""

import json
import os
from pathlib import Path

# Path anchoring
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_F03_DIR = os.path.dirname(_SCRIPT_DIR)
_PROJECT_ROOT = os.path.dirname(_F03_DIR)
_CONTRACTS_DIR = os.path.join(_PROJECT_ROOT, "CONTRACTS")
_ARCHIVUM_RULES = os.path.join(_PROJECT_ROOT, "ARCHIVUM", "rules")
_ARCHIVUM_TRANSCRIPTS = os.path.join(_PROJECT_ROOT, "ARCHIVUM", "transcripts")


def load_system_prompt() -> str:
    """Charge system_prompt.md — la doctrine complète."""
    path = os.path.join(_CONTRACTS_DIR, "system_prompt.md")
    if not os.path.exists(path):
        return "Tu es un expert en reverse engineering YouTube."
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def load_anti_bullshit() -> str:
    """Charge anti_bullshit.md — le filtre des fausses règles d'or."""
    path = os.path.join(_CONTRACTS_DIR, "anti_bullshit.md")
    if not os.path.exists(path):
        return ""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def load_iron_prompt() -> str:
    """Charge iron_prompt.md — le contrat de l'Exécuteur (l'IRON)."""
    path = os.path.join(_CONTRACTS_DIR, "iron_prompt.md")
    if not os.path.exists(path):
        path = os.path.join(_CONTRACTS_DIR, "system_prompt.md")
        if not os.path.exists(path):
            return "Tu es un expert en reverse engineering YouTube."
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def load_archivum_rules() -> str:
    """Charge les règles de la Mémoire Impériale depuis ARCHIVUM/rules/."""
    if not os.path.exists(_ARCHIVUM_RULES):
        return "[ARCHIVUM] Aucune règle trouvée — dossier rules/ vide ou inexistant."

    rules = []
    for f in sorted(Path(_ARCHIVUM_RULES).glob("*.md")):
        content = f.read_text(encoding="utf-8").strip()
        if content:
            rules.append(f"--- {f.name} ---\n{content}")

    if not rules:
        return "[ARCHIVUM] Aucune règle .md trouvée dans rules/."

    return "\n\n".join(rules)


def load_archivum_transcripts(limit: int = 3) -> str:
    """Charge un échantillon de transcriptions depuis ARCHIVUM/transcripts/."""
    if not os.path.exists(_ARCHIVUM_TRANSCRIPTS):
        return ""

    transcripts = []
    files = sorted(Path(_ARCHIVUM_TRANSCRIPTS).glob("*.json"))[:limit]

    for f in files:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            text = data.get("transcript", {}).get("text", "")
            if text:
                title = data.get("title", f.name)
                transcripts.append(f"--- {title} ---\n{text[:2000]}")
        except (json.JSONDecodeError, KeyError):
            continue

    if not transcripts:
        return ""

    return "\n\n".join(transcripts)


def load_all() -> dict:
    """Charge tous les contrats et l'ARCHIVUM en un seul appel."""
    return {
        "system_prompt": load_system_prompt(),
        "anti_bullshit": load_anti_bullshit(),
        "iron_prompt": load_iron_prompt(),
        "archivum_rules": load_archivum_rules(),
        "archivum_transcripts": load_archivum_transcripts(),
        "meta": {
            "contracts_dir": _CONTRACTS_DIR,
            "archivum_rules_dir": _ARCHIVUM_RULES,
            "rules_count": len(list(Path(_ARCHIVUM_RULES).glob("*.md"))) if os.path.exists(_ARCHIVUM_RULES) else 0,
            "transcripts_count": len(list(Path(_ARCHIVUM_TRANSCRIPTS).glob("*.json"))) if os.path.exists(_ARCHIVUM_TRANSCRIPTS) else 0,
        }
    }


if __name__ == "__main__":
    contracts = load_all()
    print(f"[CONTRACTS] System prompt: {len(contracts['system_prompt'])} caractères")
    print(f"[CONTRACTS] Anti-bullshit: {len(contracts['anti_bullshit'])} caractères")
    print(f"[CONTRACTS] Iron prompt: {len(contracts['iron_prompt'])} caractères")
    print(f"[CONTRACTS] Rules: {contracts['meta']['rules_count']} fichiers")
    print(f"[CONTRACTS] Transcripts: {contracts['meta']['transcripts_count']} fichiers")
