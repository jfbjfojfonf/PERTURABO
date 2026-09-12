"""
herald_short.py — S04_HERALD SHORT : Le Porte-Étendard (Shorts)
================================================================

Frégate de design de la première frame d'un Short.
Les Shorts n'ont pas de thumbnail personnalisée — YouTube prend une frame du vidéo.
S04 designe ce que le spectateur voit avant de swiper.

ARCHITECTURE HYBRIDE :
  Phase 1 (--prepare) : herald_short.py assemble le prompt (specimen + contrats)
  Phase 2 (IRON)      : Claude analyse + génère le concept de first frame
  Phase 3 (--finalize): herald_short.py valide → check-in IW_CUSTOS

OUTPUTS :
  - iron_prompt.txt           : le prompt assemblé (phase 1)
  - first_frame_concept.json  : le concept de first frame (phase 2, par l'IRON)
  - first_frame.png           : l'image générée par l'IRON (image_generator)

Usage:
  python herald_short.py --prepare
  python herald_short.py --finalize
  python herald_short.py --status
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_S04_DIR = os.path.dirname(_SCRIPT_DIR)
_PROJECT_ROOT = os.path.dirname(_S04_DIR)
_S04_IN = os.path.join(_S04_DIR, "IN")
_S04_OUT = os.path.join(_S04_DIR, "OUT")

sys.path.insert(0, _SCRIPT_DIR)
from contracts_loader_short import load_all_short


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_specimen_short(path: str = None) -> dict:
    if path is None:
        path = os.path.join(_S04_IN, "specimen_short.json")
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_brief(path: str = None) -> dict:
    if path is None:
        path = os.path.join(_S04_IN, "brief.json")
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def assemble_iron_prompt(specimen: dict, brief: dict, contracts: dict) -> str:
    iron_prompt = contracts.get("iron_prompt_short", "")
    anti_bullshit = contracts.get("anti_bullshit", "")
    doctrine = contracts.get("shorts_doctrine", "")

    specimen_title = specimen.get("title", "N/A")
    specimen_channel = specimen.get("channel", {}).get("name", "N/A")
    first_frame = specimen.get("first_frame", "N/A")
    video_url = specimen.get("video_url", "N/A")

    new_title = brief.get("title", "N/A")
    new_niche = brief.get("niche", "N/A")

    prompt = f"""# MISSION DE L'IRON — S04_HERALD SHORT

## CONTRAT IRON SHORT
{iron_prompt}

## ANTI-BULLSHIT
{anti_bullshit}

## SHORTS DOCTRINE
{doctrine}

## SPECIMEN DE RÉFÉRENCE
- Titre : {specimen_title}
- Chaîne : {specimen_channel}
- URL : {video_url}
- First frame du specimen : {first_frame}

## CONTEXTE DE FORGE
- Nouveau titre : {new_title}
- Niche : {new_niche}

## TA MISSION — DESIGNER LA FIRST FRAME

Les Shorts n'ont pas de thumbnail personnalisée. C'est la PREMIÈRE FRAME du vidéo
qui détermine si le spectateur swipe ou regarde.

### RÈGLES (MoneyBoyMaxx)
- "Someone should see your video even if they can't hear anything"
- La first frame doit stopper le scroll SANS SON
- Contraste élevé, mouvement, émotion forte
- Lisible à la taille d'un ongle sur mobile
- Le visual hook doit set up le payoff

### ANALYSE
1. Analyse la first frame du specimen (si disponible)
2. Identifie : composition, contraste, couleurs, émotion, mouvement
3. Adapte à la nouvelle niche

### GÉNÉRATION
Génère un prompt pour image_generator qui produira la first frame.
Format : vertical 9:16 (Shorts), pas 16:9 (Long).

## FORMAT DE SORTIE

Écris `first_frame_concept.json` dans S04_HERALD/OUT/ :

```json
{{
  "source_specimen": "{specimen_title}",
  "new_title": "{new_title}",
  "new_niche": "{new_niche}",
  "visual_analysis": {{
    "composition": "...",
    "contrast": "...",
    "colors": "...",
    "emotion": "...",
    "movement": "...",
    "mobile_readability": "..."
  }},
  "first_frame_prompt": "... (prompt pour image_generator, format 9:16 vertical)",
  "first_frame_text": "... (texte overlay si applicable)",
  "canva_instructions": "... (police, couleur, position si texte overlay)",
  "s04_meta": {{
    "analyzed_at": "{now_iso()}",
    "model_used": "claude-sandbox",
    "format": "9:16 vertical"
  }}
}}
```

Ensuite, génère l'image via image_generator et sauvegarde-la dans S04_HERALD/OUT/first_frame.png
"""
    return prompt


def cmd_prepare(args):
    print(f"\n{'='*60}")
    print(f"S04_HERALD SHORT — Phase 1 : Préparation du prompt")
    print(f"{'='*60}\n")

    specimen = load_specimen_short()
    brief = load_brief()

    contracts = load_all_short()
    print(f"[S04] Contrats chargés :")
    print(f"  Iron prompt short : {len(contracts.get('iron_prompt_short', ''))} chars")
    print(f"  Doctrine           : {len(contracts.get('shorts_doctrine', ''))} chars")

    prompt = assemble_iron_prompt(specimen, brief, contracts)

    os.makedirs(_S04_OUT, exist_ok=True)
    prompt_path = os.path.join(_S04_OUT, "iron_prompt.txt")
    with open(prompt_path, "w", encoding="utf-8") as f:
        f.write(prompt)

    print(f"\n[S04] Prompt assemblé : {prompt_path}")
    print(f"[S04] Taille : {len(prompt)} caractères")
    print(f"\n[S04] 🛠️ Prompt prêt. En attente de l'IRON.")
    print(f"[S04] L'IRON doit :")
    print(f"  1. Lire iron_prompt.txt")
    print(f"  2. Analyser la first frame du specimen")
    print(f"  3. Écrire first_frame_concept.json")
    print(f"  4. Générer first_frame.png via image_generator (format 9:16)")
    print(f"\n[S04] Ensuite : python herald_short.py --finalize")


def validate_first_frame_concept(data: dict) -> tuple:
    errors = []
    required = ["visual_analysis", "first_frame_prompt", "s04_meta"]
    for section in required:
        if section not in data:
            errors.append(f"Section manquante : {section}")
    return (len(errors) == 0, errors)


def cmd_finalize(args):
    print(f"\n{'='*60}")
    print(f"S04_HERALD SHORT — Phase 3 : Finalisation")
    print(f"{'='*60}\n")

    concept_path = os.path.join(_S04_OUT, "first_frame_concept.json")
    if not os.path.exists(concept_path):
        print(f"[S04] ❌ first_frame_concept.json introuvable dans OUT/")
        return

    with open(concept_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    ok, errors = validate_first_frame_concept(data)
    if not ok:
        print(f"[S04] ❌ Validation échouée :")
        for e in errors:
            print(f"  - {e}")
        return

    print(f"[S04] ✅ first_frame_concept.json validé")

    frame_path = os.path.join(_S04_OUT, "first_frame.png")
    print(f"[S04] First frame image : {'✅' if os.path.exists(frame_path) else '❌'}")

    # Check-in IW_CUSTOS
    iw_custos = os.path.join(_PROJECT_ROOT, "IW_CUSTOS.py")
    os.system(f"python3 {iw_custos} --mode check-in --frigate S04 --output {concept_path}")

    print(f"\n[S04] ✅ First frame forgée. En attente de validation du Warsmith (Porte 4).")


def cmd_status(args):
    print(f"\nS04_HERALD SHORT — Statut")
    print(f"{'='*40}")
    prompt_path = os.path.join(_S04_OUT, "iron_prompt.txt")
    concept_path = os.path.join(_S04_OUT, "first_frame_concept.json")
    frame_path = os.path.join(_S04_OUT, "first_frame.png")
    print(f"  Prompt prêt        : {'✅' if os.path.exists(prompt_path) else '❌'}")
    print(f"  Concept forgé      : {'✅' if os.path.exists(concept_path) else '❌'}")
    print(f"  First frame image  : {'✅' if os.path.exists(frame_path) else '❌'}")


def main():
    parser = argparse.ArgumentParser(description="S04_HERALD SHORT — Design first frame")
    subparsers = parser.add_subparsers(dest="command")

    p_prepare = subparsers.add_parser("prepare", help="Phase 1 : assembler le prompt")
    p_prepare.set_defaults(func=cmd_prepare)

    p_finalize = subparsers.add_parser("finalize", help="Phase 3 : valider et check-in")
    p_finalize.set_defaults(func=cmd_finalize)

    p_status = subparsers.add_parser("status", help="État de S04")
    p_status.set_defaults(func=cmd_status)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
