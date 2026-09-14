"""
TYRANT — MONDE-FORGE API
Frégate de renseignement stratégique.
Identifie le demon RapidAPI, évalue sa vulnerabilite, propose 20 angles d'attaque.

Usage:
    python tyrant.py --prepare    → assemble iron_prompt.txt dans TYRANT/IN/
    python tyrant.py --iron       → appelle l'Oracle, produit tyrant_output.json
    python tyrant.py --finalize   → valide, check-in IW_CUSTOS, affiche Gate 1
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

# Paths
TYRANT_DIR = Path(__file__).parent.parent        # MONDES_FORGES/API/TYRANT/
MONDE_DIR = TYRANT_DIR.parent                    # MONDES_FORGES/API/
CORE_DIR = MONDE_DIR.parent.parent / "CORE"      # CORE/
IN_DIR = TYRANT_DIR / "IN"
OUT_DIR = TYRANT_DIR / "OUT"
IW_CUSTOS_PATH = MONDE_DIR / "IW_CUSTOS.py"
LIBER_PATH = MONDE_DIR / "liber_api.json"

# Ajouter CORE au path pour ai_gateway
sys.path.insert(0, str(CORE_DIR))

# Charger contracts_loader depuis le même dossier
import importlib.util
_spec = importlib.util.spec_from_file_location(
    "contracts_loader", Path(__file__).parent / "contracts_loader.py"
)
contracts_loader = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(contracts_loader)


def load_liber() -> dict:
    if LIBER_PATH.exists():
        return json.loads(LIBER_PATH.read_text(encoding="utf-8"))
    return {}


def prepare():
    """Assemble iron_prompt.txt dans TYRANT/IN/."""
    IN_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    liber = load_liber()
    warsmith_brief = liber.get("warsmith_brief", {"mode": "enclenche", "categorie_hint": None})

    context = contracts_loader.assemble_context(warsmith_brief)
    context_text = contracts_loader.format_for_prompt(context)

    tyrant_prompt_path = MONDE_DIR / "CONTRACTS" / "tyrant_prompt.md"
    tyrant_prompt = tyrant_prompt_path.read_text(encoding="utf-8") if tyrant_prompt_path.exists() else ""

    iron_prompt = f"""{context_text}

---

{tyrant_prompt}

---

Reponds UNIQUEMENT avec un objet JSON valide selon le schema specifie dans tyrant_prompt.md.
Ne genere aucun texte avant ou apres le JSON.
"""

    prompt_path = IN_DIR / "iron_prompt.txt"
    prompt_path.write_text(iron_prompt, encoding="utf-8")
    print(f"[TYRANT --prepare] iron_prompt.txt genere ({len(iron_prompt)} chars)")
    print(f"Chemin : {prompt_path}")


def iron():
    """Appelle l'Oracle et produit tyrant_output.json dans TYRANT/OUT/."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    prompt_path = IN_DIR / "iron_prompt.txt"
    if not prompt_path.exists():
        print("[TYRANT --iron] ERREUR : iron_prompt.txt introuvable. Lancer --prepare d'abord.")
        sys.exit(1)

    prompt = prompt_path.read_text(encoding="utf-8")

    try:
        from ai_gateway import call_oracle
    except ImportError:
        print(f"[TYRANT --iron] ERREUR : ai_gateway.py introuvable dans {CORE_DIR}")
        sys.exit(1)

    print("[TYRANT --iron] Appel Oracle en cours...")
    result = call_oracle("TYRANT", prompt)

    if result is None:
        print("[TYRANT --iron] ERREUR : Oracle n'a pas repondu.")
        sys.exit(1)

    # Nettoyer les backticks markdown eventuels
    clean = result.strip()
    if clean.startswith("```"):
        lines = clean.split("\n")
        end = -1 if lines[-1].strip() == "```" else len(lines)
        clean = "\n".join(lines[1:end])

    try:
        tyrant_output = json.loads(clean)
    except json.JSONDecodeError as e:
        print(f"[TYRANT --iron] ERREUR JSON : {e}")
        print("Reponse brute (500 premiers chars) :")
        print(result[:500])
        # Sauvegarder quand meme pour debug
        (OUT_DIR / "tyrant_raw_response.txt").write_text(result, encoding="utf-8")
        sys.exit(1)

    output_path = OUT_DIR / "tyrant_output.json"
    output_path.write_text(json.dumps(tyrant_output, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[TYRANT --iron] tyrant_output.json produit.")
    print(f"Cible : {tyrant_output.get('cible', {}).get('nom', 'N/A')}")
    print(f"Score : {tyrant_output.get('cible', {}).get('score_total', 'N/A')}/100")


def finalize():
    """Valide tyrant_output.json, check-in IW_CUSTOS, affiche Gate 1."""
    output_path = OUT_DIR / "tyrant_output.json"
    if not output_path.exists():
        print("[TYRANT --finalize] ERREUR : tyrant_output.json introuvable. Lancer --iron d'abord.")
        sys.exit(1)

    tyrant_output = json.loads(output_path.read_text(encoding="utf-8"))

    required = ["cible", "demon", "vulnerabilite", "angles_attaque", "recommandation"]
    missing = [k for k in required if k not in tyrant_output]
    if missing:
        print(f"[TYRANT --finalize] ERREUR : champs manquants : {missing}")
        sys.exit(1)

    # Check-in IW_CUSTOS
    result = subprocess.run(
        [sys.executable, str(IW_CUSTOS_PATH),
         "--mode", "check-in",
         "--frigate", "TYRANT",
         "--output", str(output_path)],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"[TYRANT --finalize] AVERTISSEMENT IW_CUSTOS : {result.stderr.strip()}")
    else:
        print(result.stdout.strip())

    # ─── Affichage Gate 1 ───
    cible = tyrant_output.get("cible", {})
    demon = tyrant_output.get("demon", {})
    vulne = tyrant_output.get("vulnerabilite", {})
    angles = tyrant_output.get("angles_attaque", [])
    reco = tyrant_output.get("recommandation", "")

    sep = "=" * 62
    print(f"\n{sep}")
    print("              GATE 1 — TYRANT REPORT")
    print(sep)
    print(f"\nCIBLE IDENTIFIEE    : {cible.get('nom', 'N/A')}")
    print(f"CATEGORIE           : {cible.get('categorie', 'N/A')}")
    print(f"SCORE TOTAL         : {cible.get('score_total', 'N/A')}/100")
    print(f"\nDEMON DOMINANT      : {demon.get('nom', 'N/A')}")
    print(f"POPULARITE          : {demon.get('popularite_score', 'N/A')}/10")
    print(f"LATENCE             : {demon.get('latence_ms', 'N/A')} ms  [FAILLE]")
    print(f"FRUSTRATION PRICING : {demon.get('pricing_frustration', 'N/A')}/10")
    print(f"\nVULNERABILITE       : {vulne.get('type', 'N/A')}")
    print(f"DETAIL              : {vulne.get('detail', 'N/A')}")
    print(f"\n20 ANGLES D'ATTAQUE (apercu 5/20) :")
    for i, angle in enumerate(angles[:5], 1):
        print(f"  {i:02d}. [{angle.get('type', '?')}] {angle.get('description', '')}")
    if len(angles) > 5:
        print(f"       ... +{len(angles) - 5} angles supplementaires dans tyrant_output.json")
    print(f"\nRECOMMANDATION WARSMITH :")
    print(f"  {reco}")
    print(f"\n{sep}")
    print("GATE 1 — En attente de validation Warsmith")
    print("  python IW_CUSTOS.py --mode gate --gate 1 --decision yes")
    print(f"{sep}\n")


def main():
    parser = argparse.ArgumentParser(description="TYRANT — Frégate de renseignement stratégique API")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--prepare", action="store_true", help="Assembler iron_prompt.txt")
    group.add_argument("--iron", action="store_true", help="Appeler l'Oracle")
    group.add_argument("--finalize", action="store_true", help="Valider et check-in IW_CUSTOS")
    args = parser.parse_args()

    if args.prepare:
        prepare()
    elif args.iron:
        iron()
    elif args.finalize:
        finalize()


if __name__ == "__main__":
    main()
