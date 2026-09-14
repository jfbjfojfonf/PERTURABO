"""
TYRANT contracts_loader.py — MONDE-FORGE API
Assemble le contexte doctrinal pour le TYRANT.
Lit la couche froide (rules, markets) et la couche chaude (targets existants).
"""

import json
from pathlib import Path

MONDE_ROOT = Path(__file__).parent.parent.parent  # MONDES_FORGES/API/
CONTRACTS_DIR = MONDE_ROOT / "CONTRACTS"
ARCHIVUM_DIR = MONDE_ROOT / "ARCHIVUM"


def load_contracts() -> dict:
    contracts = {}
    for fname in ["system_prompt.md", "tyrant_prompt.md", "anti_bullshit.md"]:
        fpath = CONTRACTS_DIR / fname
        key = fname.replace(".md", "").replace(".", "_")
        contracts[key] = fpath.read_text(encoding="utf-8") if fpath.exists() else f"[{fname} not found]"
    return contracts


def load_cold_layer() -> dict:
    cold = {"rules": [], "markets": []}

    rules_dir = ARCHIVUM_DIR / "rules"
    if rules_dir.exists():
        for f in sorted(rules_dir.glob("*.md")):
            cold["rules"].append({"name": f.stem, "content": f.read_text(encoding="utf-8")})

    markets_dir = ARCHIVUM_DIR / "markets"
    if markets_dir.exists():
        for f in sorted(markets_dir.glob("*.json")):
            try:
                cold["markets"].append({
                    "name": f.stem,
                    "data": json.loads(f.read_text(encoding="utf-8"))
                })
            except json.JSONDecodeError:
                pass

    return cold


def load_hot_layer() -> dict:
    hot = {"recent_targets": [], "ledger_summary": None}

    targets_dir = ARCHIVUM_DIR / "targets"
    if targets_dir.exists():
        target_dirs = sorted(
            [d for d in targets_dir.iterdir() if d.is_dir()],
            key=lambda d: d.stat().st_mtime,
            reverse=True
        )[:3]
        for td in target_dirs:
            raw_intel = td / "raw_intel.json"
            if raw_intel.exists():
                try:
                    hot["recent_targets"].append({
                        "siege_id": td.name,
                        "intel": json.loads(raw_intel.read_text(encoding="utf-8"))
                    })
                except json.JSONDecodeError:
                    pass

    ledgers_dir = ARCHIVUM_DIR / "ledgers"
    if ledgers_dir.exists():
        ledger_files = list(ledgers_dir.glob("*.json"))
        if ledger_files:
            survivors, dead = [], []
            for lf in ledger_files:
                try:
                    entry = json.loads(lf.read_text(encoding="utf-8"))
                    (survivors if entry.get("status") == "alive" else dead).append(entry)
                except json.JSONDecodeError:
                    pass
            hot["ledger_summary"] = {
                "total_launched": len(ledger_files),
                "survivors": len(survivors),
                "dead": len(dead),
                "survivor_patterns": [
                    s.get("winning_pattern") for s in survivors if s.get("winning_pattern")
                ]
            }

    return hot


def load_scoring_checklist() -> dict:
    checklist_path = CONTRACTS_DIR / "api_scoring_checklist.json"
    if checklist_path.exists():
        try:
            return json.loads(checklist_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {}


def assemble_context(warsmith_brief: dict | None = None) -> dict:
    return {
        "contracts": load_contracts(),
        "cold_layer": load_cold_layer(),
        "hot_layer": load_hot_layer(),
        "scoring_checklist": load_scoring_checklist(),
        "warsmith_brief": warsmith_brief or {"mode": "enclenche", "categorie_hint": None}
    }


def format_for_prompt(context: dict) -> str:
    parts = []

    parts.append("# DOCTRINE SYSTEME")
    parts.append(context["contracts"].get("system_prompt", ""))

    if context["cold_layer"]["rules"]:
        parts.append("\n# REGLES DISTILLEES (ARCHIVUM COUCHE FROIDE)")
        for rule in context["cold_layer"]["rules"]:
            parts.append(f"\n## {rule['name']}\n{rule['content']}")

    hot = context["hot_layer"]
    if hot.get("ledger_summary") and hot["ledger_summary"].get("survivor_patterns"):
        parts.append("\n# PATTERNS GAGNANTS (IRON WARRIORS SURVIVANTS)")
        for p in hot["ledger_summary"]["survivor_patterns"]:
            parts.append(f"- {p}")

    if context["cold_layer"]["markets"]:
        parts.append("\n# CARTOGRAPHIE MARCHES RAPIDAPI")
        for market in context["cold_layer"]["markets"]:
            parts.append(f"\n## {market['name']}")
            parts.append(json.dumps(market["data"], indent=2, ensure_ascii=False))

    if context["scoring_checklist"]:
        parts.append("\n# GRILLE DE SCORING CIBLES")
        parts.append(json.dumps(context["scoring_checklist"], indent=2, ensure_ascii=False))

    parts.append("\n# FILTRE ANTI-BULLSHIT")
    parts.append(context["contracts"].get("anti_bullshit", ""))

    brief = context["warsmith_brief"]
    parts.append("\n# BRIEF WARSMITH")
    if brief.get("categorie_hint"):
        parts.append(f"Categorie cible suggeree : {brief['categorie_hint']}")
    else:
        parts.append("Mode : ENCLENCHE — identifier la cible optimale de maniere autonome.")

    return "\n".join(parts)
