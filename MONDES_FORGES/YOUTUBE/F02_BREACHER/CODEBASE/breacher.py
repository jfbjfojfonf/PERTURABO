"""
breacher.py — F02_BREACHER : Le Briseur de Murs
================================================

Frégate d'extraction du squelette viral.
Analyse la transcription d'une vidéo cible et extrait sa structure cachée
(Hook, Promise, Rehooks, Body, Payoff, CTA) selon la skeleton_checklist.

ARCHITECTURE HYBRIDE :
  Phase 1 (--prepare) : breacher.py assemble le prompt → iron_prompt.txt
  Phase 2 (IRON)      : Claude (sandbox) lit le prompt, analyse, écrit skeleton.json
  Phase 3 (--finalize): breacher.py valide skeleton.json → check-in IW_CUSTOS

Usage:
  python breacher.py --prepare                    # Assemble le prompt
  python breacher.py --prepare --specimen path    # Spécifier le specimen
  python breacher.py --finalize                   # Valider l'output
  python breacher.py --status                     # Vérifier l'état
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

# Path anchoring
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_F02_DIR = os.path.dirname(_SCRIPT_DIR)
_PROJECT_ROOT = os.path.dirname(_F02_DIR)
_F02_IN = os.path.join(_F02_DIR, "IN")
_F02_OUT = os.path.join(_F02_DIR, "OUT")

# Import contracts_loader (local)
sys.path.insert(0, _SCRIPT_DIR)
from contracts_loader import load_all


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_specimen(specimen_path: str = None) -> dict:
    """Charge specimen.json depuis F02_BREACHER/IN/ ou un chemin spécifié."""
    if specimen_path is None:
        specimen_path = os.path.join(_F02_IN, "specimen.json")
    if not os.path.exists(specimen_path):
        raise FileNotFoundError(
            f"Specimen introuvable: {specimen_path}\n"
            f"Place specimen.json (de F01_SENTINEL/OUT/) dans F02_BREACHER/IN/"
        )
    with open(specimen_path, "r", encoding="utf-8") as f:
        return json.load(f)


def assemble_iron_prompt(specimen: dict, contracts: dict) -> str:
    """
    Assemble le prompt complet pour l'IRON (Claude sandbox).
    Le prompt contient : la transcription, la checklist, l'anti-bullshit,
    les règles de l'ARCHIVUM, et les instructions d'extraction.
    """
    transcript_text = specimen.get("transcript", {}).get("text", "")
    transcript_segments = specimen.get("transcript", {}).get("segments", [])
    video_title = specimen.get("title", "Inconnu")
    video_id = specimen.get("video_id", "Inconnu")
    view_count = specimen.get("view_count", "N/A")
    outlier_score = specimen.get("outlier_score", "N/A")

    # Formater les segments avec timestamps pour l'analyse temporelle
    segments_formatted = ""
    if transcript_segments:
        segments_lines = []
        for seg in transcript_segments[:200]:  # Limiter pour le contexte
            start = seg.get("start", 0)
            text = seg.get("text", "").strip()
            if text:
                # Convertir en format mm:ss
                mins = int(start // 60)
                secs = int(start % 60)
                segments_lines.append(f"[{mins:02d}:{secs:02d}] {text}")
        segments_formatted = "\n".join(segments_lines)

    checklist_json = json.dumps(contracts["skeleton_checklist"], ensure_ascii=False, indent=2)

    prompt = f"""# MISSION DE L'IRON — F02_BREACHER

## CONTRAT
{contracts["iron_prompt"]}

## RÈGLES ANTI-BULLSHIT
{contracts["anti_bullshit"]}

## MÉMOIRE IMPÉRIALE — RÈGLES DES EXPERTS
{contracts["archivum_rules"]}

## MÉMOIRE IMPÉRIALE — TRANSCRIPTIONS DE RÉFÉRENCE
{contracts["archivum_transcripts"] or "[Aucune transcription de référence disponible]"}

## CHECKLIST D'EXTRACTION (skeleton_checklist.json)
{checklist_json}

---

## SPECIMEN À ANALYSER

**Video ID:** {video_id}
**Titre:** {video_title}
**Vues:** {view_count}
**Outlier Score:** {outlier_score}

### TRANSCRIPTION AVEC TIMESTAMPS
{segments_formatted if segments_formatted else transcript_text[:8000]}

### TRANSCRIPTION TEXTE BRUT
{transcript_text[:8000]}

---

## INSTRUCTIONS D'EXTRACTION

Tu es l'IRON. Analyse cette transcription et extrais le squelette viral.

1. Pour CHAQUE élément de la checklist (Hook, Promise, Rehook_1, Rehook_2,
   Body_Structure, Payoff, CTA), remplis TOUS les extraction_fields.

2. Utilise les timestamps pour identifier précisément où chaque élément
   se situe dans la vidéo.

3. Applique l'anti-bullshit : ne valide un pattern que s'il est structurel,
   pas s'il est subjectif ou isolé.

4. Croise avec les règles de la Mémoire Impériale : cite la règle appliquée
   quand c'est pertinent.

5. Retourne UNIQUEMENT un JSON valide avec cette structure exacte :

```json
{{
  "source_video_id": "{video_id}",
  "source_title": "{video_title}",
  "skeleton": {{
    "Hook": {{
      "type_hook": "...",
      "phrase_exacte": "...",
      "emotion_cible": "..."
    }},
    "Promise": {{
      "promesse_explicite": "...",
      "promesse_implicite": "..."
    }},
    "Rehook_1": {{
      "type_rehook": "...",
      "phrase_exacte": "..."
    }},
    "Rehook_2": {{
      "type_rehook": "...",
      "phrase_exacte": "..."
    }},
    "Body_Structure": {{
      "type_structure": "...",
      "nombre_sections": 0,
      "rythme": "..."
    }},
    "Payoff": {{
      "reponse_promesse": "...",
      "satisfaction_cible": "..."
    }},
    "CTA": {{
      "type_cta": "...",
      "phrase_exacte": "...",
      "lien_sujet": "..."
    }}
  }},
  "analysis_notes": "Notes sur les patterns identifiés, règles de l'ARCHIVUM appliquées",
  "rules_applied": ["règle 1", "règle 2"]
}}
```

Ne retourne RIEN d'autre que le JSON. Pas de texte avant. Pas de texte après.
Le JSON doit être valide et parseable par json.loads().
"""

    return prompt


def save_iron_prompt(prompt: str) -> str:
    """Sauvegarde le prompt assemblé dans F02_BREACHER/OUT/iron_prompt.txt."""
    os.makedirs(_F02_OUT, exist_ok=True)
    path = os.path.join(_F02_OUT, "iron_prompt.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(prompt)
    return path


def validate_skeleton(skeleton_path: str = None) -> dict:
    """
    Valide le skeleton.json produit par l'IRON.
    Vérifie la présence de tous les éléments attendus.
    """
    if skeleton_path is None:
        skeleton_path = os.path.join(_F02_OUT, "skeleton.json")

    if not os.path.exists(skeleton_path):
        return {"valid": False, "error": f"skeleton.json introuvable: {skeleton_path}"}

    try:
        with open(skeleton_path, "r", encoding="utf-8") as f:
            skeleton = json.load(f)
    except json.JSONDecodeError as e:
        return {"valid": False, "error": f"JSON invalide: {e}"}

    # Vérifier les éléments attendus
    required_elements = ["Hook", "Promise", "Rehook_1", "Rehook_2", "Body_Structure", "Payoff", "CTA"]
    skel = skeleton.get("skeleton", {})

    missing = [el for el in required_elements if el not in skel]
    if missing:
        return {"valid": False, "error": f"Éléments manquants: {missing}", "skeleton": skeleton}

    # Vérifier les champs d'extraction
    field_checks = {
        "Hook": ["type_hook", "phrase_exacte", "emotion_cible"],
        "Promise": ["promesse_explicite", "promesse_implicite"],
        "Rehook_1": ["type_rehook", "phrase_exacte"],
        "Rehook_2": ["type_rehook", "phrase_exacte"],
        "Body_Structure": ["type_structure", "nombre_sections", "rythme"],
        "Payoff": ["reponse_promesse", "satisfaction_cible"],
        "CTA": ["type_cta", "phrase_exacte", "lien_sujet"],
    }

    incomplete = []
    for el, fields in field_checks.items():
        for field in fields:
            if field not in skel[el] or not skel[el][field]:
                incomplete.append(f"{el}.{field}")

    if incomplete:
        return {"valid": False, "error": f"Champs incomplets: {incomplete}", "skeleton": skeleton}

    return {"valid": True, "error": None, "skeleton": skeleton}


def check_in_iw_custos(output_path: str):
    """Signale à IW_CUSTOS.py que F02 a terminé."""
    custos_path = os.path.join(_PROJECT_ROOT, "IW_CUSTOS.py")
    if os.path.exists(custos_path):
        import subprocess
        result = subprocess.run(
            [sys.executable, custos_path, "--mode", "check-in", "--frigate", "F02", "--output", output_path],
            capture_output=True, text=True, timeout=30
        )
        print(f"[F02] IW_CUSTOS: {result.stdout.strip()}")
        if result.stderr:
            print(f"[F02] IW_CUSTOS stderr: {result.stderr.strip()}")
    else:
        print(f"[F02] ⚠️ IW_CUSTOS.py non trouvé — check-in ignoré")


def cmd_prepare(args):
    """Phase 1 : assemble le prompt pour l'IRON."""
    print("=" * 60)
    print("🧨 F02_BREACHER — Le Briseur de Murs")
    print("=" * 60)

    # 1. Charger le specimen
    print("\n[F02] Chargement du specimen...")
    specimen = load_specimen(args.specimen)
    print(f"[F02] Video: {specimen.get('title', 'N/A')}")
    print(f"[F02] Transcript: {specimen.get('transcript', {}).get('segment_count', 0)} segments")

    # 2. Charger les contrats + ARCHIVUM
    print("\n[F02] Chargement des contrats et de l'ARCHIVUM...")
    contracts = load_all()
    print(f"[F02] Checklist: {len(contracts['skeleton_checklist']['viral_skeleton_elements'])} éléments")
    print(f"[F02] Anti-bullshit: {len(contracts['anti_bullshit'])} caractères")
    print(f"[F02] Règles ARCHIVUM: {contracts['meta']['rules_count']} fichiers")
    print(f"[F02] Transcripts ARCHIVUM: {contracts['meta']['transcripts_count']} fichiers")

    # 3. Assembler le prompt
    print("\n[F02] Assemblage du prompt pour l'IRON...")
    prompt = assemble_iron_prompt(specimen, contracts)
    prompt_path = save_iron_prompt(prompt)
    prompt_size = len(prompt.encode("utf-8")) / 1024
    print(f"[F02] Prompt sauvegardé: {prompt_path} ({prompt_size:.1f} KB)")

    # 4. Instructions pour l'IRON
    print(f"\n{'=' * 60}")
    print(f"🛠️  PROMPT PRÊT — EN ATTENTE DE L'IRON (Claude sandbox)")
    print(f"{'=' * 60}")
    print(f"\nLe prompt est dans: {prompt_path}")
    print(f"\nL'IRON (Claude) doit :")
    print(f"  1. Lire {prompt_path}")
    print(f"  2. Analyser la transcription avec la checklist")
    print(f"  3. Extraire le squelette viral")
    print(f"  4. Écrire le résultat dans F02_BREACHER/OUT/skeleton.json")
    print(f"\nEnsuite, lancer :")
    print(f"  python breacher.py --finalize")
    print(f"\nPour vérifier l'état :")
    print(f"  python breacher.py --status")


def cmd_finalize(args):
    """Phase 3 : valide le skeleton.json et check-in."""
    print("=" * 60)
    print("🧨 F02_BREACHER — FINALISATION")
    print("=" * 60)

    skeleton_path = args.skeleton if args.skeleton else os.path.join(_F02_OUT, "skeleton.json")

    print(f"\n[F02] Validation de {skeleton_path}...")
    result = validate_skeleton(skeleton_path)

    if not result["valid"]:
        print(f"[F02] ❌ VALIDATION ÉCHOUÉE: {result['error']}")
        sys.exit(1)

    skeleton = result["skeleton"]
    print(f"[F02] ✅ Squelette valide !")
    print(f"[F02] Hook: {skeleton['skeleton']['Hook']['type_hook']} — \"{skeleton['skeleton']['Hook']['phrase_exacte'][:60]}...\"")
    print(f"[F02] Body: {skeleton['skeleton']['Body_Structure']['type_structure']} ({skeleton['skeleton']['Body_Structure']['nombre_sections']} sections)")
    print(f"[F02] CTA: {skeleton['skeleton']['CTA']['type_cta']}")

    if skeleton.get("rules_applied"):
        print(f"[F02] Règles appliquées: {skeleton['rules_applied']}")

    # Check-in IW_CUSTOS
    if not args.no_checkin:
        check_in_iw_custos(skeleton_path)

    print(f"\n{'=' * 60}")
    print(f"🧨 F02_BREACHER — MISSION ACCOMPLIE")
    print(f"{'=' * 60}")
    print(f"Squelette: {skeleton_path}")
    print(f"Prochaine étape: Porte 2 (validation du Warsmith) → F03_FORGEWARD")


def cmd_status(args):
    """Vérifie l'état de F02."""
    print("=" * 60)
    print("🧨 F02_BREACHER — ÉTAT")
    print("=" * 60)

    # Vérifier IN
    specimen_path = os.path.join(_F02_IN, "specimen.json")
    has_specimen = os.path.exists(specimen_path)
    print(f"\n[IN]  specimen.json: {'✅ présent' if has_specimen else '❌ absent'}")

    # Vérifier OUT
    prompt_path = os.path.join(_F02_OUT, "iron_prompt.txt")
    skeleton_path = os.path.join(_F02_OUT, "skeleton.json")

    has_prompt = os.path.exists(prompt_path)
    has_skeleton = os.path.exists(skeleton_path)

    print(f"[OUT] iron_prompt.txt: {'✅ prêt' if has_prompt else '❌ absent'}")
    print(f"[OUT] skeleton.json:   {'✅ prêt' if has_skeleton else '❌ en attente de l'IRON'}")

    if has_prompt and not has_skeleton:
        print(f"\n→ L'IRON doit produire skeleton.json")
        print(f"  Lire: {prompt_path}")
        print(f"  Écrire: {skeleton_path}")
    elif has_skeleton:
        print(f"\n→ Lancer: python breacher.py --finalize")
    elif not has_specimen:
        print(f"\n→ Placer specimen.json dans F02_BREACHER/IN/")
    else:
        print(f"\n→ Lancer: python breacher.py --prepare")


def main():
    parser = argparse.ArgumentParser(description="F02_BREACHER — Le Briseur de Murs")
    subparsers = parser.add_subparsers(dest="command", help="Phase d'exécution")

    # --prepare
    p_prepare = subparsers.add_parser("prepare", help="Phase 1 : assembler le prompt pour l'IRON")
    p_prepare.add_argument("--specimen", default=None, help="Chemin vers specimen.json (défaut: F02_BREACHER/IN/)")
    p_prepare.set_defaults(func=cmd_prepare)

    # --finalize
    p_finalize = subparsers.add_parser("finalize", help="Phase 3 : valider skeleton.json et check-in")
    p_finalize.add_argument("--skeleton", default=None, help="Chemin vers skeleton.json (défaut: F02_BREACHER/OUT/)")
    p_finalize.add_argument("--no-checkin", action="store_true", help="Ne pas signaler à IW_CUSTOS.py")
    p_finalize.set_defaults(func=cmd_finalize)

    # --status
    p_status = subparsers.add_parser("status", help="Vérifier l'état de F02")
    p_status.set_defaults(func=cmd_status)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
