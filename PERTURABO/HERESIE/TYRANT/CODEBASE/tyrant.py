"""
tyrant.py — TYRANT : L'Oracle (Psyker II)
==========================================

L'Oracle de la flotte PERTURABO. Il ne produit rien. Il voit.
Intervient à la Porte 1, avant l'activation des frégates.
Éclaire le territoire, identifie le démon, propose des marchés adjacents,
estime l'automatisabilité, recommande un chemin.

ARCHITECTURE HYBRIDE :
  Phase 1 (--prepare) : tyrant.py assemble le prompt → iron_prompt.txt
  Phase 2 (IRON)      : Claude (sandbox) analyse, éclaire, écrit eclairissement.json
  Phase 3 (--finalize): tyrant.py valide eclairissement.json → check-in IW_CUSTOS

OUTPUT :
  - eclairissement.json : Rapport d'Éclairement (stratégie pré-siège)

Usage:
  python tyrant.py --prepare --url "https://..." --niche "..." --intent "..."
  python tyrant.py --prepare --brief TYRANT/IN/brief.json
  python tyrant.py --finalize
  python tyrant.py --status
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

# Path anchoring
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_TYRANT_DIR = os.path.dirname(_SCRIPT_DIR)
_PROJECT_ROOT = os.path.dirname(_TYRANT_DIR)
_TYRANT_IN = os.path.join(_TYRANT_DIR, "IN")
_TYRANT_OUT = os.path.join(_TYRANT_DIR, "OUT")

# Import local
sys.path.insert(0, _SCRIPT_DIR)
from contracts_loader import load_all


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_brief(brief_path: str = None) -> dict:
    """Charge brief.json depuis TYRANT/IN/."""
    if brief_path is None:
        brief_path = os.path.join(_TYRANT_IN, "brief.json")
    if not os.path.exists(brief_path):
        return {}
    with open(brief_path, "r", encoding="utf-8") as f:
        return json.load(f)


def assemble_iron_prompt(brief: dict, contracts: dict,
                         url: str, niche: str, intent: str) -> str:
    """
    Assemble le prompt complet pour l'IRON (Claude sandbox).
    Le TYRANT ne reçoit pas de transcription — il voit le territoire, pas le specimen.
    """
    prompt = f"""# MISSION DE L'IRON — TYRANT (L'Oracle)

## CONTRAT DU TYRANT
{contracts["tyrant_prompt"]}

## DOCTRINE GÉNÉRALE
{contracts["system_prompt"]}

## RÈGLES ANTI-BULLSHIT
{contracts["anti_bullshit"]}

## MÉMOIRE IMPÉRIALE — RÈGLES DES EXPERTS
{contracts["archivum_rules"]}

## MÉMOIRE IMPÉRIALE — TRANSCRIPTIONS DE RÉFÉRENCE
{contracts["archivum_transcripts"] or "[Aucune transcription de référence disponible]"}

## SIGNAUX DES CAPTEURS
{contracts["capteur_signals"]}

---

## BRIEF DU WARSMITH

- **URL cible** : {url}
- **Niche** : {niche}
- **Intention** : {intent}

---

## LES 5 QUESTIONS DE VISION

Tu es le TYRANT. Tu vois le territoire avant le siège. Réponds aux 5 questions
dans l'ordre. Ne saute aucune question.

### 1. Le Territoire
Analyse la niche cible :
- **Taille** : grande / moyenne / petite
- **Audience** : démographie, comportement, engagement
- **Monétisation** : AdSense, sponsoring, merch, potentiel de revenu

### 2. Le Démon
Identifie qui domine cette niche :
- **Qui** : nom de la chaîne ou du créateur dominant
- **Avantage structurel** : qu'est-ce qui le rend fort ? (temps, talent, outil, réseau)
- **Arme secrète** : a-t-il un outil ou processus que les autres n'ont pas ?
- **Vulnérabilité** : où est-ce qu'il est attaquable ? (limité à un univers, format copiable, etc.)

### 3. L'Adjacent
Propose 5-10 territoires adjacents où le concept n'existe pas encore :
- Des marchés où la même audience existe mais personne ne sert ce format
- Des univers/mondes/thématiques proches mais non exploités

### 4. L'Automatisabilité
Estime si cette niche peut être produite en série sans main humaine :
- Score 1-10 (1 = impossible à automatiser, 10 = 100% automatisable)
- Justifie le score

### 5. Le Chemin Recommandé
Deux options :
- **attaque_directe** : même territoire que le démon, même format, mais plus vite et en série
- **ocean_bleu** : territoire adjacent que le démon ignore, zéro concurrence

Recommande un chemin et justifie.

---

## FORMAT DE SORTIE ATTENDU (JSON)

Retourne UNIQUEMENT un JSON valide :

```json
{{
  "warsmith_brief": {{
    "video_url": "{url}",
    "niche": "{niche}",
    "intent": "{intent}"
  }},

  "territory_analysis": {{
    "taille": "...",
    "audience": "...",
    "monetization": "..."
  }},

  "demon_identification": {{
    "who": "...",
    "advantage": "...",
    "secret_weapon": "...",
    "vulnerability": "..."
  }},

  "adjacent_territories": [
    "territoire 1",
    "territoire 2",
    "territoire 3",
    "territoire 4",
    "territoire 5"
  ],

  "automatability_score": 0,
  "automatability_justification": "...",

  "recommended_path": "attaque_directe | ocean_bleu",
  "hunt_brief": "Le brief affiné que les frégates vont exécuter",

  "capteur_signals": "Signaux intégrés des Capteurs",

  "tyrant_meta": {{
    "illuminated_at": "{now_iso()}",
    "model_used": "claude-sandbox",
    "rules_applied": ["règle 1", "règle 2"]
  }}
}}
```

Ne retourne RIEN d'autre que le JSON.
"""

    return prompt


def save_iron_prompt(prompt: str) -> str:
    os.makedirs(_TYRANT_OUT, exist_ok=True)
    path = os.path.join(_TYRANT_OUT, "iron_prompt.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(prompt)
    return path


def validate_eclairissement(report_path: str = None) -> dict:
    """Valide l'eclairissement.json produit par l'IRON."""
    if report_path is None:
        report_path = os.path.join(_TYRANT_OUT, "eclairissement.json")

    if not os.path.exists(report_path):
        return {"valid": False, "error": f"eclairissement.json introuvable: {report_path}"}

    try:
        with open(report_path, "r", encoding="utf-8") as f:
            report = json.load(f)
    except json.JSONDecodeError as e:
        return {"valid": False, "error": f"JSON invalide: {e}"}

    # Vérifier les champs obligatoires
    required = ["territory_analysis", "demon_identification", "adjacent_territories",
                "automatability_score", "recommended_path", "hunt_brief"]
    missing = [k for k in required if k not in report]
    if missing:
        return {"valid": False, "error": f"Champs manquants: {missing}", "report": report}

    # Vérifier qu'il y a au moins 3 territoires adjacents
    adjacent = report.get("adjacent_territories", [])
    if len(adjacent) < 3:
        return {"valid": False, "error": f"Pas assez de territoires adjacents ({len(adjacent)}/5)", "report": report}

    # Vérifier le score d'automatisabilité
    score = report.get("automatability_score", 0)
    if not isinstance(score, (int, float)) or score < 1 or score > 10:
        return {"valid": False, "error": f"Score d'automatisabilité invalide: {score} (doit être 1-10)", "report": report}

    # Vérifier le chemin recommandé
    path = report.get("recommended_path", "")
    if path not in ["attaque_directe", "ocean_bleu"]:
        return {"valid": False, "error": f"Chemin recommandé invalide: {path} (doit être 'attaque_directe' ou 'ocean_bleu')", "report": report}

    return {"valid": True, "error": None, "report": report}


def check_in_iw_custos(output_path: str):
    custos_path = os.path.join(_PROJECT_ROOT, "IW_CUSTOS.py")
    if os.path.exists(custos_path):
        import subprocess
        result = subprocess.run(
            [sys.executable, custos_path, "--mode", "check-in", "--frigate", "TYRANT", "--output", output_path],
            capture_output=True, text=True, timeout=30
        )
        print(f"[TYRANT] IW_CUSTOS: {result.stdout.strip()}")
        if result.stderr:
            print(f"[TYRANT] IW_CUSTOS stderr: {result.stderr.strip()}")
    else:
        print(f"[TYRANT] ⚠️ IW_CUSTOS.py non trouvé — check-in ignoré")


def cmd_prepare(args):
    """Phase 1 : assemble le prompt pour l'IRON."""
    print("=" * 60)
    print("👁️  TYRANT — L'Oracle (Psyker II)")
    print("=" * 60)

    # 1. Charger le brief
    brief = load_brief(args.brief)
    url = args.url or brief.get("video_url") or brief.get("url", "")
    niche = args.niche or brief.get("niche", "")
    intent = args.intent or brief.get("intent", "Analyser le territoire et proposer une stratégie")

    if not url:
        print("[TYRANT] ❌ URL requise (via --url ou brief.json)")
        sys.exit(1)

    print(f"[TYRANT] URL cible: {url}")
    print(f"[TYRANT] Niche: {niche or 'Non spécifiée'}")
    print(f"[TYRANT] Intention: {intent}")

    # 2. Charger les contrats + ARCHIVUM + Capteurs
    print("\n[TYRANT] Chargement des contrats, de l'ARCHIVUM et des Capteurs...")
    contracts = load_all()
    print(f"[TYRANT] Tyrant prompt: {len(contracts['tyrant_prompt'])} caractères")
    print(f"[TYRANT] Règles ARCHIVUM: {contracts['meta']['rules_count']} fichiers")
    print(f"[TYRANT] Transcripts ARCHIVUM: {contracts['meta']['transcripts_count']} fichiers")
    print(f"[TYRANT] Signaux Capteurs: {contracts['meta']['capteurs_signals_count']} fichiers")

    # 3. Assembler le prompt
    print("\n[TYRANT] Assemblage du prompt pour l'IRON...")
    prompt = assemble_iron_prompt(brief, contracts, url, niche, intent)
    prompt_path = save_iron_prompt(prompt)
    prompt_size = len(prompt.encode("utf-8")) / 1024
    print(f"[TYRANT] Prompt sauvegardé: {prompt_path} ({prompt_size:.1f} KB)")

    # 4. Instructions pour l'IRON
    print(f"\n{'=' * 60}")
    print(f"🛠️  PROMPT PRÊT — EN ATTENTE DE L'IRON (Claude sandbox)")
    print(f"{'=' * 60}")
    print(f"\nLe prompt est dans: {prompt_path}")
    print(f"\nL'IRON (Claude) doit :")
    print(f"  1. Lire {prompt_path}")
    print(f"  2. Analyser le territoire (taille, audience, monétisation)")
    print(f"  3. Identifier le démon (qui domine, avantage, vulnérabilité)")
    print(f"  4. Proposer 5-10 territoires adjacents (océan bleu)")
    print(f"  5. Estimer l'automatisabilité (1-10)")
    print(f"  6. Recommander un chemin (attaque_directe ou ocean_bleu)")
    print(f"  7. Écrire eclairissement.json dans TYRANT/OUT/")
    print(f"\nEnsuite, lancer :")
    print(f"  python tyrant.py --finalize")


def cmd_finalize(args):
    """Phase 3 : valide eclairissement.json et check-in."""
    print("=" * 60)
    print("👁️  TYRANT — FINALISATION")
    print("=" * 60)

    report_path = args.report if args.report else os.path.join(_TYRANT_OUT, "eclairissement.json")

    print(f"\n[TYRANT] Validation de {report_path}...")
    result = validate_eclairissement(report_path)

    if not result["valid"]:
        print(f"[TYRANT] ❌ VALIDATION ÉCHOUÉE: {result['error']}")
        sys.exit(1)

    report = result["report"]
    print(f"[TYRANT] ✅ Rapport d'Éclairement valide !")
    print(f"[TYRANT] Territoire: {report['territory_analysis'].get('taille', 'N/A')}")
    print(f"[TYRANT] Démon: {report['demon_identification'].get('who', 'N/A')}")
    print(f"[TYRANT] Territoires adjacents: {len(report['adjacent_territories'])}")
    print(f"[TYRANT] Automatisabilité: {report['automatability_score']}/10")
    print(f"[TYRANT] Chemin recommandé: {report['recommended_path']}")
    print(f"[TYRANT] Hunt brief: {report['hunt_brief'][:80]}...")

    # Check-in IW_CUSTOS
    if not args.no_checkin:
        check_in_iw_custos(report_path)

    print(f"\n{'=' * 60}")
    print(f"👁️  TYRANT — MISSION ACCOMPLIE")
    print(f"{'=' * 60}")
    print(f"Rapport: {report_path}")
    print(f"Prochaine étape: Porte 1 (validation du Warsmith) → F01_SENTINEL")


def cmd_status(args):
    """Vérifie l'état du TYRANT."""
    print("=" * 60)
    print("👁️  TYRANT — ÉTAT")
    print("=" * 60)

    brief_path = os.path.join(_TYRANT_IN, "brief.json")
    prompt_path = os.path.join(_TYRANT_OUT, "iron_prompt.txt")
    report_path = os.path.join(_TYRANT_OUT, "eclairissement.json")

    print(f"\n[IN]  brief.json:         {'✅ présent' if os.path.exists(brief_path) else '❌ absent'}")
    print(f"[OUT] iron_prompt.txt:    {'✅ prêt' if os.path.exists(prompt_path) else '❌ absent'}")
    print(f"[OUT] eclairissement.json: {'✅ prêt' if os.path.exists(report_path) else '❌ en attente de l'IRON'}")

    if os.path.exists(prompt_path) and not os.path.exists(report_path):
        print(f"\n→ L'IRON doit produire eclairissement.json")
        print(f"  Lire: {prompt_path}")
        print(f"  Écrire: {report_path}")
    elif os.path.exists(report_path):
        print(f"\n→ Lancer: python tyrant.py --finalize")
    else:
        print(f"\n→ Lancer: python tyrant.py --prepare --url \"...\" --niche \"...\" --intent \"...\"")


def main():
    parser = argparse.ArgumentParser(description="TYRANT — L'Oracle (Psyker II)")
    subparsers = parser.add_subparsers(dest="command", help="Phase d'exécution")

    p_prepare = subparsers.add_parser("prepare", help="Phase 1 : assembler le prompt pour l'IRON")
    p_prepare.add_argument("--brief", default=None, help="Chemin vers brief.json")
    p_prepare.add_argument("--url", default=None, help="URL YouTube cible")
    p_prepare.add_argument("--niche", default=None, help="Niche de destination")
    p_prepare.add_argument("--intent", default=None, help="Intention du Warsmith")
    p_prepare.set_defaults(func=cmd_prepare)

    p_finalize = subparsers.add_parser("finalize", help="Phase 3 : valider eclairissement.json → check-in")
    p_finalize.add_argument("--report", default=None, help="Chemin vers eclairissement.json")
    p_finalize.add_argument("--no-checkin", action="store_true", help="Ne pas signaler à IW_CUSTOS.py")
    p_finalize.set_defaults(func=cmd_finalize)

    p_status = subparsers.add_parser("status", help="Vérifier l'état du TYRANT")
    p_status.set_defaults(func=cmd_status)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
