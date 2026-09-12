"""
forgeward_short.py — S03_FORGEWARD SHORT : La Forge de Fer (Shorts)
====================================================================

Frégate de forge de script/storyboard Short.
Produit un script de 15-60s avec loop hook, adapté au format de contenu identifié.

ARCHITECTURE HYBRIDE :
  Phase 1 (--prepare) : forgeward_short.py assemble le prompt (squelette + niche + contrats)
  Phase 2 (IRON)      : Claude génère le script/storyboard Short
  Phase 3 (--finalize): forgeward_short.py valide → check-in IW_CUSTOS

OUTPUTS :
  - iron_prompt.txt      : le prompt assemblé (phase 1)
  - script_short.json    : le script Short + timing + metadata (phase 2, par l'IRON)
  - script_raw.txt       : le script brut format META_01 Short
  - timing_short.json    : segments start/end pour calage visuel
  - metadata.txt         : titre + description + tags

Usage:
  python forgeward_short.py --prepare --niche "Hurricanes US" --format voiceover --duree 30
  python forgeward_short.py --finalize
  python forgeward_short.py --status
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_S03_DIR = os.path.dirname(_SCRIPT_DIR)
_PROJECT_ROOT = os.path.dirname(_S03_DIR)
_S03_IN = os.path.join(_S03_DIR, "IN")
_S03_OUT = os.path.join(_S03_DIR, "OUT")

sys.path.insert(0, _SCRIPT_DIR)
from contracts_loader_short import load_all_short


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_skeleton_short(path: str = None) -> dict:
    if path is None:
        path = os.path.join(_S03_IN, "skeleton_short.json")
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_brief(path: str = None) -> dict:
    if path is None:
        path = os.path.join(_S03_IN, "brief.json")
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def assemble_iron_prompt(skeleton: dict, brief: dict, contracts: dict,
                         niche: str, fmt: str, duree: int) -> str:
    iron_prompt = contracts.get("iron_prompt_short", "")
    anti_bullshit = contracts.get("anti_bullshit", "")
    doctrine = contracts.get("shorts_doctrine", "")
    rules = contracts.get("shorts_rules", "")

    skeleton_json = json.dumps(skeleton.get("skeleton", {}), ensure_ascii=False, indent=2)
    inferred = json.dumps(skeleton.get("inferred_metrics", {}), ensure_ascii=False, indent=2)

    prompt = f"""# MISSION DE L'IRON — S03_FORGEWARD SHORT

## CONTRAT IRON SHORT
{iron_prompt}

## ANTI-BULLSHIT
{anti_bullshit}

## SHORTS DOCTRINE
{doctrine}

## MÉMOIRE IMPÉRIALE — RÈGLES SHORTS
{rules}

## SQUELETTE SHORT À RESPECTER
{skeleton_json}

## MÉTRIQUES INFÉRÉES DU SPECIMEN
{inferred}

## CONTEXTE DE FORGE
- Niche : {niche}
- Format de contenu : {fmt}
- Durée cible : {duree}s

## TA MISSION — FORGER LE SCRIPT SHORT

Produis un script Short de {duree}s en respectant STRICTEMENT le squelette extrait.

### RÈGLES (MoneyBoyMaxx)
- Structure : Hook → Explain Payoff → Foreshadow Payoff → Reveal Payoff
- Le script entier est structuré autour du PAYOFF
- Le hook set up le payoff (un mid hook qui set up le payoff > un great hook qui ne le fait pas)
- Loop hook obligatoire à la fin (combiner 2+ techniques)
- Pas de CTA "abonne-toi"
- Pas de "bonjour"
- Pas de transitions verbales
- Chaque seconde = info nouvelle

### FORMAT DE CONTENU : {fmt}
Adapte le script au format :
- voiceover : script voix off + indications visuelles
- text_on_screen : texte overlay + indications visuelles
- visual_only : storyboard visuel (pas de texte ni voix)
- green_screen : script + indications fond vert
- duet_reply : script de réaction
- image_carousel : description des images + texte overlay + musique

### TIMING
- ~1-2s par ligne (plus rapide que le Long)
- Chaque section doit avoir un start et end estimés
- Total = {duree}s

## FORMAT DE SORTIE

Écris `script_short.json` dans S03_FORGEWARD/OUT/ :

```json
{{
  "source_skeleton": "SHORT",
  "niche": "{niche}",
  "format": "{fmt}",
  "duree_cible": {duree},
  "title": "...",
  "description": "...",
  "tags": ["..."],
  "script_structured": [
    {{
      "section": "Hook",
      "lines": [
        {{"text": "...", "mots_forts": ["..."], "timing": {{"start": 0.0, "end": 3.0}}}}
      ]
    }},
    {{
      "section": "Context",
      "lines": [...]
    }},
    {{
      "section": "Escalade",
      "lines": [...]
    }},
    {{
      "section": "Payoff",
      "lines": [...]
    }},
    {{
      "section": "Loop_Hook",
      "lines": [...]
    }}
  ],
  "timing": {{
    "segments": [...],
    "total_duration": {duree},
    "format": "SHORT"
  }},
  "metadata": {{
    "title": "...",
    "hashtags": ["..."],
    "description": "..."
  }},
  "thumbnail_text": "...",
  "s03_meta": {{
    "forged_at": "{now_iso()}",
    "model_used": "claude-sandbox",
    "skeleton_respected": true,
    "loop_hook_included": true
  }}
}}
```

Écris aussi :
- `script_raw.txt` : le script brut (format META_01 Short)
- `timing_short.json` : les segments start/end pour calage visuel
- `metadata.txt` : titre + description + tags
"""
    return prompt


def cmd_prepare(args):
    print(f"\n{'='*60}")
    print(f"S03_FORGEWARD SHORT — Phase 1 : Préparation du prompt")
    print(f"{'='*60}\n")

    skeleton = load_skeleton_short()
    if not skeleton:
        print(f"[S03] ❌ skeleton_short.json introuvable dans IN/")
        return

    contracts = load_all_short()
    print(f"[S03] Contrats chargés :")
    print(f"  Iron prompt short : {len(contracts.get('iron_prompt_short', ''))} chars")
    print(f"  Doctrine           : {len(contracts.get('shorts_doctrine', ''))} chars")
    print(f"  Rules              : {len(contracts.get('shorts_rules', ''))} chars")

    prompt = assemble_iron_prompt(
        skeleton=skeleton,
        brief=load_brief(),
        contracts=contracts,
        niche=args.niche,
        fmt=args.format,
        duree=args.duree
    )

    os.makedirs(_S03_OUT, exist_ok=True)
    prompt_path = os.path.join(_S03_OUT, "iron_prompt.txt")
    with open(prompt_path, "w", encoding="utf-8") as f:
        f.write(prompt)

    print(f"\n[S03] Prompt assemblé : {prompt_path}")
    print(f"[S03] Taille : {len(prompt)} caractères")
    print(f"[S03] Niche : {args.niche}")
    print(f"[S03] Format : {args.format}")
    print(f"[S03] Durée cible : {args.duree}s")
    print(f"\n[S03] 🛠️ Prompt prêt. En attente de l'IRON.")
    print(f"[S03] L'IRON doit :")
    print(f"  1. Lire iron_prompt.txt")
    print(f"  2. Générer le script Short ({args.duree}s, format {args.format})")
    print(f"  3. Inclure le loop hook obligatoire")
    print(f"  4. Écrire script_short.json + script_raw.txt + timing_short.json + metadata.txt")
    print(f"\n[S03] Ensuite : python forgeward_short.py --finalize")


def validate_script_short(data: dict) -> tuple:
    errors = []
    required = ["script_structured", "timing", "metadata", "s03_meta"]
    for section in required:
        if section not in data:
            errors.append(f"Section manquante : {section}")

    sections = [s.get("section", "") for s in data.get("script_structured", [])]
    if "Loop_Hook" not in sections:
        errors.append("Loop_Hook manquant dans script_structured (OBLIGATOIRE en Short)")

    return (len(errors) == 0, errors)


def cmd_finalize(args):
    print(f"\n{'='*60}")
    print(f"S03_FORGEWARD SHORT — Phase 3 : Finalisation")
    print(f"{'='*60}\n")

    script_path = os.path.join(_S03_OUT, "script_short.json")
    if not os.path.exists(script_path):
        print(f"[S03] ❌ script_short.json introuvable dans OUT/")
        return

    with open(script_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    ok, errors = validate_script_short(data)
    if not ok:
        print(f"[S03] ❌ Validation échouée :")
        for e in errors:
            print(f"  - {e}")
        return

    print(f"[S03] ✅ script_short.json validé")
    sections = [s.get("section", "") for s in data.get("script_structured", [])]
    print(f"[S03] Sections : {sections}")
    print(f"[S03] Loop Hook : {'✅' if 'Loop_Hook' in sections else '❌'}")
    print(f"[S03] Durée cible : {data.get('duree_cible', 'N/A')}s")
    print(f"[S03] Titre : {data.get('metadata', {}).get('title', 'N/A')}")

    # Check-in IW_CUSTOS
    iw_custos = os.path.join(_PROJECT_ROOT, "IW_CUSTOS.py")
    os.system(f"python3 {iw_custos} --mode check-in --frigate S03 --output {script_path}")

    print(f"\n[S03] ✅ Script Short forgé. En attente de validation du Warsmith (Porte 3).")


def cmd_status(args):
    print(f"\nS03_FORGEWARD SHORT — Statut")
    print(f"{'='*40}")
    prompt_path = os.path.join(_S03_OUT, "iron_prompt.txt")
    script_path = os.path.join(_S03_OUT, "script_short.json")
    print(f"  Prompt prêt    : {'✅' if os.path.exists(prompt_path) else '❌'}")
    print(f"  Script forgé   : {'✅' if os.path.exists(script_path) else '❌'}")


def main():
    parser = argparse.ArgumentParser(description="S03_FORGEWARD SHORT — Forge de script Short")
    subparsers = parser.add_subparsers(dest="command")

    p_prepare = subparsers.add_parser("prepare", help="Phase 1 : assembler le prompt")
    p_prepare.add_argument("--niche", required=True, help="Niche de destination")
    p_prepare.add_argument("--format", default="voiceover",
                           choices=["visual_only", "text_on_screen", "voiceover",
                                    "green_screen", "duet_reply", "image_carousel"],
                           help="Format de contenu Short")
    p_prepare.add_argument("--duree", type=int, default=30, help="Durée cible en secondes")
    p_prepare.set_defaults(func=cmd_prepare)

    p_finalize = subparsers.add_parser("finalize", help="Phase 3 : valider et check-in")
    p_finalize.set_defaults(func=cmd_finalize)

    p_status = subparsers.add_parser("status", help="État de S03")
    p_status.set_defaults(func=cmd_status)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
