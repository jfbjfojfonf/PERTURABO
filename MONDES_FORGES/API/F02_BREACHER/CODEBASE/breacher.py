"""
breacher.py — F02 BREACHER — Scoring et 20 angles d'attaque
Usage:
    python breacher.py --prepare    → charge raw_intel.json de F01
    python breacher.py --iron       → Oracle score + génère 20 angles
    python breacher.py --finalize   → valide, check-in IW_CUSTOS, affiche Gate 2
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

BREACHER_DIR = Path(__file__).parent.parent
MONDE_DIR = BREACHER_DIR.parent
CORE_DIR = MONDE_DIR.parent.parent / "CORE"
IN_DIR = BREACHER_DIR / "IN"
OUT_DIR = BREACHER_DIR / "OUT"
IW_CUSTOS_PATH = MONDE_DIR / "IW_CUSTOS.py"
LIBER_PATH = MONDE_DIR / "liber_api.json"
ARCHIVUM_DIR = MONDE_DIR / "ARCHIVUM"
CONTRACTS_DIR = MONDE_DIR / "CONTRACTS"

sys.path.insert(0, str(CORE_DIR))


def load_liber() -> dict:
    return json.loads(LIBER_PATH.read_text(encoding="utf-8")) if LIBER_PATH.exists() else {}


def load_cold_rules() -> str:
    rules_dir = ARCHIVUM_DIR / "rules"
    if not rules_dir.exists():
        return ""
    parts = []
    for f in sorted(rules_dir.glob("*.md")):
        parts.append(f"### {f.stem}\n{f.read_text(encoding='utf-8')}")
    return "\n".join(parts)


def load_scoring_checklist() -> dict:
    p = CONTRACTS_DIR / "api_scoring_checklist.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


# ─── --prepare ───────────────────────────────────────────────────────────────

def prepare():
    IN_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    liber = load_liber()
    siege_id = liber.get("siege_id", "API-001")

    raw_intel_path = ARCHIVUM_DIR / "targets" / siege_id / "raw_intel.json"
    if not raw_intel_path.exists():
        print(f"[F02 BREACHER --prepare] ERREUR : raw_intel.json introuvable pour {siege_id}.")
        print("Lancer F01 SENTINEL d'abord.")
        sys.exit(1)

    raw_intel = json.loads(raw_intel_path.read_text(encoding="utf-8"))
    apis = raw_intel.get("parsed", {}).get("apis_candidates", [])

    context = {
        "siege_id": siege_id,
        "apis_candidates": apis,
        "signal_global": raw_intel.get("parsed", {}).get("signal_global", ""),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    (IN_DIR / "breacher_context.json").write_text(
        json.dumps(context, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"[F02 BREACHER --prepare] {len(apis)} APIs candidates — Siège {siege_id}")


# ─── --iron ───────────────────────────────────────────────────────────────────

def iron():
    context_path = IN_DIR / "breacher_context.json"
    if not context_path.exists():
        print("[F02 BREACHER --iron] ERREUR : Lancer --prepare d'abord.")
        sys.exit(1)

    context = json.loads(context_path.read_text(encoding="utf-8"))
    cold_rules = load_cold_rules()
    checklist = load_scoring_checklist()

    try:
        from ai_gateway import call_oracle
    except ImportError:
        print(f"[F02 BREACHER --iron] ERREUR : ai_gateway.py introuvable dans {CORE_DIR}")
        sys.exit(1)

    prompt = f"""Tu es F02 BREACHER du système PERTURABO.
Mission : scorer les APIs candidates, identifier la cible, générer 20 angles d'attaque.

## RÈGLES DISTILLÉES
{cold_rules[:3000] if cold_rules else "Aucune règle encore — première campagne."}

## GRILLE DE SCORING
{json.dumps(checklist, indent=2, ensure_ascii=False)}

## APIS CANDIDATES (depuis F01 SENTINEL)
{json.dumps(context['apis_candidates'], indent=2, ensure_ascii=False)}

## SIGNAL GLOBAL F01
{context.get('signal_global', 'N/A')}

## FORMULE DE SCORING (chaque dimension normalisée sur 100)
score_total = popularite_rapidapi × 0.35
            + (latence_elevee_ms / 100) × 0.25   [faille : > 2000ms = score élevé]
            + wrappers_github / 10 × 0.20
            + frustration_pricing × 0.20

## TYPES D'ANGLES (répartis sur les 20)
prix(×5), endpoint(×4), format(×3), niche(×4), vitesse(×2), bundle(×2)

Génère UNIQUEMENT ce JSON valide :
{{
  "siege_id": "{context['siege_id']}",
  "scores": [
    {{
      "nom": "string",
      "score_total": 0,
      "score_popularite": 0,
      "score_latence": 0,
      "score_wrappers": 0,
      "score_pricing": 0,
      "verdict": "CIBLE|RESERVE|ELIMINE"
    }}
  ],
  "cible_retenue": {{
    "nom": "string",
    "categorie": "string",
    "score_total": 0,
    "faille_principale": "string"
  }},
  "angles_attaque": [
    {{
      "id": 1,
      "type": "prix|endpoint|format|niche|vitesse|bundle",
      "description": "string",
      "prix_suggere": "string",
      "differenciateur": "string"
    }}
  ],
  "strategie_globale": "string"
}}"""

    print("[F02 BREACHER --iron] Oracle scoring en cours...")
    result = call_oracle("F02", prompt)

    if not result:
        print("[F02 BREACHER --iron] ERREUR : Oracle n'a pas répondu.")
        sys.exit(1)

    clean = result.strip()
    if clean.startswith("```"):
        lines = clean.split("\n")
        end = -1 if lines[-1].strip() == "```" else len(lines)
        clean = "\n".join(lines[1:end])

    try:
        output = json.loads(clean)
    except json.JSONDecodeError as e:
        print(f"[F02 BREACHER --iron] ERREUR JSON : {e}")
        (OUT_DIR / "breacher_raw.txt").write_text(result, encoding="utf-8")
        sys.exit(1)

    (OUT_DIR / "breacher_output.json").write_text(
        json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    cible = output.get("cible_retenue", {})
    print(f"[F02 BREACHER --iron] Cible : {cible.get('nom','N/A')} — score {cible.get('score_total','N/A')}/100")
    print(f"Angles générés : {len(output.get('angles_attaque', []))}")


# ─── --finalize ───────────────────────────────────────────────────────────────

def finalize():
    out_path = OUT_DIR / "breacher_output.json"
    if not out_path.exists():
        print("[F02 BREACHER --finalize] ERREUR : Lancer --iron d'abord.")
        sys.exit(1)

    output = json.loads(out_path.read_text(encoding="utf-8"))

    required = ["cible_retenue", "angles_attaque", "scores"]
    missing = [k for k in required if k not in output]
    if missing:
        print(f"[F02 BREACHER --finalize] ERREUR : champs manquants : {missing}")
        sys.exit(1)

    angles = output.get("angles_attaque", [])
    if len(angles) < 15:
        print(f"[F02 BREACHER --finalize] AVERTISSEMENT : {len(angles)} angles seulement (attendu 20)")

    result = subprocess.run(
        [sys.executable, str(IW_CUSTOS_PATH),
         "--mode", "check-in", "--frigate", "F02", "--output", str(out_path)],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        print(result.stdout.strip())
    else:
        print(f"[F02 BREACHER] AVERTISSEMENT IW_CUSTOS : {result.stderr.strip()}")

    cible = output.get("cible_retenue", {})
    sep = "=" * 62
    print(f"\n{sep}\n              GATE 2 — BREACHER REPORT\n{sep}")
    print(f"\nCIBLE RETENUE  : {cible.get('nom','N/A')}")
    print(f"SCORE TOTAL    : {cible.get('score_total','N/A')}/100")
    print(f"FAILLE         : {cible.get('faille_principale','N/A')}")
    print(f"\nSCORES :")
    for s in output.get("scores", [])[:6]:
        marker = ">>>" if s.get("verdict") == "CIBLE" else "   "
        print(f"  {marker} [{s.get('score_total',0):3.0f}] {s.get('nom','?')} — {s.get('verdict','?')}")
    print(f"\n20 ANGLES D'ATTAQUE (8/20 affichés) :")
    for angle in angles[:8]:
        print(f"  {angle.get('id','?'):02d}. [{angle.get('type','?')}] {angle.get('description','')}")
        print(f"       {angle.get('prix_suggere','?')} | {angle.get('differenciateur','')[:60]}")
    if len(angles) > 8:
        print(f"       ... +{len(angles)-8} autres angles dans breacher_output.json")
    print(f"\nSTRATEGIE : {output.get('strategie_globale','N/A')}")
    print(f"\n{sep}\nGATE 2 — En attente de validation Warsmith")
    print("  python IW_CUSTOS.py --mode gate --gate 2 --decision yes")
    print(f"{sep}\n")


def main():
    parser = argparse.ArgumentParser(description="F02 BREACHER — Scoring et angles d'attaque")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--prepare", action="store_true")
    group.add_argument("--iron", action="store_true")
    group.add_argument("--finalize", action="store_true")
    args = parser.parse_args()

    if args.prepare: prepare()
    elif args.iron: iron()
    elif args.finalize: finalize()


if __name__ == "__main__":
    main()
