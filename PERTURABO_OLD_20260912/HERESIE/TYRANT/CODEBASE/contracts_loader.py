"""
contracts_loader.py — Charge les contrats et l'ARCHIVUM pour le TYRANT
Récupère : tyrant_prompt.md, anti_bullshit.md, system_prompt.md, rules/, capteurs/
"""

import json
import os
from pathlib import Path

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_TYRANT_DIR = os.path.dirname(_SCRIPT_DIR)
_PROJECT_ROOT = os.path.dirname(_TYRANT_DIR)
_CONTRACTS_DIR = os.path.join(_PROJECT_ROOT, "CONTRACTS")
_ARCHIVUM_RULES = os.path.join(_PROJECT_ROOT, "ARCHIVUM", "rules")
_ARCHIVUM_TRANSCRIPTS = os.path.join(_PROJECT_ROOT, "ARCHIVUM", "transcripts")
_CAPTEURS_OUT = os.path.join(_PROJECT_ROOT, "CAPTEURS", "OUT")


def load_tyrant_prompt() -> str:
    """Charge tyrant_prompt.md — le contrat spécifique du TYRANT."""
    path = os.path.join(_CONTRACTS_DIR, "tyrant_prompt.md")
    if not os.path.exists(path):
        return "Tu es le TYRANT, l'Oracle de la flotte PERTURABO. Tu vois. Tu éclaires. Tu te tais."
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def load_system_prompt() -> str:
    """Charge system_prompt.md — la doctrine complète."""
    path = os.path.join(_CONTRACTS_DIR, "system_prompt.md")
    if not os.path.exists(path):
        return ""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def load_anti_bullshit() -> str:
    """Charge anti_bullshit.md — le filtre des fausses règles d'or."""
    path = os.path.join(_CONTRACTS_DIR, "anti_bullshit.md")
    if not os.path.exists(path):
        return ""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


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


def load_capteur_signals() -> str:
    """
    Charge les signaux des CAPTEURS (si disponibles).
    Les Capteurs écrivent des fichiers JSON dans CAPTEURS/OUT/.
    """
    if not os.path.exists(_CAPTEURS_OUT):
        return "[CAPTEURS] Aucun signal — dossier OUT/ inexistant."

    signals = []
    for f in sorted(Path(_CAPTEURS_OUT).glob("*.json"))[:5]:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            signals.append(f"--- {f.name} ---\n{json.dumps(data, ensure_ascii=False, indent=2)[:1000]}")
        except (json.JSONDecodeError, KeyError):
            continue

    if not signals:
        return "[CAPTEURS] Aucun signal capturé — première chasse ou Capteurs inactifs."

    return "\n\n".join(signals)


def load_all() -> dict:
    """Charge tous les contrats, l'ARCHIVUM et les signaux des Capteurs."""
    return {
        "tyrant_prompt": load_tyrant_prompt(),
        "system_prompt": load_system_prompt(),
        "anti_bullshit": load_anti_bullshit(),
        "archivum_rules": load_archivum_rules(),
        "archivum_transcripts": load_archivum_transcripts(),
        "capteur_signals": load_capteur_signals(),
        "meta": {
            "contracts_dir": _CONTRACTS_DIR,
            "rules_count": len(list(Path(_ARCHIVUM_RULES).glob("*.md"))) if os.path.exists(_ARCHIVUM_RULES) else 0,
            "transcripts_count": len(list(Path(_ARCHIVUM_TRANSCRIPTS).glob("*.json"))) if os.path.exists(_ARCHIVUM_TRANSCRIPTS) else 0,
            "capteurs_signals_count": len(list(Path(_CAPTEURS_OUT).glob("*.json"))) if os.path.exists(_CAPTEURS_OUT) else 0,
        }
    }


if __name__ == "__main__":
    contracts = load_all()
    print(f"[CONTRACTS] Tyrant prompt: {len(contracts['tyrant_prompt'])} caractères")
    print(f"[CONTRACTS] System prompt: {len(contracts['system_prompt'])} caractères")
    print(f"[CONTRACTS] Anti-bullshit: {len(contracts['anti_bullshit'])} caractères")
    print(f"[CONTRACTS] Rules: {contracts['meta']['rules_count']} fichiers")
    print(f"[CONTRACTS] Transcripts: {contracts['meta']['transcripts_count']} fichiers")
    print(f"[CONTRACTS] Capteur signals: {contracts['meta']['capteurs_signals_count']} fichiers")
