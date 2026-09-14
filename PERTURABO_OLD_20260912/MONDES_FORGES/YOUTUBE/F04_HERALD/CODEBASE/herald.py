"""
herald.py — F04_HERALD : Le Porte-Étendard
================================================

Frégate de génération de miniature.
Analyse la thumbnail de la vidéo virale d'origine (Visual Skeleton),
génère une nouvelle image adaptée à la niche (via l'IRON + image_generator),
et produit un prompt Gemini de backup + les instructions texte Canva.

ARCHITECTURE HYBRIDE :
  Phase 1 (--prepare) : herald.py télécharge la thumbnail + assemble le prompt
  Phase 2 (IRON)      : Claude (sandbox) analyse l'image, génère la nouvelle image,
                        écrit thumbnail_concept.json
  Phase 3 (--finalize): herald.py valide → check-in IW_CUSTOS

OUTPUTS :
  - thumbnail_concept.json : visual skeleton + image générée + prompt Gemini + instructions Canva
  - thumbnail.png          : l'image générée par l'IRON (image_generator)

Usage:
  python herald.py --prepare
  python herald.py --prepare --thumbnail-url "https://..." --title "..." --niche "..."
  python herald.py --finalize
  python herald.py --status
"""

import argparse
import json
import os
import sys
import base64
from datetime import datetime, timezone

# Path anchoring
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_F04_DIR = os.path.dirname(_SCRIPT_DIR)
_PROJECT_ROOT = os.path.dirname(_F04_DIR)
_F04_IN = os.path.join(_F04_DIR, "IN")
_F04_OUT = os.path.join(_F04_DIR, "OUT")

# Import local
sys.path.insert(0, _SCRIPT_DIR)
from contracts_loader import load_all
from thumb_downloader import download_thumbnail


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_specimen(specimen_path: str = None) -> dict:
    """Charge specimen.json depuis F04_HERALD/IN/ pour récupérer l'URL de la thumbnail."""
    if specimen_path is None:
        specimen_path = os.path.join(_F04_IN, "specimen.json")
    if not os.path.exists(specimen_path):
        return {}
    with open(specimen_path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_brief(brief_path: str = None) -> dict:
    """Charge brief.json (titre + niche depuis F03_FORGEWARD)."""
    if brief_path is None:
        brief_path = os.path.join(_F04_IN, "brief.json")
    if not os.path.exists(brief_path):
        return {}
    with open(brief_path, "r", encoding="utf-8") as f:
        return json.load(f)


def encode_image_base64(image_path: str) -> str:
    """Encode une image en base64 pour inclusion dans le prompt."""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def assemble_iron_prompt(thumbnail_path: str, new_title: str, new_niche: str,
                         contracts: dict, source_title: str = "") -> str:
    """
    Assemble le prompt complet pour l'IRON (Claude sandbox).
    Inclut : l'image en base64, la checklist visuelle, la niche, les règles.
    """
    # Encoder l'image
    img_b64 = encode_image_base64(thumbnail_path)
    img_size_kb = os.path.getsize(thumbnail_path) / 1024

    checklist_json = json.dumps(contracts["thumbnail_checklist"], ensure_ascii=False, indent=2)

    prompt = f"""# MISSION DE L'IRON — F04_HERALD

## CONTRAT
{contracts["iron_prompt"]}

## RÈGLES ANTI-BULLSHIT
{contracts["anti_bullshit"]}

## MÉMOIRE IMPÉRIALE — RÈGLES DES EXPERTS
{contracts["archivum_rules"]}

---

## CHECKLIST DU SQUELETTE VISUEL (thumbnail_skeleton_elements)
{checklist_json}

---

## SPECIMEN VISUEL À ANALYSER

**Image source :** {thumbnail_path} ({img_size_kb:.1f} KB)
**Vidéo source :** {source_title}
**Nouveau titre :** {new_title}
**Nouvelle niche :** {new_niche}

L'image source est encodée en base64 à la fin de ce prompt.
Analyse-la avec la checklist visuelle.

---

## INSTRUCTIONS POUR L'IRON

### Étape 1 — Analyse du Visual Skeleton
Analyse la thumbnail d'origine et extrais son squelette visuel :
- **Composition** : position des éléments (sujet, objet, texte)
- **Contraste_Couleurs** : palette dominante, contraste, lisibilité mobile
- **Emotion_Expression** : expression du visage, posture, intensité
- **Texte_Image** : mots affichés, police, couleur, encadré
- **Curiosity_Gap** : élément de mystère (objet flouté, flèche, zone illuminée)

### Étape 2 — Génération de l'image
Utilise l'outil image_generator pour générer une nouvelle miniature qui :
- Reproduit fidèlement la composition et l'ambiance de l'originale
- Adapte le contenu à la niche "{new_niche}"
- Respecte le format 16:9 (horizontal) ou 9:16 (vertical selon le format)
- A un contraste élevé pour la lisibilité mobile
- Ne contient AUCUN texte (le texte sera ajouté sur Canva)
- Sauvegarde l'image dans F04_HERALD/OUT/thumbnail.png

### Étape 3 — Prompt Gemini de backup
Rédige un prompt optimisé pour Gemini 3.1 Pro (en anglais) qui permettrait
de régénérer cette image si la qualité de l'image générée est insuffisante.
Le prompt doit décrire précisément la composition, les couleurs, l'ambiance,
le style, sans inclure de texte.

### Étape 4 — Instructions texte Canva
Donne les instructions exactes pour ajouter le texte sur la miniature :
- Les 3-4 mots à afficher (en français, impact maximum)
- La police recommandée
- La couleur du texte
- La position sur l'image
- L'encadré/ombre si nécessaire

---

## FORMAT DE SORTIE ATTENDU (JSON)

Retourne UNIQUEMENT un JSON valide avec cette structure exacte :

```json
{{
  "source_thumbnail": "{thumbnail_path}",
  "source_title": "{source_title}",
  "new_title": "{new_title}",
  "new_niche": "{new_niche}",

  "visual_skeleton": {{
    "composition": "...",
    "contrast_colors": "...",
    "emotion_expression": "...",
    "text_on_image": "...",
    "curiosity_gap": "..."
  }},

  "thumbnail_image": "thumbnail.png",
  "gemini_backup_prompt": "Prompt optimisé pour Gemini 3.1 Pro en anglais...",

  "thumbnail_text": "3-4 MOTS MAX",
  "canva_instructions": "Police: ..., Couleur: ..., Position: ..., Encadré: ...",

  "f04_meta": {{
    "analyzed_at": "{now_iso()}",
    "model_used": "claude-sandbox-vision",
    "image_generated": true,
    "rules_applied": ["règle 1", "règle 2"]
  }}
}}
```

Ne retourne RIEN d'autre que le JSON.

---

## IMAGE SOURCE EN BASE64

L'image de la thumbnail d'origine est ci-dessous (base64) :
data:image/jpeg;base64,{img_b64}
"""

    return prompt


def save_iron_prompt(prompt: str) -> str:
    """Sauvegarde le prompt assemblé dans F04_HERALD/OUT/iron_prompt.txt."""
    os.makedirs(_F04_OUT, exist_ok=True)
    path = os.path.join(_F04_OUT, "iron_prompt.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(prompt)
    return path


def validate_thumbnail_concept(concept_path: str = None) -> dict:
    """Valide le thumbnail_concept.json produit par l'IRON."""
    if concept_path is None:
        concept_path = os.path.join(_F04_OUT, "thumbnail_concept.json")

    if not os.path.exists(concept_path):
        return {"valid": False, "error": f"thumbnail_concept.json introuvable: {concept_path}"}

    try:
        with open(concept_path, "r", encoding="utf-8") as f:
            concept = json.load(f)
    except json.JSONDecodeError as e:
        return {"valid": False, "error": f"JSON invalide: {e}"}

    # Vérifier les champs obligatoires
    required = ["visual_skeleton", "thumbnail_text", "canva_instructions"]
    missing = [k for k in required if k not in concept]
    if missing:
        return {"valid": False, "error": f"Champs manquants: {missing}", "concept": concept}

    # Vérifier le visual skeleton
    vs = concept.get("visual_skeleton", {})
    vs_required = ["composition", "contrast_colors", "emotion_expression", "text_on_image", "curiosity_gap"]
    vs_missing = [k for k in vs_required if k not in vs]
    if vs_missing:
        return {"valid": False, "error": f"Visual skeleton incomplet: {vs_missing}", "concept": concept}

    # Vérifier l'image générée (optionnel mais recommandé)
    thumb_path = os.path.join(_F04_OUT, "thumbnail.png")
    has_image = os.path.exists(thumb_path)

    return {"valid": True, "error": None, "concept": concept, "has_image": has_image}


# ============================================================
# ANALYSE VISUELLE QUANTITATIVE (pixel-level)
# ============================================================

def extract_visual_metrics(image_path: str) -> dict:
    """
    Extrait les métriques visuelles quantitatives d'une image.
    Utilise PIL + numpy pour analyser pixel par pixel.
    """
    try:
        from PIL import Image
        import numpy as np
    except ImportError:
        return {"error": "PIL et numpy requis (pip install pillow numpy)"}

    img = Image.open(image_path)
    arr = np.array(img)
    gray = arr.mean(axis=2)

    # Saturation = max_rgb - min_rgb par pixel
    sat = arr.max(axis=2).astype(int) - arr.min(axis=2).astype(int)

    # Quadrants
    h, w = arr.shape[:2]
    h2, w2 = h // 2, w // 2
    quads = {
        "top_left":     arr[:h2, :w2].mean(),
        "top_right":    arr[:h2, w2:].mean(),
        "bottom_left":  arr[h2:, :w2].mean(),
        "bottom_right": arr[h2:, w2:].mean(),
    }

    # Couleurs dominantes (quantized par 32)
    pixels = arr.reshape(-1, 3)
    quantized = (pixels // 32 * 32)
    from collections import Counter
    top_colors = []
    for color, count in Counter(map(tuple, quantized)).most_common(5):
        r, g, b = color
        if r > 200 and g > 200 and b > 200:
            name = "WHITE/BRIGHT"
        elif r < 50 and g < 50 and b < 50:
            name = "BLACK/DARK"
        elif r > g and r > b:
            name = "RED/WARM"
        elif g > r and g > b:
            name = "GREEN"
        elif b > r and b > g:
            name = "BLUE"
        elif r > 150 and g > 120:
            name = "YELLOW/ORANGE"
        else:
            name = "MIXED"
        top_colors.append({
            "rgb": [int(r), int(g), int(b)],
            "pct": round(count / len(pixels) * 100, 1),
            "name": name
        })

    metrics = {
        "brightness": round(float(gray.mean()), 1),
        "dark_pct": round(float((gray < 50).mean() * 100), 1),
        "bright_pct": round(float((gray > 200).mean() * 100), 1),
        "saturation": round(float(sat.mean()), 1),
        "vibrant_pct": round(float((sat > 80).mean() * 100), 1),
        "quadrants": {k: round(float(v), 1) for k, v in quads.items()},
        "dominant_colors": top_colors,
        "image_size": [int(w), int(h)],
    }
    return metrics


def compare_visual_metrics(demon_metrics: dict, generated_metrics: dict) -> dict:
    """
    Compare les métriques de l'image générée vs le Démon.
    Retourne un rapport de match avec PASS/FAIL par métrique.
    """
    tolerances = {
        "brightness": 30,
        "dark_pct": 20,
        "bright_pct": 20,
        "saturation": 25,
        "vibrant_pct": 15,
    }

    results = []
    pass_count = 0

    for metric, tol in tolerances.items():
        d_val = demon_metrics.get(metric, 0)
        g_val = generated_metrics.get(metric, 0)
        diff = abs(g_val - d_val)
        passed = diff <= tol
        if passed:
            pass_count += 1
        results.append({
            "metric": metric,
            "demon": d_val,
            "generated": g_val,
            "diff": round(diff, 1),
            "tolerance": tol,
            "pass": passed
        })

    overall_pass = pass_count >= 4  # 4/5 = PASS

    return {
        "overall": "PASS" if overall_pass else "FAIL",
        "pass_count": f"{pass_count}/5",
        "metrics": results,
        "recommendation": "Image validée — check-in autorisé" if overall_pass
                         else "Image rejetée — re-générer avec prompt ajusté"
    }


def validate_visual_match(demon_image_path: str, generated_image_path: str) -> dict:
    """
    Validation post-génération : compare l'image générée au Démon.
    """
    if not os.path.exists(demon_image_path):
        return {"error": f"Démon image introuvable: {demon_image_path}"}
    if not os.path.exists(generated_image_path):
        return {"error": f"Image générée introuvable: {generated_image_path}"}

    demon_metrics = extract_visual_metrics(demon_image_path)
    if "error" in demon_metrics:
        return demon_metrics

    gen_metrics = extract_visual_metrics(generated_image_path)
    if "error" in gen_metrics:
        return gen_metrics

    comparison = compare_visual_metrics(demon_metrics, gen_metrics)

    return {
        "demon_metrics": demon_metrics,
        "generated_metrics": gen_metrics,
        "comparison": comparison
    }


def check_in_iw_custos(output_path: str):
    """Signale à IW_CUSTOS.py que F04 a terminé."""
    custos_path = os.path.join(_PROJECT_ROOT, "IW_CUSTOS.py")
    if os.path.exists(custos_path):
        import subprocess
        result = subprocess.run(
            [sys.executable, custos_path, "--mode", "check-in", "--frigate", "F04", "--output", output_path],
            capture_output=True, text=True, timeout=30
        )
        print(f"[F04] IW_CUSTOS: {result.stdout.strip()}")
        if result.stderr:
            print(f"[F04] IW_CUSTOS stderr: {result.stderr.strip()}")
    else:
        print(f"[F04] ⚠️ IW_CUSTOS.py non trouvé — check-in ignoré")


def cmd_prepare(args):
    """Phase 1 : télécharge la thumbnail + assemble le prompt pour l'IRON."""
    print("=" * 60)
    print("🚩 F04_HERALD — Le Porte-Étendard")
    print("=" * 60)

    # 1. Charger le brief (titre + niche)
    brief = load_brief(args.brief)
    new_title = args.title or brief.get("title", "")
    new_niche = args.niche or brief.get("niche", "")

    if not new_title or not new_niche:
        print("[F04] ❌ Titre et niche requis (via --title/--niche ou brief.json)")
        sys.exit(1)

    print(f"[F04] Nouveau titre: {new_title}")
    print(f"[F04] Nouvelle niche: {new_niche}")

    # 2. Télécharger la thumbnail
    thumbnail_url = args.thumbnail_url
    if not thumbnail_url:
        specimen = load_specimen(args.specimen)
        thumbnail_url = specimen.get("thumbnail")

    if not thumbnail_url:
        print("[F04] ❌ Aucune URL de thumbnail trouvée (via --thumbnail-url ou specimen.json)")
        sys.exit(1)

    print(f"\n[F04] Téléchargement de la thumbnail...")
    thumb_path = download_thumbnail(thumbnail_url)
    if not thumb_path:
        print("[F04] ❌ Échec du téléchargement")
        sys.exit(1)

    # 3. Charger les contrats + ARCHIVUM
    print("\n[F04] Chargement des contrats et de l'ARCHIVUM...")
    contracts = load_all()
    print(f"[F04] Thumbnail checklist: {len(contracts['thumbnail_checklist'])} éléments")
    print(f"[F04] Règles ARCHIVUM: {contracts['meta']['rules_count']} fichiers")

    # 4. Récupérer le titre source
    source_title = ""
    if os.path.exists(os.path.join(_F04_IN, "specimen.json")):
        specimen = load_specimen(args.specimen)
        source_title = specimen.get("title", "")

    # 5. Assembler le prompt
    print("\n[F04] Assemblage du prompt pour l'IRON...")
    prompt = assemble_iron_prompt(thumb_path, new_title, new_niche, contracts, source_title)
    prompt_path = save_iron_prompt(prompt)
    prompt_size = len(prompt.encode("utf-8")) / 1024
    print(f"[F04] Prompt sauvegardé: {prompt_path} ({prompt_size:.1f} KB)")

    # 6. Instructions pour l'IRON
    print(f"\n{'=' * 60}")
    print(f"🛠️  PROMPT PRÊT — EN ATTENTE DE L'IRON (Claude sandbox)")
    print(f"{'=' * 60}")
    print(f"\nLe prompt est dans: {prompt_path}")
    print(f"La thumbnail d'origine est dans: {thumb_path}")
    print(f"\nL'IRON (Claude) doit :")
    print(f"  1. Lire {prompt_path}")
    print(f"  2. Analyser la thumbnail (Visual Skeleton)")
    print(f"  3. Générer une nouvelle image (image_generator) → F04_HERALD/OUT/thumbnail.png")
    print(f"  4. Rédiger le prompt Gemini de backup")
    print(f"  5. Rédiger les instructions texte Canva")
    print(f"  6. Écrire thumbnail_concept.json dans F04_HERALD/OUT/")
    print(f"\nEnsuite, lancer :")
    print(f"  python herald.py --finalize")


def cmd_finalize(args):
    """Phase 3 : valide thumbnail_concept.json, compare visuel vs Démon, check-in."""
    print("=" * 60)
    print("🚩 F04_HERALD — FINALISATION")
    print("=" * 60)

    concept_path = args.concept if args.concept else os.path.join(_F04_OUT, "thumbnail_concept.json")

    print(f"\n[F04] Validation de {concept_path}...")
    result = validate_thumbnail_concept(concept_path)

    if not result["valid"]:
        print(f"[F04] ❌ VALIDATION ÉCHOUÉE: {result['error']}")
        sys.exit(1)

    concept = result["concept"]
    print(f"[F04] ✅ Concept valide !")
    print(f"[F04] Visual skeleton: {list(concept['visual_skeleton'].keys())}")
    print(f"[F04] Texte miniature: {concept['thumbnail_text']}")
    print(f"[F04] Image générée: {'✅ oui' if result['has_image'] else '⚠️ non'}")

    if concept.get("gemini_backup_prompt"):
        print(f"[F04] Prompt Gemini backup: disponible")

    # --- NOUVEAU : Validation visuelle post-génération ---
    demon_thumb_path = os.path.join(_F04_IN, "thumbnail.jpg")
    generated_thumb_path = os.path.join(_F04_OUT, "thumbnail.png")
    generated_jpg_path = os.path.join(_F04_OUT, "thumbnail.jpg")

    # Accepter .png ou .jpg
    gen_path = generated_thumb_path if os.path.exists(generated_thumb_path) else (
        generated_jpg_path if os.path.exists(generated_jpg_path) else None
    )

    if gen_path and os.path.exists(demon_thumb_path):
        print(f"\n[F04] Validation visuelle (comparaison Démon vs généré)...")
        visual_report = validate_visual_match(demon_thumb_path, gen_path)

        if "error" in visual_report:
            print(f"[F04] ⚠️ Validation visuelle ignorée: {visual_report['error']}")
        else:
            comp = visual_report["comparison"]
            print(f"\n{'Metric':<18} {'Démon':>8} {'Généré':>8} {'Diff':>8} {'Tol':>6} {'Pass?':>6}")
            print("-" * 56)
            for m in comp["metrics"]:
                status = "✅" if m["pass"] else "❌"
                print(f"{m['metric']:<18} {m['demon']:>8.0f} {m['generated']:>8.0f} {m['diff']:>8.0f} {m['tolerance']:>6} {status:>6}")
            print(f"\n[F04] Résultat: {comp['overall']} ({comp['pass_count']})")
            print(f"[F04] {comp['recommendation']}")

            # Sauvegarder le rapport de validation
            report_path = os.path.join(_F04_OUT, "visual_validation.json")
            with open(report_path, "w", encoding="utf-8") as f:
                json.dump(visual_report, f, ensure_ascii=False, indent=2)
            print(f"[F04] Rapport sauvegardé: {report_path}")

            if comp["overall"] == "FAIL":
                print(f"\n[F04] ❌ IMAGE REJETÉE — re-générer avec prompt ajusté")
                print(f"[F04] Voir le rapport: {report_path}")
                sys.exit(1)
    else:
        print(f"\n[F04] ⚠️ Validation visuelle ignorée (image Démon ou générée manquante)")

    # Check-in IW_CUSTOS
    if not args.no_checkin:
        check_in_iw_custos(concept_path)

    print(f"\n{'=' * 60}")
    print(f"🚩 F04_HERALD — MISSION ACCOMPLIE")
    print(f"{'=' * 60}")
    print(f"Concept: {concept_path}")
    if gen_path:
        print(f"Image: {gen_path}")
    print(f"Prochaine étape: Porte 4 (validation du Warsmith) → Artefact final")


def cmd_status(args):
    """Vérifie l'état de F04."""
    print("=" * 60)
    print("🚩 F04_HERALD — ÉTAT")
    print("=" * 60)

    specimen_path = os.path.join(_F04_IN, "specimen.json")
    brief_path = os.path.join(_F04_IN, "brief.json")
    thumb_path = os.path.join(_F04_IN, "thumbnail.jpg")
    prompt_path = os.path.join(_F04_OUT, "iron_prompt.txt")
    concept_path = os.path.join(_F04_OUT, "thumbnail_concept.json")
    image_path = os.path.join(_F04_OUT, "thumbnail.png")

    print(f"\n[IN]  specimen.json:    {'✅ présent' if os.path.exists(specimen_path) else '❌ absent'}")
    print(f"[IN]  brief.json:       {'✅ présent' if os.path.exists(brief_path) else '❌ absent'}")
    print(f"[IN]  thumbnail.jpg:    {'présente ✅' if os.path.exists(thumb_path) else 'absente ❌'}")
    print(f"[OUT] iron_prompt.txt:  {'prêt ✅' if os.path.exists(prompt_path) else 'absent ❌'}")
    print(f"[OUT] thumbnail_concept.json: {'prêt ✅' if os.path.exists(concept_path) else 'en attente de l IRON ❌'}")
    print(f"[OUT] thumbnail.png:    {'générée ✅' if os.path.exists(image_path) else 'en attente de l IRON ❌'}")

    if os.path.exists(prompt_path) and not os.path.exists(concept_path):
        print(f"\n→ L'IRON doit produire thumbnail_concept.json + thumbnail.png")
        print(f"  Lire: {prompt_path}")
        print(f"  Écrire: {concept_path} + {image_path}")
    elif os.path.exists(concept_path):
        print(f"\n→ Lancer: python herald.py --finalize")
    elif not os.path.exists(thumb_path):
        print(f"\n→ Placer specimen.json dans F04_HERALD/IN/ (pour l'URL de la thumbnail)")
    else:
        print(f"\n→ Lancer: python herald.py --prepare")


def cmd_validate(args):
    """Compare visuellement deux images (Démon vs généré)."""
    print("=" * 60)
    print("🚩 F04_HERALD — VALIDATION VISUELLE")
    print("=" * 60)

    report = validate_visual_match(args.demon, args.generated)

    if "error" in report:
        print(f"\n❌ {report['error']}")
        sys.exit(1)

    comp = report["comparison"]
    print(f"\n{'Metric':<18} {'Démon':>8} {'Généré':>8} {'Diff':>8} {'Tol':>6} {'Pass?':>6}")
    print("-" * 56)
    for m in comp["metrics"]:
        status = "✅" if m["pass"] else "❌"
        print(f"{m['metric']:<18} {m['demon']:>8.0f} {m['generated']:>8.0f} {m['diff']:>8.0f} {m['tolerance']:>6} {status:>6}")

    print(f"\nRésultat: {comp['overall']} ({comp['pass_count']})")
    print(f"{comp['recommendation']}")

    # Sauvegarder
    report_path = os.path.join(_F04_OUT, "visual_validation.json")
    os.makedirs(_F04_OUT, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\nRapport: {report_path}")


def cmd_analyze(args):
    """Extrait les métriques visuelles d'une seule image."""
    print("=" * 60)
    print("🚩 F04_HERALD — ANALYSE VISUELLE")
    print("=" * 60)

    metrics = extract_visual_metrics(args.image)

    if "error" in metrics:
        print(f"\n❌ {metrics['error']}")
        sys.exit(1)

    print(f"\nImage: {args.image}")
    print(f"Taille: {metrics['image_size']}")
    print(f"\n{'Metric':<18} {'Valeur':>10}")
    print("-" * 30)
    for key in ["brightness", "dark_pct", "bright_pct", "saturation", "vibrant_pct"]:
        print(f"{key:<18} {metrics[key]:>10.1f}")

    print(f"\nQuadrants (brightness):")
    for q, v in metrics["quadrants"].items():
        print(f"  {q:<15} {v:>8.1f}")

    print(f"\nCouleurs dominantes:")
    for c in metrics["dominant_colors"]:
        print(f"  RGB{c['rgb']} = {c['pct']:5.1f}% — {c['name']}")


def main():
    parser = argparse.ArgumentParser(description="F04_HERALD — Le Porte-Étendard")
    subparsers = parser.add_subparsers(dest="command", help="Phase d'exécution")

    # --prepare
    p_prepare = subparsers.add_parser("prepare", help="Phase 1 : télécharger thumbnail + assembler le prompt")
    p_prepare.add_argument("--specimen", default=None, help="Chemin vers specimen.json")
    p_prepare.add_argument("--brief", default=None, help="Chemin vers brief.json")
    p_prepare.add_argument("--thumbnail-url", default=None, help="URL de la thumbnail (override)")
    p_prepare.add_argument("--title", default=None, help="Nouveau titre (de F03)")
    p_prepare.add_argument("--niche", default=None, help="Nouvelle niche")
    p_prepare.set_defaults(func=cmd_prepare)

    # --finalize
    p_finalize = subparsers.add_parser("finalize", help="Phase 3 : valider thumbnail_concept.json + validation visuelle → check-in")
    p_finalize.add_argument("--concept", default=None, help="Chemin vers thumbnail_concept.json")
    p_finalize.add_argument("--no-checkin", action="store_true", help="Ne pas signaler à IW_CUSTOS.py")
    p_finalize.set_defaults(func=cmd_finalize)

    # --validate (standalone : compare deux images sans refaire le flux)
    p_validate = subparsers.add_parser("validate", help="Comparer visuellement deux images (Démon vs généré)")
    p_validate.add_argument("--demon", required=True, help="Chemin vers l'image du Démon")
    p_validate.add_argument("--generated", required=True, help="Chemin vers l'image générée")
    p_validate.set_defaults(func=cmd_validate)

    # --analyze (extrait les métriques d'une seule image)
    p_analyze = subparsers.add_parser("analyze", help="Extraire les métriques visuelles d'une image")
    p_analyze.add_argument("--image", required=True, help="Chemin vers l'image à analyser")
    p_analyze.set_defaults(func=cmd_analyze)

    # --status
    p_status = subparsers.add_parser("status", help="Vérifier l'état de F04")
    p_status.set_defaults(func=cmd_status)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
