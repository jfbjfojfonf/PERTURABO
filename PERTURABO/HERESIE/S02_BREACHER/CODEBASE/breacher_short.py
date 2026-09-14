"""
breacher_short.py — S02_BREACHER SHORT : Le Briseur de Murs (Shorts)
====================================================================

Frégate d'extraction du squelette viral d'un YouTube Short.
Utilise skeleton_checklist_short.json (8 éléments) + Gemini pour l'analyse vidéo.

ARCHITECTURE HYBRIDE :
  Phase 1 (--prepare) : breacher_short.py assemble le prompt (specimen + contrats)
  Phase 2 (IRON)      : Claude + Gemini analyse la vidéo → extrait le squelette Short
  Phase 3 (--finalize): breacher_short.py valide → check-in IW_CUSTOS

OUTPUTS :
  - iron_prompt.txt       : le prompt assemblé (phase 1)
  - skeleton_short.json   : le squelette Short extrait (phase 2, par l'IRON)

Usage:
  python breacher_short.py --prepare
  python breacher_short.py --finalize
  python breacher_short.py --status
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_S02_DIR = os.path.dirname(_SCRIPT_DIR)
_PROJECT_ROOT = os.path.dirname(_S02_DIR)
_S02_IN = os.path.join(_S02_DIR, "IN")
_S02_OUT = os.path.join(_S02_DIR, "OUT")

sys.path.insert(0, _SCRIPT_DIR)
from contracts_loader_short import load_all_short


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_specimen_short(path: str = None) -> dict:
    if path is None:
        path = os.path.join(_S02_IN, "specimen_short.json")
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def assemble_iron_prompt(specimen: dict, contracts: dict) -> str:
    iron_prompt = contracts.get("iron_prompt_short", "")
    anti_bullshit = contracts.get("anti_bullshit", "")
    doctrine = contracts.get("shorts_doctrine", "")
    rules = contracts.get("shorts_rules", "")
    checklist = contracts.get("skeleton_checklist_short", {})

    specimen_title = specimen.get("title", "N/A")
    specimen_channel = specimen.get("channel", {}).get("name", "N/A")
    specimen_outlier = specimen.get("outlier_score", "N/A")
    specimen_duration = specimen.get("duration", "N/A")
    transcript_text = specimen.get("transcript", {}).get("text", "N/A")
    video_url = specimen.get("video_url", "N/A")

    prompt = f"""# MISSION DE L'IRON — S02_BREACHER SHORT

## CONTRAT IRON SHORT
{iron_prompt}

## ANTI-BULLSHIT
{anti_bullshit}

## SHORTS DOCTRINE
{doctrine}

## MÉMOIRE IMPÉRIALE — RÈGLES SHORTS
{rules}

## SQUELETTE CHECKLIST SHORT
{json.dumps(checklist, ensure_ascii=False, indent=2)}

## SPECIMEN À ANALYSER

- Titre : {specimen_title}
- Chaîne : {specimen_channel}
- Durée : {specimen_duration}s
- Outlier Score : {specimen_outlier}
- URL : {video_url}

### Transcript
{transcript_text[:5000] if transcript_text != 'N/A' else 'N/A — utiliser Gemini pour analyser la vidéo'}

## TA MISSION — EXTRAIRE LE SQUELETTE SHORT

Analyse ce specimen et extrais le squelette Short avec les 8 éléments suivants :

1. Visual_Hook_Frame (0-0.5s) — La première frame stoppe-t-elle le scroll ?
2. Verbal_Text_Hook (0-3s) — Une phrase qui crée un vide cognitif ET set up le payoff
3. Context_Rapide (3-10s) — Contexte fourni rapidement après le hook
4. Foreshadow_Payoff — Le payoff est-il foreshadowé dès le début ?
5. Content_Format — Type de format (visual_only, text_on_screen, voiceover, etc.)
6. Escalade_Rythme (10-50s) — Chaque seconde = info nouvelle ?
7. Payoff (3-5s avant fin) — Le fait dingue final
8. Loop_Hook (dernière seconde) — La fin reconnecte au début ?

### IMPORTANT — GEMINI VIDEO ANALYSIS
Si tu as accès à Gemini, donne-lui l'URL de la vidéo pour qu'il la regarde.
Gemini peut voir la first frame, lire le texte overlay, entendre l'audio, percevoir le pacing.
C'est strictement supérieur à l'analyse transcript-only.

### Inférence
Infère aussi : swipe_away_estimation, completion_estimation, loop_potentiel (faible/moyen/élevé)

## FORMAT DE SORTIE

Écris `skeleton_short.json` dans S02_BREACHER/OUT/ avec cette structure :

```json
{{
  "source_video_id": "...",
  "source_title": "...",
  "skeleton_type": "SHORT",
  "skeleton": {{
    "Visual_Hook_Frame": {{...}},
    "Verbal_Text_Hook": {{...}},
    "Context_Rapide": {{...}},
    "Foreshadow_Payoff": {{...}},
    "Content_Format": {{...}},
    "Escalade_Rythme": {{...}},
    "Payoff": {{...}},
    "Loop_Hook": {{...}}
  }},
  "inferred_metrics": {{
    "swipe_away_estimation": "...",
    "completion_estimation": "...",
    "loop_potentiel": "..."
  }},
  "s02_meta": {{
    "extracted_at": "{now_iso()}",
    "model_used": "claude-sandbox + gemini-video",
    "checklist_used": "skeleton_checklist_short.json"
  }}
}}
```
"""
    return prompt


def cmd_prepare(args):
    print(f"\n{'='*60}")
    print(f"S02_BREACHER SHORT — Phase 1 : Préparation du prompt")
    print(f"{'='*60}\n")

    specimen = load_specimen_short()
    if not specimen:
        print(f"[S02] ❌ specimen_short.json introuvable dans IN/")
        return

    contracts = load_all_short()
    print(f"[S02] Contrats chargés :")
    print(f"  Iron prompt short : {len(contracts.get('iron_prompt_short', ''))} chars")
    print(f"  Checklist short    : {len(contracts.get('skeleton_checklist_short', {}))} keys")
    print(f"  Doctrine           : {len(contracts.get('shorts_doctrine', ''))} chars")
    print(f"  Rules              : {len(contracts.get('shorts_rules', ''))} chars")

    prompt = assemble_iron_prompt(specimen, contracts)

    os.makedirs(_S02_OUT, exist_ok=True)
    prompt_path = os.path.join(_S02_OUT, "iron_prompt.txt")
    with open(prompt_path, "w", encoding="utf-8") as f:
        f.write(prompt)

    print(f"\n[S02] Prompt assemblé : {prompt_path}")
    print(f"[S02] Taille : {len(prompt)} caractères")
    print(f"\n[S02] 🛠️ Prompt prêt. En attente de l'IRON (Claude + Gemini).")
    print(f"[S02] L'IRON doit :")
    print(f"  1. Lire iron_prompt.txt")
    print(f"  2. (Optionnel) Gemini regarde la vidéo via URL")
    print(f"  3. Extraire le squelette Short (8 éléments)")
    print(f"  4. Inférer swipe_away / completion / loop potentiel")
    print(f"  5. Écrire skeleton_short.json dans S02_BREACHER/OUT/")
    print(f"\n[S02] Ensuite : python breacher_short.py --finalize")


def validate_skeleton_short(data: dict) -> tuple:
    errors = []
    if "skeleton" not in data:
        errors.append("Section 'skeleton' manquante")
        return (False, errors)

    skeleton = data["skeleton"]
    required = ["Visual_Hook_Frame", "Verbal_Text_Hook", "Payoff", "Loop_Hook"]
    for el in required:
        if el not in skeleton:
            errors.append(f"Élément manquant : {el}")

    return (len(errors) == 0, errors)


def cmd_finalize(args):
    print(f"\n{'='*60}")
    print(f"S02_BREACHER SHORT — Phase 3 : Finalisation")
    print(f"{'='*60}\n")

    skeleton_path = os.path.join(_S02_OUT, "skeleton_short.json")
    if not os.path.exists(skeleton_path):
        print(f"[S02] ❌ skeleton_short.json introuvable dans OUT/")
        return

    with open(skeleton_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    ok, errors = validate_skeleton_short(data)
    if not ok:
        print(f"[S02] ❌ Validation échouée :")
        for e in errors:
            print(f"  - {e}")
        return

    print(f"[S02] ✅ skeleton_short.json validé")
    skel = data.get("skeleton", {})
    for el in ["Visual_Hook_Frame", "Verbal_Text_Hook", "Payoff", "Loop_Hook"]:
        if el in skel:
            print(f"  {el}: ✅")

    inferred = data.get("inferred_metrics", {})
    if inferred:
        print(f"\n[S02] Métriques inférées :")
        for k, v in inferred.items():
            print(f"  {k}: {v}")

    # Check-in IW_CUSTOS
    iw_custos = os.path.join(_PROJECT_ROOT, "IW_CUSTOS.py")
    os.system(f"python3 {iw_custos} --mode check-in --frigate S02 --output {skeleton_path}")

    print(f"\n[S02] ✅ Squelette Short extrait. En attente de validation du Warsmith (Porte 2).")


def cmd_status(args):
    print(f"\nS02_BREACHER SHORT — Statut")
    print(f"{'='*40}")
    prompt_path = os.path.join(_S02_OUT, "iron_prompt.txt")
    skeleton_path = os.path.join(_S02_OUT, "skeleton_short.json")
    print(f"  Prompt prêt       : {'✅' if os.path.exists(prompt_path) else '❌'}")
    print(f"  Squelette extrait : {'✅' if os.path.exists(skeleton_path) else '❌'}")


def main():
    parser = argparse.ArgumentParser(description="S02_BREACHER SHORT — Extraction squelette Short")
    subparsers = parser.add_subparsers(dest="command")

    p_prepare = subparsers.add_parser("prepare", help="Phase 1 : assembler le prompt")
    p_prepare.set_defaults(func=cmd_prepare)

    p_finalize = subparsers.add_parser("finalize", help="Phase 3 : valider et check-in")
    p_finalize.set_defaults(func=cmd_finalize)

    p_status = subparsers.add_parser("status", help="État de S02")
    p_status.set_defaults(func=cmd_status)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
