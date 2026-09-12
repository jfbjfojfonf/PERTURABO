"""
grand_compass.py — F05_GRAND_COMPASS : Le Compas
===================================================

Frégate de cartographie de territoire (Mode 2 — Lancement de Chaîne).
Niche Bending + Validation Océan Bleu + Stratégie de lancement.

ARCHITECTURE HYBRIDE :
  Phase 1 (--prepare) : grand_compass.py fait la recherche web + assemble le prompt
  Phase 2 (IRON)      : Claude (sandbox) analyse, propose marchés, valide océan bleu
  Phase 3 (--finalize): grand_compass.py valide niche_report.json → check-in

OUTPUTS :
  - niche_report.json : concept + 8 marchés adjacents + top 3 océan bleu + stratégie lancement

Usage:
  python grand_compass.py --prepare
  python grand_compass.py --prepare --specimen path
  python grand_compass.py --finalize
  python grand_compass.py --status
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

# Path anchoring
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_F05_DIR = os.path.dirname(_SCRIPT_DIR)
_PROJECT_ROOT = os.path.dirname(_F05_DIR)
_F05_IN = os.path.join(_F05_DIR, "IN")
_F05_OUT = os.path.join(_F05_DIR, "OUT")

# Import local
sys.path.insert(0, _SCRIPT_DIR)
from contracts_loader import load_all
from web_search import search_web, validate_blue_ocean


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_specimen(specimen_path: str = None) -> dict:
    """Charge specimen.json depuis F05_GRAND_COMPASS/IN/."""
    if specimen_path is None:
        specimen_path = os.path.join(_F05_IN, "specimen.json")
    if not os.path.exists(specimen_path):
        raise FileNotFoundError(
            f"Specimen introuvable: {specimen_path}\n"
            f"Place specimen.json (de F01_SENTINEL/OUT/) dans F05_GRAND_COMPASS/IN/"
        )
    with open(specimen_path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_brief(brief_path: str = None) -> dict:
    """Charge brief.json (intention du Warsmith — optionnel)."""
    if brief_path is None:
        brief_path = os.path.join(_F05_IN, "brief.json")
    if not os.path.exists(brief_path):
        return {}
    with open(brief_path, "r", encoding="utf-8") as f:
        return json.load(f)


def perform_web_research(transcript_text: str) -> dict:
    """
    Effectue des recherches web préliminaires pour évaluer la concurrence.
    Cherche des chaînes YouTube qui font des concepts similaires.
    """
    print("[F05] Recherche web préliminaire (DuckDuckGo)...")

    # Recherche large sur le concept de "niche bending YouTube"
    query1 = "faceless youtube channel niche bending blue ocean strategy"
    results1 = search_web(query1, max_results=5)
    print(f"[F05]   Recherche 1: {len(results1)} résultats")

    # Recherche sur des chaînes anonymes dans des univers fictionnels
    query2 = "anonymous youtube channel fictional universe explained animation"
    results2 = search_web(query2, max_results=5)
    print(f"[F05]   Recherche 2: {len(results2)} résultats")

    return {
        "query_1": query1,
        "results_1": results1,
        "query_2": query2,
        "results_2": results2,
        "total_results": len(results1) + len(results2),
    }


def assemble_iron_prompt(specimen: dict, brief: dict, contracts: dict,
                         web_research: dict) -> str:
    """
    Assemble le prompt complet pour l'IRON (Claude sandbox).
    """
    transcript_text = specimen.get("transcript", {}).get("text", "")
    video_title = specimen.get("title", "Inconnu")
    video_id = specimen.get("video_id", "Inconnu")
    view_count = specimen.get("view_count", "N/A")
    outlier_score = specimen.get("outlier_score", "N/A")
    channel_name = specimen.get("channel", {}).get("name", "N/A")
    subscriber_count = specimen.get("channel", {}).get("subscriber_count", "N/A")

    web_research_json = json.dumps(web_research, ensure_ascii=False, indent=2)

    intent = brief.get("intent", "Analyser le territoire et proposer des marchés adjacents")

    prompt = f"""# MISSION DE L'IRON — F05_GRAND_COMPASS

## CONTRAT
{contracts["iron_prompt"]}

## RÈGLES ANTI-BULLSHIT
{contracts["anti_bullshit"]}

## MÉMOIRE IMPÉRIALE — RÈGLES DES EXPERTS
{contracts["archivum_rules"]}

## MÉMOIRE IMPÉRIALE — TRANSCRIPTIONS DE RÉFÉRENCE
{contracts["archivum_transcripts"] or "[Aucune transcription de référence disponible]"}

---

## SPECIMEN À ANALYSER

**Video ID:** {video_id}
**Titre:** {video_title}
**Chaîne:** {channel_name} ({subscriber_count} abonnés)
**Vues:** {view_count}
**Outlier Score:** {outlier_score}

### TRANSCRIPTION
{transcript_text[:8000]}

---

## INTENTION DU WARSMITH
{intent}

---

## RECHERCHE WEB PRÉLIMINAIRE (DuckDuckGo)
{web_research_json}

---

## INSTRUCTIONS POUR L'IRON

### Étape 1 — Identification du Concept et du Format
Analyse la transcription et identifie :
- **Le CONCEPT** : qu'est-ce que cette vidéo fait ? (ex: "liste ordonnée de personnages d'un univers fictionnel")
- **Le FORMAT** : quel format vidéo ? (ex: "vidéo explicative animée, 7-10 min")

### Étape 2 — Niche Bending
Propose 8 marchés adjacents où ce concept n'existe pas encore ou est sous-exploité.
Pour chaque marché :
- **niche** : le nom du marché
- **rationale** : pourquoi le concept s'y prête
- **audience_potential** : haute / moyenne / faible
- **monetization_potential** : haute / moyenne / faible
- **production_difficulty** : facile / moyen / difficile

### Étape 3 — Validation Océan Bleu (Top 3)
Pour les 3 meilleures propositions :
- **verdict** : OCÉAN BLEU / OCÉAN BLEU LÉGER / OCÉAN ROUGE
- **confidence_score** : 1-10
- **reasoning** : analyse de la concurrence basée sur la recherche web
- **competition_analysis** : qui existe déjà, quel est l'écart
- **monetization_outlook** : potentiel de revenu
- **first_5_video_ideas** : 5 idées de vidéos pour lancer la chaîne
  Chaque idée : {{"title", "concept", "why"}}

### Étape 4 — Recommandation
Choisis la meilleure niche et justifie.

---

## FORMAT DE SORTIE ATTENDU (JSON)

Retourne UNIQUEMENT un JSON valide :

```json
{{
  "source_video_id": "{video_id}",
  "source_title": "{video_title}",

  "concept_identified": "...",
  "format_identified": "...",

  "niche_bending_proposals": [
    {{
      "niche": "...",
      "rationale": "...",
      "audience_potential": "haute",
      "monetization_potential": "haute",
      "production_difficulty": "facile"
    }}
  ],

  "blue_ocean_validations": [
    {{
      "niche": "...",
      "verdict": "OCÉAN BLEU",
      "confidence_score": 9,
      "reasoning": "...",
      "competition_analysis": "...",
      "monetization_outlook": "...",
      "first_5_video_ideas": [
        {{"title": "...", "concept": "...", "why": "..."}}
      ]
    }}
  ],

  "recommended_niche": "...",

  "f05_meta": {{
    "analyzed_at": "{now_iso()}",
    "model_used": "claude-sandbox",
    "web_searches_performed": {web_research.get("total_results", 0)},
    "rules_applied": ["niche bending", "océan bleu", "anti-bullshit"]
  }}
}}
```

Ne retourne RIEN d'autre que le JSON.
"""

    return prompt


def save_iron_prompt(prompt: str) -> str:
    os.makedirs(_F05_OUT, exist_ok=True)
    path = os.path.join(_F05_OUT, "iron_prompt.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(prompt)
    return path


def validate_niche_report(report_path: str = None) -> dict:
    """Valide le niche_report.json produit par l'IRON."""
    if report_path is None:
        report_path = os.path.join(_F05_OUT, "niche_report.json")

    if not os.path.exists(report_path):
        return {"valid": False, "error": f"niche_report.json introuvable: {report_path}"}

    try:
        with open(report_path, "r", encoding="utf-8") as f:
            report = json.load(f)
    except json.JSONDecodeError as e:
        return {"valid": False, "error": f"JSON invalide: {e}"}

    # Vérifier les champs obligatoires
    required = ["concept_identified", "format_identified", "niche_bending_proposals",
                "blue_ocean_validations", "recommended_niche"]
    missing = [k for k in required if k not in report]
    if missing:
        return {"valid": False, "error": f"Champs manquants: {missing}", "report": report}

    # Vérifier qu'il y a au moins 3 propositions
    proposals = report.get("niche_bending_proposals", [])
    if len(proposals) < 3:
        return {"valid": False, "error": f"Pas assez de propositions ({len(proposals)}/8)", "report": report}

    # Vérifier les validations océan bleu
    validations = report.get("blue_ocean_validations", [])
    if len(validations) < 1:
        return {"valid": False, "error": "Aucune validation océan bleu", "report": report}

    return {"valid": True, "error": None, "report": report}


def check_in_iw_custos(output_path: str):
    custos_path = os.path.join(_PROJECT_ROOT, "IW_CUSTOS.py")
    if os.path.exists(custos_path):
        import subprocess
        result = subprocess.run(
            [sys.executable, custos_path, "--mode", "check-in", "--frigate", "F05", "--output", output_path],
            capture_output=True, text=True, timeout=30
        )
        print(f"[F05] IW_CUSTOS: {result.stdout.strip()}")
        if result.stderr:
            print(f"[F05] IW_CUSTOS stderr: {result.stderr.strip()}")
    else:
        print(f"[F05] ⚠️ IW_CUSTOS.py non trouvé — check-in ignoré")


def cmd_prepare(args):
    """Phase 1 : recherche web + assemble le prompt pour l'IRON."""
    print("=" * 60)
    print("🧭 F05_GRAND_COMPASS — Le Compas")
    print("=" * 60)

    # 1. Charger le specimen
    print("\n[F05] Chargement du specimen...")
    specimen = load_specimen(args.specimen)
    print(f"[F05] Video: {specimen.get('title', 'N/A')}")
    print(f"[F05] Channel: {specimen.get('channel', {}).get('name', 'N/A')}")
    print(f"[F05] Outlier Score: {specimen.get('outlier_score', 'N/A')}")

    # 2. Charger le brief
    brief = load_brief(args.brief)
    print(f"[F05] Intention: {brief.get('intent', 'Analyse de territoire')}")

    # 3. Charger les contrats + ARCHIVUM
    print("\n[F05] Chargement des contrats et de l'ARCHIVUM...")
    contracts = load_all()
    print(f"[F05] System prompt: {len(contracts['system_prompt'])} caractères")
    print(f"[F05] Règles ARCHIVUM: {contracts['meta']['rules_count']} fichiers")

    # 4. Recherche web préliminaire
    transcript_text = specimen.get("transcript", {}).get("text", "")
    print("\n[F05] Recherche web préliminaire...")
    web_research = perform_web_research(transcript_text)
    print(f"[F05] {web_research['total_results']} résultats web collectés")

    # 5. Assembler le prompt
    print("\n[F05] Assemblage du prompt pour l'IRON...")
    prompt = assemble_iron_prompt(specimen, brief, contracts, web_research)
    prompt_path = save_iron_prompt(prompt)
    prompt_size = len(prompt.encode("utf-8")) / 1024
    print(f"[F05] Prompt sauvegardé: {prompt_path} ({prompt_size:.1f} KB)")

    # 6. Instructions pour l'IRON
    print(f"\n{'=' * 60}")
    print(f"🛠️  PROMPT PRÊT — EN ATTENTE DE L'IRON (Claude sandbox)")
    print(f"{'=' * 60}")
    print(f"\nLe prompt est dans: {prompt_path}")
    print(f"\nL'IRON (Claude) doit :")
    print(f"  1. Lire {prompt_path}")
    print(f"  2. Identifier le concept + le format")
    print(f"  3. Proposer 8 marchés adjacents (niche bending)")
    print(f"  4. Valider le top 3 en océan bleu (avec recherche web)")
    print(f"  5. Proposer 5 idées de vidéos pour la niche recommandée")
    print(f"  6. Écrire niche_report.json dans F05_GRAND_COMPASS/OUT/")
    print(f"\nEnsuite, lancer :")
    print(f"  python grand_compass.py --finalize")


def cmd_finalize(args):
    """Phase 3 : valide niche_report.json et check-in."""
    print("=" * 60)
    print("🧭 F05_GRAND_COMPASS — FINALISATION")
    print("=" * 60)

    report_path = args.report if args.report else os.path.join(_F05_OUT, "niche_report.json")

    print(f"\n[F05] Validation de {report_path}...")
    result = validate_niche_report(report_path)

    if not result["valid"]:
        print(f"[F05] ❌ VALIDATION ÉCHOUÉE: {result['error']}")
        sys.exit(1)

    report = result["report"]
    print(f"[F05] ✅ Rapport valide !")
    print(f"[F05] Concept: {report['concept_identified']}")
    print(f"[F05] Format: {report['format_identified']}")
    print(f"[F05] Propositions: {len(report['niche_bending_proposals'])} marchés")
    print(f"[F05] Validations: {len(report['blue_ocean_validations'])} océans bleus")
    print(f"[F05] Recommandation: {report['recommended_niche']}")

    # Afficher le top 3
    for v in report["blue_ocean_validations"][:3]:
        print(f"  → {v['niche']}: {v['verdict']} (confiance: {v.get('confidence_score', 'N/A')}/10)")

    # Check-in IW_CUSTOS
    if not args.no_checkin:
        check_in_iw_custos(report_path)

    print(f"\n{'=' * 60}")
    print(f"🧭 F05_GRAND_COMPASS — MISSION ACCOMPLIE")
    print(f"{'=' * 60}")
    print(f"Rapport: {report_path}")
    print(f"Niche recommandée: {report['recommended_niche']}")
    print(f"Prochaine étape: Porte 2 (validation du Warsmith) → F03_FORGEWARD (premier script)")


def cmd_status(args):
    """Vérifie l'état de F05."""
    print("=" * 60)
    print("🧭 F05_GRAND_COMPASS — ÉTAT")
    print("=" * 60)

    specimen_path = os.path.join(_F05_IN, "specimen.json")
    brief_path = os.path.join(_F05_IN, "brief.json")
    prompt_path = os.path.join(_F05_OUT, "iron_prompt.txt")
    report_path = os.path.join(_F05_OUT, "niche_report.json")

    print(f"\n[IN]  specimen.json: {'✅ présent' if os.path.exists(specimen_path) else '❌ absent'}")
    print(f"[IN]  brief.json:    {'✅ présent' if os.path.exists(brief_path) else '❌ absent'}")
    print(f"[OUT] iron_prompt.txt: {'✅ prêt' if os.path.exists(prompt_path) else '❌ absent'}")
    print(f"[OUT] niche_report.json: {'✅ prêt' if os.path.exists(report_path) else '❌ en attente de l'IRON'}")

    if os.path.exists(prompt_path) and not os.path.exists(report_path):
        print(f"\n→ L'IRON doit produire niche_report.json")
        print(f"  Lire: {prompt_path}")
        print(f"  Écrire: {report_path}")
    elif os.path.exists(report_path):
        print(f"\n→ Lancer: python grand_compass.py --finalize")
    elif not os.path.exists(specimen_path):
        print(f"\n→ Placer specimen.json dans F05_GRAND_COMPASS/IN/")
    else:
        print(f"\n→ Lancer: python grand_compass.py --prepare")


def main():
    parser = argparse.ArgumentParser(description="F05_GRAND_COMPASS — Le Compas")
    subparsers = parser.add_subparsers(dest="command", help="Phase d'exécution")

    p_prepare = subparsers.add_parser("prepare", help="Phase 1 : recherche web + assembler le prompt")
    p_prepare.add_argument("--specimen", default=None, help="Chemin vers specimen.json")
    p_prepare.add_argument("--brief", default=None, help="Chemin vers brief.json")
    p_prepare.set_defaults(func=cmd_prepare)

    p_finalize = subparsers.add_parser("finalize", help="Phase 3 : valider niche_report.json → check-in")
    p_finalize.add_argument("--report", default=None, help="Chemin vers niche_report.json")
    p_finalize.add_argument("--no-checkin", action="store_true", help="Ne pas signaler à IW_CUSTOS.py")
    p_finalize.set_defaults(func=cmd_finalize)

    p_status = subparsers.add_parser("status", help="Vérifier l'état de F05")
    p_status.set_defaults(func=cmd_status)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
