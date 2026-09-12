"""
forgeward.py — F03_FORGEWARD : La Forge de Fer
================================================

Frégate de génération de script.
Prend le squelette viral de F02_BREACHER + la niche du Warsmith et forge
un script original au format META_01 (compatible CRUSADER/SANCTORUM/DORN).

ARCHITECTURE HYBRIDE :
  Phase 1 (--prepare) : forgeward.py assemble le prompt → iron_prompt.txt
  Phase 2 (IRON)      : Claude (sandbox) lit le prompt, génère, écrit script.json
  Phase 3 (--finalize): forgeward.py valide script.json + génère timing.json + exports → check-in

OUTPUTS :
  - script.json        : script structuré + métadonnées + timing par ligne
  - script_raw.txt     : format META_01 (balises [ACCROCHE], [mots_forts], ...)
  - timing.json        : segments avec start/end pour calage visuel (META_02)
  - metadata.txt       : titre + hashtags + description prêts à copier-coller

Usage:
  python forgeward.py --prepare --niche "Le Seigneur des Anneaux" --format SHORT --duree 60
  python forgeward.py --finalize
  python forgeward.py --status
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

# Path anchoring
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_F03_DIR = os.path.dirname(_SCRIPT_DIR)
_PROJECT_ROOT = os.path.dirname(_F03_DIR)
_F03_IN = os.path.join(_F03_DIR, "IN")
_F03_OUT = os.path.join(_F03_DIR, "OUT")

# Import contracts_loader (local)
sys.path.insert(0, _SCRIPT_DIR)
from contracts_loader import load_all


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_skeleton(skeleton_path: str = None) -> dict:
    """Charge skeleton.json depuis F03_FORGEWARD/IN/ ou un chemin spécifié."""
    if skeleton_path is None:
        skeleton_path = os.path.join(_F03_IN, "skeleton.json")
    if not os.path.exists(skeleton_path):
        raise FileNotFoundError(
            f"Squelette introuvable: {skeleton_path}\n"
            f"Place skeleton.json (de F02_BREACHER/OUT/) dans F03_FORGEWARD/IN/"
        )
    with open(skeleton_path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_brief(brief_path: str = None) -> dict:
    """Charge brief.json depuis F03_FORGEWARD/IN/ (contient la niche, le format, la durée)."""
    if brief_path is None:
        brief_path = os.path.join(_F03_IN, "brief.json")
    if not os.path.exists(brief_path):
        return {}
    with open(brief_path, "r", encoding="utf-8") as f:
        return json.load(f)


def assemble_iron_prompt(skeleton: dict, brief: dict, contracts: dict,
                         niche: str, fmt: str, duree: int) -> str:
    """
    Assemble le prompt complet pour l'IRON (Claude sandbox).
    Inclut : le squelette viral, la niche, les règles META_01, l'anti-bullshit,
    l'ARCHIVUM, et les instructions de génération avec timing.
    """
    skeleton_json = json.dumps(skeleton.get("skeleton", {}), ensure_ascii=False, indent=2)
    analysis_notes = skeleton.get("analysis_notes", "")
    rules_applied = skeleton.get("rules_applied", [])
    source_title = skeleton.get("source_title", "Inconnu")

    # Timestamps du squelette pour le calage temporel
    timing_info = ""
    skel = skeleton.get("skeleton", {})
    if skel:
        timing_info = f"""
## CALAGE TEMPOREL DU SQUELETTE (de F02_BREACHER)

Le squelette viral a été extrait avec des timestamps de la vidéo originale.
Utilise ces repères temporels pour caler ton script :

- Hook : 0-5s (accroche immédiate)
- Promise : 5-15s (annonce de la valeur)
- Rehook_1 : 60-90s (relance d'attention)
- Rehook_2 : milieu (second point de rétention)
- Body_Structure : global (structure narrative)
- Payoff : fin (réponse à la promesse)
- CTA : très fin (appel à l'action)

Pour un SHORT de {duree}s, compresse ces proportions.
Pour un LONG, respecte les proportions originales.
"""

    prompt = f"""# MISSION DE L'IRON — F03_FORGEWARD

## CONTRAT
{contracts["iron_prompt"]}

## RÈGLES ANTI-BULLSHIT
{contracts["anti_bullshit"]}

## MÉMOIRE IMPÉRIALE — RÈGLES DES EXPERTS
{contracts["archivum_rules"]}

## MÉMOIRE IMPÉRIALE — TRANSCRIPTIONS DE RÉFÉRENCE
{contracts["archivum_transcripts"] or "[Aucune transcription de référence disponible]"}

---

## SQUELETTE VIRAL À RESPECTER STRICTEMENT
{timing_info}

Source : {source_title}
Notes d'analyse : {analysis_notes}
Règles appliquées : {rules_applied}

{skeleton_json}

---

## PARAMÈTRES DE PRODUCTION

- **Niche** : {niche}
- **Format** : {fmt} ({"vertical 9:16, ≤ 60s" if fmt == "SHORT" else "horizontal 16:9, > 60s"})
- **Durée cible** : {duree} secondes
- **Langue** : Français

---

## RÈGLES DE FORMAT META_01 (OBLIGATOIRES)

### Script
1. **Rythme court** : phrases courtes, une idée par phrase. Maximum 12 mots par phrase.
2. **Balisage des mots forts** : encadre les mots-clés avec `[mot]`. Maximum 2 mots forts par phrase.
3. **Pauses** : indique les pauses avec `...` (3 points).
4. **Structure balisée** : `[ACCROCHE]`, `[DÉVELOPPEMENT]`, `[CHUTE/CTA]`.
5. **Pas de ponctuation complexe** : virgules et points uniquement.
6. **CTA final** : appel à l'action naturel intégré au ton du script.
7. **Durée vs lignes** : ~2.5s par ligne. Pour {duree}s → ~{duree // 2.5:.0f} lignes.

### Métadonnées
- **Titre** : {"choc, question brutale ou chiffre. 1 emoji en fin. Max 45 caractères" if fmt == "SHORT" else "angle viral + promesse/révélation. 1 emoji en fin. Max 45 caractères"}
- **Hashtags** : exactement 3 (2 spécifiques + 1 récurrent #animation)
- **Description** : 4 blocs :
  - Bloc 1 : accroche virale (2-3 lignes)
  - Bloc 2 (FIXE — reproduire EXACTEMENT) :
    "Chaque vidéo publiée sur cette chaîne est le résultat d'une enquête personnelle et minutieuse menée par le propriétaire de la chaîne. Les faits, données et informations présentés ont été rigoureusement vérifiés et recoupés avant toute mise en production.\\n\\nCe contenu — script, narration et production visuelle — est entièrement conçu et réalisé par le propriétaire de la chaîne, sans template ni production en série.\\n\\nCe contenu est la propriété intellectuelle exclusive de cette chaîne. Toute reproduction, rediffusion ou réutilisation — partielle ou totale — sans autorisation écrite préalable est strictement interdite."
  - Bloc 3 : hashtags en ligne
  - Bloc 4 : 10-15 mots-clés SEO nus séparés par des espaces

---

## FORMAT DE SORTIE ATTENDU (JSON)

Retourne UNIQUEMENT un JSON valide avec cette structure exacte :

```json
{{
  "source_skeleton": "{skeleton.get("source_video_id", "unknown")}",
  "niche": "{niche}",
  "format": "{fmt}",
  "duree_cible": {duree},

  "script_raw": "[ACCROCHE]\\nLigne 1 avec [mot_fort]...\\nLigne 2...\\n\\n[DÉVELOPPEMENT]\\n...\\n\\n[CHUTE/CTA]\\n...",

  "script_structured": [
    {{
      "section": "ACCROCHE",
      "lines": [
        {{
          "text": "Ligne avec [mot_fort]",
          "mots_forts": ["mot_fort"],
          "timing": {{"start": 0.0, "end": 2.5}}
        }}
      ]
    }},
    {{
      "section": "DÉVELOPPEMENT",
      "lines": [...]
    }},
    {{
      "section": "CHUTE/CTA",
      "lines": [...]
    }}
  ],

  "timing": {{
    "segments": [
      {{"id": 1, "start": 0.0, "end": 2.5, "text": "..."}},
      {{"id": 2, "start": 2.5, "end": 5.0, "text": "..."}}
    ],
    "total_duration": {duree}.0,
    "format": "{fmt}"
  }},

  "metadata": {{
    "title": "Titre optimisé 😱",
    "hashtags": ["#tag1", "#tag2", "#animation"],
    "description": {{
      "bloc_1_accroche": "2-3 lignes reformulant l'angle",
      "bloc_2_qualite": "Chaque vidéo publiée sur cette chaîne est le résultat...",
      "bloc_3_hashtags": "#tag1 #tag2 #animation",
      "bloc_4_seo": "mots-clés seo mot1 mot2 mot3 mot4 mot5 mot6 mot7 mot8 mot9 mot10"
    }}
  }},

  "thumbnail_text": "3-4 MOTS MAX",

  "f03_meta": {{
    "forged_at": "{now_iso()}",
    "skeleton_respected": true,
    "timing_source": "F02_skeleton + estimation 2.5s/ligne",
    "rules_applied": ["règle 1", "règle 2"]
  }}
}}
```

### RÈGLES DE TIMING
- Chaque ligne = ~2.5 secondes (start = somme des durations précédentes)
- Le timing doit être CONTINU (pas de gap, pas de chevauchement)
- Le total doit approcher {duree}s
- Les segments du timing.json correspondent 1:1 aux lignes du script_structured

Ne retourne RIEN d'autre que le JSON. Pas de texte avant. Pas de texte après.
"""

    return prompt


def save_iron_prompt(prompt: str) -> str:
    """Sauvegarde le prompt assemblé dans F03_FORGEWARD/OUT/iron_prompt.txt."""
    os.makedirs(_F03_OUT, exist_ok=True)
    path = os.path.join(_F03_OUT, "iron_prompt.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(prompt)
    return path


def validate_script(script_path: str = None) -> dict:
    """Valide le script.json produit par l'IRON."""
    if script_path is None:
        script_path = os.path.join(_F03_OUT, "script.json")

    if not os.path.exists(script_path):
        return {"valid": False, "error": f"script.json introuvable: {script_path}"}

    try:
        with open(script_path, "r", encoding="utf-8") as f:
            script = json.load(f)
    except json.JSONDecodeError as e:
        return {"valid": False, "error": f"JSON invalide: {e}"}

    # Vérifier les champs obligatoires
    required = ["niche", "format", "script_raw", "script_structured", "timing", "metadata"]
    missing = [k for k in required if k not in script]
    if missing:
        return {"valid": False, "error": f"Champs manquants: {missing}", "script": script}

    # Vérifier les sections du script
    sections = [s.get("section", "") for s in script["script_structured"]]
    required_sections = ["ACCROCHE", "DÉVELOPPEMENT", "CHUTE/CTA"]
    missing_sections = [s for s in required_sections if s not in sections]
    if missing_sections:
        return {"valid": False, "error": f"Sections manquantes: {missing_sections}", "script": script}

    # Vérifier le timing
    timing = script.get("timing", {})
    segments = timing.get("segments", [])
    if not segments:
        return {"valid": False, "error": "Timing: aucun segment", "script": script}

    # Vérifier la continuité du timing
    for i, seg in enumerate(segments):
        if "start" not in seg or "end" not in seg:
            return {"valid": False, "error": f"Segment {i+1}: start/end manquants", "script": script}
        if i > 0 and abs(seg["start"] - segments[i-1]["end"]) > 0.1:
            return {"valid": False, "error": f"Gap temporel au segment {i+1}", "script": script}

    # Vérifier les métadonnées
    meta = script.get("metadata", {})
    if not meta.get("title"):
        return {"valid": False, "error": "Métadonnées: titre manquant", "script": script}

    return {"valid": True, "error": None, "script": script}


def generate_exports(script: dict) -> list:
    """
    Génère les fichiers d'export complémentaires :
    - script_raw.txt : format META_01 pour voix off
    - timing.json : pour META_02 / pipeline visuel
    - metadata.txt : prêt à copier-coller dans YouTube Studio
    """
    exports = []

    # 1. script_raw.txt
    raw_path = os.path.join(_F03_OUT, "script_raw.txt")
    with open(raw_path, "w", encoding="utf-8") as f:
        f.write(script["script_raw"])
    exports.append(raw_path)

    # 2. timing.json
    timing_path = os.path.join(_F03_OUT, "timing.json")
    timing_data = script.get("timing", {})
    with open(timing_path, "w", encoding="utf-8") as f:
        json.dump(timing_data, f, ensure_ascii=False, indent=2)
    exports.append(timing_path)

    # 3. metadata.txt
    meta_path = os.path.join(_F03_OUT, "metadata.txt")
    meta = script.get("metadata", {})
    desc = meta.get("description", {})
    meta_text = f"""[MÉTADONNÉES]

TITRE : {meta.get("title", "")}

HASHTAGS : {" ".join(meta.get("hashtags", []))}

DESCRIPTION :
{desc.get("bloc_1_accroche", "")}

{desc.get("bloc_2_qualite", "")}

{desc.get("bloc_3_hashtags", "")}

{desc.get("bloc_4_seo", "")}

---

THUMBNAIL TEXT : {script.get("thumbnail_text", "")}
"""
    with open(meta_path, "w", encoding="utf-8") as f:
        f.write(meta_text)
    exports.append(meta_path)

    return exports


def check_in_iw_custos(output_path: str):
    """Signale à IW_CUSTOS.py que F03 a terminé."""
    custos_path = os.path.join(_PROJECT_ROOT, "IW_CUSTOS.py")
    if os.path.exists(custos_path):
        import subprocess
        result = subprocess.run(
            [sys.executable, custos_path, "--mode", "check-in", "--frigate", "F03", "--output", output_path],
            capture_output=True, text=True, timeout=30
        )
        print(f"[F03] IW_CUSTOS: {result.stdout.strip()}")
        if result.stderr:
            print(f"[F03] IW_CUSTOS stderr: {result.stderr.strip()}")
    else:
        print(f"[F03] ⚠️ IW_CUSTOS.py non trouvé — check-in ignoré")


def cmd_prepare(args):
    """Phase 1 : assemble le prompt pour l'IRON."""
    print("=" * 60)
    print("⚒️  F03_FORGEWARD — La Forge de Fer")
    print("=" * 60)

    # 1. Charger le squelette
    print("\n[F03] Chargement du squelette viral...")
    skeleton = load_skeleton(args.skeleton)
    print(f"[F03] Source: {skeleton.get('source_title', 'N/A')}")

    # 2. Charger le brief (niche, format, durée)
    brief = load_brief(args.brief)
    niche = args.niche or brief.get("niche", "Non spécifiée")
    fmt = args.format or brief.get("format", "SHORT")
    duree = args.duree or brief.get("duree", 60)
    print(f"[F03] Niche: {niche}")
    print(f"[F03] Format: {fmt} — Durée cible: {duree}s")

    # 3. Charger les contrats + ARCHIVUM
    print("\n[F03] Chargement des contrats et de l'ARCHIVUM...")
    contracts = load_all()
    print(f"[F03] System prompt: {len(contracts['system_prompt'])} caractères")
    print(f"[F03] Règles ARCHIVUM: {contracts['meta']['rules_count']} fichiers")

    # 4. Assembler le prompt
    print("\n[F03] Assemblage du prompt pour l'IRON...")
    prompt = assemble_iron_prompt(skeleton, brief, contracts, niche, fmt, duree)
    prompt_path = save_iron_prompt(prompt)
    prompt_size = len(prompt.encode("utf-8")) / 1024
    print(f"[F03] Prompt sauvegardé: {prompt_path} ({prompt_size:.1f} KB)")

    # 5. Instructions pour l'IRON
    print(f"\n{'=' * 60}")
    print(f"🛠️  PROMPT PRÊT — EN ATTENTE DE L'IRON (Claude sandbox)")
    print(f"{'=' * 60}")
    print(f"\nLe prompt est dans: {prompt_path}")
    print(f"\nL'IRON (Claude) doit :")
    print(f"  1. Lire {prompt_path}")
    print(f"  2. Générer le script au format META_01 avec timing par ligne")
    print(f"  3. Générer les métadonnées (titre, hashtags, description 4 blocs)")
    print(f"  4. Écrire le résultat dans F03_FORGEWARD/OUT/script.json")
    print(f"\nEnsuite, lancer :")
    print(f"  python forgeward.py --finalize")
    print(f"\nExports générés automatiquement au finalize :")
    print(f"  - script_raw.txt  (format META_01 pour voix off)")
    print(f"  - timing.json     (calage visuel pour META_02/DORN/CRUSADER)")
    print(f"  - metadata.txt    (prêt à copier-coller YouTube Studio)")


def cmd_finalize(args):
    """Phase 3 : valide script.json, génère les exports, check-in."""
    print("=" * 60)
    print("⚒️  F03_FORGEWARD — FINALISATION")
    print("=" * 60)

    script_path = args.script if args.script else os.path.join(_F03_OUT, "script.json")

    print(f"\n[F03] Validation de {script_path}...")
    result = validate_script(script_path)

    if not result["valid"]:
        print(f"[F03] ❌ VALIDATION ÉCHOUÉE: {result['error']}")
        sys.exit(1)

    script = result["script"]
    print(f"[F03] ✅ Script valide !")
    print(f"[F03] Titre: {script['metadata']['title']}")
    print(f"[F03] Format: {script['format']} — Durée: {script.get('duree_cible', 'N/A')}s")
    print(f"[F03] Sections: {[s['section'] for s in script['script_structured']]}")
    print(f"[F03] Segments timing: {len(script['timing']['segments'])}")

    # Générer les exports
    print(f"\n[F03] Génération des exports...")
    exports = generate_exports(script)
    for e in exports:
        print(f"[F03]   → {e}")

    # Check-in IW_CUSTOS
    if not args.no_checkin:
        check_in_iw_custos(script_path)

    print(f"\n{'=' * 60}")
    print(f"⚒️  F03_FORGEWARD — MISSION ACCOMPLIE")
    print(f"{'=' * 60}")
    print(f"Script: {script_path}")
    print(f"Exports: {len(exports)} fichiers générés")
    print(f"Prochaine étape: Porte 3 (validation du Warsmith) → F04_HERALD")


def cmd_status(args):
    """Vérifie l'état de F03."""
    print("=" * 60)
    print("⚒️  F03_FORGEWARD — ÉTAT")
    print("=" * 60)

    skeleton_path = os.path.join(_F03_IN, "skeleton.json")
    brief_path = os.path.join(_F03_IN, "brief.json")
    prompt_path = os.path.join(_F03_OUT, "iron_prompt.txt")
    script_path = os.path.join(_F03_OUT, "script.json")

    print(f"\n[IN]  skeleton.json: {'✅ présent' if os.path.exists(skeleton_path) else '❌ absent'}")
    print(f"[IN]  brief.json:    {'✅ présent' if os.path.exists(brief_path) else '❌ absent'}")
    print(f"[OUT] iron_prompt.txt: {'✅ prêt' if os.path.exists(prompt_path) else '❌ absent'}")
    print(f"[OUT] script.json:     {'✅ prêt' if os.path.exists(script_path) else '❌ en attente de l'IRON'}")

    if os.path.exists(prompt_path) and not os.path.exists(script_path):
        print(f"\n→ L'IRON doit produire script.json")
        print(f"  Lire: {prompt_path}")
        print(f"  Écrire: {script_path}")
    elif os.path.exists(script_path):
        print(f"\n→ Lancer: python forgeward.py --finalize")
    elif not os.path.exists(skeleton_path):
        print(f"\n→ Placer skeleton.json dans F03_FORGEWARD/IN/")
    else:
        print(f"\n→ Lancer: python forgeward.py --prepare --niche \"...\" --format SHORT --duree 60")


def main():
    parser = argparse.ArgumentParser(description="F03_FORGEWARD — La Forge de Fer")
    subparsers = parser.add_subparsers(dest="command", help="Phase d'exécution")

    # --prepare
    p_prepare = subparsers.add_parser("prepare", help="Phase 1 : assembler le prompt pour l'IRON")
    p_prepare.add_argument("--skeleton", default=None, help="Chemin vers skeleton.json")
    p_prepare.add_argument("--brief", default=None, help="Chemin vers brief.json")
    p_prepare.add_argument("--niche", default=None, help="Niche de destination")
    p_prepare.add_argument("--format", default=None, choices=["SHORT", "LONG"], help="Format de la vidéo")
    p_prepare.add_argument("--duree", type=int, default=None, help="Durée cible en secondes")
    p_prepare.set_defaults(func=cmd_prepare)

    # --finalize
    p_finalize = subparsers.add_parser("finalize", help="Phase 3 : valider script.json + exports → check-in")
    p_finalize.add_argument("--script", default=None, help="Chemin vers script.json")
    p_finalize.add_argument("--no-checkin", action="store_true", help="Ne pas signaler à IW_CUSTOS.py")
    p_finalize.set_defaults(func=cmd_finalize)

    # --status
    p_status = subparsers.add_parser("status", help="Vérifier l'état de F03")
    p_status.set_defaults(func=cmd_status)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
