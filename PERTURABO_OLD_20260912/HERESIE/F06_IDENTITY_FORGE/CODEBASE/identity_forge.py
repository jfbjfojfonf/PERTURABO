"""
identity_forge.py — F06_IDENTITY_FORGE : Le Forgeur d'Identité
================================================================

Frégate de création d'identité de chaîne YouTube.
Forge le nom, la description, les tags, le tone of voice, les codes visuels,
le banner et le logo d'une nouvelle chaîne.

ARCHITECTURE HYBRIDE :
  Phase 1 (--prepare) : identity_forge.py assemble le prompt (niche + specimen + contrats)
  Phase 2 (IRON)      : Claude (sandbox) analyse le specimen, dérive le tone of voice,
                        propose 10 noms classés, génère banner + logo via image_generator,
                        écrit channel_identity.json
  Phase 3 (--finalize): identity_forge.py valide → check-in IW_CUSTOS
                        → enregistre dans ARCHIVUM/channels/

OUTPUTS :
  - channel_identity.json : nom, description, tags, tone, codes visuels, format standard
  - banner.png            : bannière YouTube (générée par l'IRON)
  - logo.png              : logo/avatar de chaîne (généré par l'IRON)
  - iron_prompt.txt       : le prompt assemblé (phase 1)

Usage:
  python identity_forge.py --prepare --niche "Hurricanes US" --specimen ../IN/specimen.json
  python identity_forge.py --finalize
  python identity_forge.py --status
  python identity_forge.py --register --channel-name "Abyssal Storms"
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

# Path anchoring
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_F06_DIR = os.path.dirname(_SCRIPT_DIR)
_PROJECT_ROOT = os.path.dirname(_F06_DIR)
_F06_IN = os.path.join(_F06_DIR, "IN")
_F06_OUT = os.path.join(_F06_DIR, "OUT")
_CHANNELS_DIR = os.path.join(_PROJECT_ROOT, "ARCHIVUM", "channels")

# Import local
sys.path.insert(0, _SCRIPT_DIR)
from contracts_loader import load_all


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_specimen(specimen_path: str = None) -> dict:
    """Charge specimen.json depuis F06_IDENTITY_FORGE/IN/."""
    if specimen_path is None:
        specimen_path = os.path.join(_F06_IN, "specimen.json")
    if not os.path.exists(specimen_path):
        return {}
    with open(specimen_path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_niche_report(report_path: str = None) -> dict:
    """Charge niche_report.json depuis F06_IDENTITY_FORGE/IN/ (Mode Chaîne)."""
    if report_path is None:
        report_path = os.path.join(_F06_IN, "niche_report.json")
    if not os.path.exists(report_path):
        return {}
    with open(report_path, "r", encoding="utf-8") as f:
        return json.load(f)


def assemble_iron_prompt(niche: str, specimen: dict, niche_report: dict,
                         contracts: dict, num_names: int = 10) -> str:
    """
    Assemble le prompt complet pour l'IRON.
    Inclut : contrats, ARCHIVUM, specimen, niche report, instructions de forge.
    """
    iron_prompt = contracts.get("iron_prompt", "")
    anti_bullshit = contracts.get("anti_bullshit", "")
    archivum_rules = contracts.get("archivum_rules", "")
    system_prompt = contracts.get("system_prompt", "")

    # Extraire les infos du specimen
    specimen_title = specimen.get("title", "N/A")
    specimen_channel = specimen.get("channel", {}).get("name", "N/A")
    specimen_desc = specimen.get("description", "N/A")[:500] if specimen.get("description") else "N/A"
    specimen_outlier = specimen.get("outlier_score", "N/A")

    # Extraire les infos du niche report
    concept = niche_report.get("concept_identified", "N/A")
    format_identified = niche_report.get("format_identified", "N/A")
    recommended = niche_report.get("recommended_niche", niche)
    first_ideas = niche_report.get("blue_ocean_validations", [])
    first_ideas_str = json.dumps(first_ideas[:3], ensure_ascii=False, indent=2) if first_ideas else "N/A"

    prompt = f"""# MISSION DE L'IRON — F06_IDENTITY_FORGE

## CONTRAT SYSTÈME
{system_prompt}

## CONTRAT IRON
{iron_prompt}

## ANTI-BULLSHIT
{anti_bullshit}

## MÉMOIRE IMPÉRIALE (ARCHIVUM)
{archivum_rules}

## CONTEXTE DU SIÈGE

### Niche validée
{recommended}

### Concept identifié
{concept}

### Format identifié
{format_identified}

### Specimen de référence
- Titre : {specimen_title}
- Chaîne : {specimen_channel}
- Outlier Score : {specimen_outlier}
- Description (extrait) : {specimen_desc}

### Premières idées de vidéos
{first_ideas_str}

## TA MISSION — FORGER L'IDENTITÉ DE LA CHAÎNE

Tu dois produire un fichier `channel_identity.json` avec les éléments suivants :

### 1. NOM DE CHAÎNE — {num_names} PROPOSITIONS CLASSÉES
Propose {num_names} noms de chaîne, classés du MEILLEUR au PIRE.
Pour chaque nom :
- Le nom lui-même (court, mémorisable, disponible comme handle YouTube)
- Pourquoi il fonctionne (rationnel stratégique)
- Score de mémorabilité (1-10)
- Score de SEO (1-10)
- Score de marque (1-10)

Règles pour les noms :
- Maximum 2-3 mots
- Pas de chiffres (sauf si pertinent au concept)
- Prononçable à l'oral
- Évocateur de la niche sans être générique
- Pas de nom déjà pris par une grosse chaîne

### 2. DESCRIPTION YOUTUBE
Format : Hook (1 phrase accrocheuse) + Mission (2-3 phrases) + SEO (mots-clés naturels)
Max 1000 caractères.

### 3. TAGS
15-20 tags : mix de tags larges (ex: "hurricane", "weather") et spécifiques (ex: "category 5", "saffir simpson").

### 4. TONE OF VOICE — DÉRIVÉ DU SPECIMEN
Analyse le specimen et dérive automatiquement :
- Registre verbal (ex: "dense, factuel, zéro blabla")
- Rythme (ex: "métronomique, ~35s par type")
- Vocabulaire signature (ex: "Nom. Définition. Chiffres. Fait dingue. Suivant.")
- Personnalité (ex: "professeur fasciné, pas animateur TV")
- Ce que la chaîne ne FAIT JAMAIS (ex: "jamais de 'bonjour à tous', jamais de CTA 'abonne-toi'")

### 5. CODES VISUELS
- Palette de couleurs principale (ex: "vert→rouge gradient, fond blanc")
- Style graphique (ex: "infographie flat, pictogrammes, pas de photo")
- Template miniature (ex: "grille de cercles colorés avec silhouettes noires")
- Typographie (ex: "Impact Bold, sans-serif, gras")

### 6. FORMAT STANDARD
- Durée cible (ex: "5-6 min")
- Nombre de types par vidéo (ex: "7-8")
- Structure (ex: "Every Type Of X Explained in Y minutes")
- Fréquence de publication recommandée

### 7. BANNER — PROMPT IMAGE_GENERATOR
Écris un prompt détaillé pour image_generator qui produira la bannière YouTube.
Format : 2560x1440 (ratio 16:9), zone safe au centre.
Style : cohérent avec les codes visuels définis ci-dessus.

### 8. LOGO — PROMPT IMAGE_GENERATOR
Écris un prompt détaillé pour image_generator qui produira le logo/avatar.
Format : carré 1:1, pictogramme simple, lisible à 32x32 pixels.

## FORMAT DE SORTIE

Écris le fichier `channel_identity.json` dans F06_IDENTITY_FORGE/OUT/ avec cette structure :

```json
{{
  "niche": "{recommended}",
  "concept": "{concept}",
  "channel_names": [
    {{
      "rank": 1,
      "name": "...",
      "rationale": "...",
      "memorability_score": 0,
      "seo_score": 0,
      "brand_score": 0
    }}
  ],
  "description": "...",
  "tags": ["..."],
  "tone_of_voice": {{
    "register": "...",
    "rhythm": "...",
    "signature_vocabulary": "...",
    "personality": "...",
    "never_does": ["..."]
  }},
  "visual_codes": {{
    "color_palette": "...",
    "graphic_style": "...",
    "thumbnail_template": "...",
    "typography": "..."
  }},
  "format_standard": {{
    "target_duration": "...",
    "types_per_video": 0,
    "structure": "...",
    "publish_frequency": "..."
  }},
  "banner_prompt": "...",
  "logo_prompt": "...",
  "f06_meta": {{
    "forged_at": "{now_iso()}",
    "model_used": "claude-sandbox",
    "specimen_source": "{specimen_title}",
    "rules_applied": []
  }}
}}
```

Une fois le JSON écrit, l'IRON génère aussi :
- `banner.png` via image_generator (utilise banner_prompt)
- `logo.png` via image_generator (utilise logo_prompt)

Sauvegarde ces images dans F06_IDENTITY_FORGE/OUT/.
"""

    return prompt


def cmd_prepare(args):
    """Phase 1 : assemble le prompt pour l'IRON."""
    print(f"\n{'='*60}")
    print(f"F06_IDENTITY_FORGE — Phase 1 : Préparation du prompt")
    print(f"{'='*60}\n")

    # Charger les inputs
    specimen = load_specimen(args.specimen)
    niche_report = load_niche_report(args.niche_report)

    # Charger les contrats
    contracts = load_all()
    print(f"[F06] Contrats chargés :")
    print(f"  System prompt : {len(contracts.get('system_prompt', ''))} chars")
    print(f"  Iron prompt   : {len(contracts.get('iron_prompt', ''))} chars")
    print(f"  Anti-bullshit : {len(contracts.get('anti_bullshit', ''))} chars")
    print(f"  ARCHIVUM rules: {contracts.get('meta', {}).get('rules_count', 0)} fichiers")

    # Assembler le prompt
    prompt = assemble_iron_prompt(
        niche=args.niche,
        specimen=specimen,
        niche_report=niche_report,
        contracts=contracts,
        num_names=args.num_names
    )

    # Écrire le prompt
    prompt_path = os.path.join(_F06_OUT, "iron_prompt.txt")
    os.makedirs(_F06_OUT, exist_ok=True)
    with open(prompt_path, "w", encoding="utf-8") as f:
        f.write(prompt)

    print(f"\n[F06] Prompt assemblé : {prompt_path}")
    print(f"[F06] Taille du prompt : {len(prompt)} caractères")
    print(f"\n[F06] 🛠️ Prompt prêt. En attente de l'IRON (Claude sandbox).")
    print(f"[F06] L'IRON doit :")
    print(f"  1. Lire iron_prompt.txt")
    print(f"  2. Analyser le specimen pour dériver le tone of voice")
    print(f"  3. Proposer {args.num_names} noms classés du meilleur au pire")
    print(f"  4. Écrire channel_identity.json dans F06_IDENTITY_FORGE/OUT/")
    print(f"  5. Générer banner.png via image_generator")
    print(f"  6. Générer logo.png via image_generator")
    print(f"\n[F06] Ensuite : python identity_forge.py --finalize")


def validate_channel_identity(data: dict) -> tuple:
    """Valide la structure de channel_identity.json. Retourne (ok, erreurs)."""
    errors = []

    required_sections = [
        "niche", "channel_names", "description", "tags",
        "tone_of_voice", "visual_codes", "format_standard",
        "banner_prompt", "logo_prompt", "f06_meta"
    ]

    for section in required_sections:
        if section not in data:
            errors.append(f"Section manquante : {section}")

    # Valider les noms
    names = data.get("channel_names", [])
    if len(names) < 3:
        errors.append(f"Trop peu de noms proposés : {len(names)} (min 3)")
    for i, n in enumerate(names):
        if "name" not in n:
            errors.append(f"Nom #{i+1} : champ 'name' manquant")
        if "rank" not in n:
            errors.append(f"Nom #{i+1} : champ 'rank' manquant")

    # Valider le tone of voice
    tov = data.get("tone_of_voice", {})
    for field in ["register", "rhythm", "personality"]:
        if field not in tov:
            errors.append(f"tone_of_voice.{field} manquant")

    # Valider les codes visuels
    vc = data.get("visual_codes", {})
    for field in ["color_palette", "graphic_style", "thumbnail_template"]:
        if field not in vc:
            errors.append(f"visual_codes.{field} manquant")

    return (len(errors) == 0, errors)


def cmd_finalize(args):
    """Phase 3 : valide channel_identity.json et check-in IW_CUSTOS."""
    print(f"\n{'='*60}")
    print(f"F06_IDENTITY_FORGE — Phase 3 : Finalisation")
    print(f"{'='*60}\n")

    identity_path = os.path.join(_F06_OUT, "channel_identity.json")
    if not os.path.exists(identity_path):
        print(f"[F06] ❌ channel_identity.json introuvable dans OUT/")
        print(f"[F06] L'IRON n'a pas encore produit l'identité.")
        return

    with open(identity_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    ok, errors = validate_channel_identity(data)
    if not ok:
        print(f"[F06] ❌ Validation échouée :")
        for e in errors:
            print(f"  - {e}")
        return

    print(f"[F06] ✅ channel_identity.json validé")
    names = data.get("channel_names", [])
    print(f"[F06] Noms proposés : {len(names)}")
    for n in names[:5]:
        print(f"  #{n.get('rank', '?')}: {n.get('name', 'N/A')}")

    # Vérifier les images
    banner_path = os.path.join(_F06_OUT, "banner.png")
    logo_path = os.path.join(_F06_OUT, "logo.png")
    print(f"[F06] Banner : {'✅' if os.path.exists(banner_path) else '❌'}")
    print(f"[F06] Logo   : {'✅' if os.path.exists(logo_path) else '❌'}")

    # Check-in IW_CUSTOS
    print(f"\n[F06] Check-in IW_CUSTOS...")
    iw_custos = os.path.join(_PROJECT_ROOT, "IW_CUSTOS.py")
    os.system(f"python3 {iw_custos} --mode check-in --frigate F06 --output {identity_path}")

    print(f"\n[F06] ✅ Identité forgée. En attente de validation du Warsmith.")
    print(f"[F06] Pour enregistrer la chaîne : python identity_forge.py --register --channel-name \"Nom Choisi\"")


def cmd_register(args):
    """Enregistre la chaîne dans ARCHIVUM/channels/."""
    print(f"\n{'='*60}")
    print(f"F06_IDENTITY_FORGE — Enregistrement de la chaîne")
    print(f"{'='*60}\n")

    identity_path = os.path.join(_F06_OUT, "channel_identity.json")
    if not os.path.exists(identity_path):
        print(f"[F06] ❌ channel_identity.json introuvable.")
        return

    with open(identity_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    channel_name = args.channel_name
    slug = channel_name.lower().replace(" ", "_").replace("-", "_")

    # Créer le dossier de la chaîne
    channel_dir = os.path.join(_CHANNELS_DIR, slug)
    os.makedirs(channel_dir, exist_ok=True)
    os.makedirs(os.path.join(channel_dir, "videos"), exist_ok=True)

    # Copier l'identité
    import shutil
    shutil.copy2(identity_path, os.path.join(channel_dir, "channel_identity.json"))

    # Copier les images si elles existent
    banner_src = os.path.join(_F06_OUT, "banner.png")
    logo_src = os.path.join(_F06_OUT, "logo.png")
    if os.path.exists(banner_src):
        shutil.copy2(banner_src, os.path.join(channel_dir, "banner.png"))
    if os.path.exists(logo_src):
        shutil.copy2(logo_src, os.path.join(channel_dir, "logo.png"))

    # Créer performance.json (Phase 1 — manuel)
    performance = {
        "channel": channel_name,
        "channel_slug": slug,
        "videos": [],
        "last_sweep": None,
        "auto_tracking": False,
        "created_at": now_iso()
    }
    perf_path = os.path.join(channel_dir, "performance.json")
    with open(perf_path, "w", encoding="utf-8") as f:
        json.dump(performance, f, ensure_ascii=False, indent=2)

    # Mettre à jour le registry
    registry_path = os.path.join(_CHANNELS_DIR, "registry.json")
    if os.path.exists(registry_path):
        with open(registry_path, "r", encoding="utf-8") as f:
            registry = json.load(f)
    else:
        registry = {"channels": {}}

    registry["channels"][slug] = {
        "name": channel_name,
        "slug": slug,
        "niche": data.get("niche", ""),
        "concept": data.get("concept", ""),
        "created_at": now_iso(),
        "videos_count": 0,
        "identity_path": f"ARCHIVUM/channels/{slug}/channel_identity.json",
        "performance_path": f"ARCHIVUM/channels/{slug}/performance.json",
        "banner": f"ARCHIVUM/channels/{slug}/banner.png" if os.path.exists(banner_src) else None,
        "logo": f"ARCHIVUM/channels/{slug}/logo.png" if os.path.exists(logo_src) else None,
    }

    with open(registry_path, "w", encoding="utf-8") as f:
        json.dump(registry, f, ensure_ascii=False, indent=2)

    print(f"[F06] ✅ Chaîne enregistrée : {channel_name}")
    print(f"[F06] Dossier : ARCHIVUM/channels/{slug}/")
    print(f"[F06] Registry mis à jour : {registry_path}")
    print(f"[F06] performance.json créé (Phase 1 — tracking manuel)")


def cmd_status(args):
    """Affiche l'état de F06."""
    print(f"\nF06_IDENTITY_FORGE — Statut")
    print(f"{'='*40}")

    prompt_path = os.path.join(_F06_OUT, "iron_prompt.txt")
    identity_path = os.path.join(_F06_OUT, "channel_identity.json")
    banner_path = os.path.join(_F06_OUT, "banner.png")
    logo_path = os.path.join(_F06_OUT, "logo.png")

    print(f"  Prompt prêt     : {'✅' if os.path.exists(prompt_path) else '❌'}")
    print(f"  Identité forgée : {'✅' if os.path.exists(identity_path) else '❌'}")
    print(f"  Banner généré   : {'✅' if os.path.exists(banner_path) else '❌'}")
    print(f"  Logo généré     : {'✅' if os.path.exists(logo_path) else '❌'}")

    # Registry
    registry_path = os.path.join(_CHANNELS_DIR, "registry.json")
    if os.path.exists(registry_path):
        with open(registry_path, "r", encoding="utf-8") as f:
            registry = json.load(f)
        channels = registry.get("channels", {})
        print(f"\n  Chaînes enregistrées : {len(channels)}")
        for slug, info in channels.items():
            print(f"    - {info.get('name', slug)} ({info.get('niche', 'N/A')}) — {info.get('videos_count', 0)} vidéos")
    else:
        print(f"\n  Aucune chaîne enregistrée.")


def main():
    parser = argparse.ArgumentParser(description="F06_IDENTITY_FORGE — Le Forgeur d'Identité")
    subparsers = parser.add_subparsers(dest="command", help="Commande")

    # --prepare
    p_prepare = subparsers.add_parser("prepare", help="Phase 1 : assembler le prompt pour l'IRON")
    p_prepare.add_argument("--niche", required=True, help="Niche validée")
    p_prepare.add_argument("--specimen", default=None, help="Chemin vers specimen.json")
    p_prepare.add_argument("--niche-report", default=None, help="Chemin vers niche_report.json")
    p_prepare.add_argument("--num-names", type=int, default=10, help="Nombre de propositions de nom")
    p_prepare.set_defaults(func=cmd_prepare)

    # --finalize
    p_finalize = subparsers.add_parser("finalize", help="Phase 3 : valider et check-in")
    p_finalize.set_defaults(func=cmd_finalize)

    # --register
    p_register = subparsers.add_parser("register", help="Enregistrer la chaîne dans ARCHIVUM/channels/")
    p_register.add_argument("--channel-name", required=True, help="Nom choisi par le Warsmith")
    p_register.set_defaults(func=cmd_register)

    # --status
    p_status = subparsers.add_parser("status", help="Afficher l'état de F06")
    p_status.set_defaults(func=cmd_status)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
