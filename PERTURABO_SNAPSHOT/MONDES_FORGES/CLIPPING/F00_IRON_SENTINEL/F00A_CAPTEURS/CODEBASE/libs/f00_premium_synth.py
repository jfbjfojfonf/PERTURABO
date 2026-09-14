"""
premium_synth.py — Synthèse des 5 sujets viraux via GLM 5.2 (F00_CAPTEURS)
==========================================================================
RÔLE : GLM 5.2 ne FAIT PAS la matière — il SYNTHÉTISE. Toutes les stats
viennent des capteurs (rss / trends / youtube / suggestions). On injecte
les observations brutes dans le prompt et GLM produit 5 sujets 10/10.

DOGME (evidence over guess) :
  - GLM n'invente JAMAIS une vue, une recherche, une tendance, une source.
  - Toute métrique affichée doit exister dans le payload capteur.
  - Si un signal manque, le sujet doit le dire ("signal indisponible").

SORTIE : dict prêt à écrire dans OUT/subjects_proposal.json
  [ {subject, notes_fr, subject_en, signal, score, metrics, sources,
     angle_propose, sous_mode, clip_background_candidates, checklists} x5 ]
"""

import json
import os
import sys

# Import du PremiumClient réutilisé depuis F04_COPYWRITER
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_F04_LIBS = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(_SCRIPT_DIR))),
    "F04_COPYWRITER", "CODEBASE", "libs")
if _F04_LIBS not in sys.path:
    sys.path.insert(0, _F04_LIBS)
from premium_client import PremiumClient, PremiumClientError  # noqa: E402

# forge_root = MONDES_FORGES/CLIPPING
# libs/ -> CODEBASE -> CAPTEURS -> CLIPPING
_FORGE_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(_SCRIPT_DIR)))

MODEL_NAME = "z-ai/glm-5.2"

SYSTEM_PROMPT = """\
Tu es F00_CAPTEURS, le capteur de sujets viraux de PERTURABO/CLIPPING.
Ton rôle : TRANSFORMER des observations réelles en 5 sujets viraux notés 10/10.

DOGME ABSOLU — evidence over guess :
- TU N'INVENTES JAMAIS une métrique. Chaque vue, recherche, tendance, source
  que tu cites doit exister EXACTEMENT dans le payload capteur fourni.
- Si une métrique manque pour un sujet, tu écris "signal indisponible".
- Les sources doivent être les URLs réelles du payload.
- Interdiction de citer une tendance qui n'apparaît pas dans les données.

RÈGLES DE FORME :
- Réponds UNIQUEMENT en JSON valide, sans texte autour, sans markdown.
- Schéma exact (une liste de 5 objets) :
  {"subjects": [ {
    "subject_en": "<titre sujet en anglais, format clip viral, max 8 mots>",
    "notes_fr": "<notes en français : contexte, angle, pourquoi ça marche>",
    "signal": "<quels signaux appuient ce sujet>",
    "score_10": <nombre entier 1..10>,
    "score_rationale_fr": "<pourquoi ce score, en français>",
    "metrics": {
      "top_video_views": <int|null>,
      "yt_search_views": <int|null>,
      "trend_growth_7d": <float|null>,
      "trending_rss_traffic": <int|null>,
      "demand_score": <int|null>,
      "freshness_hours": <float|null>,
      "coverage_media_count": <int|null>,
      "signal_missing": ["<signaux absents>"]
    },
    "sources": ["<url réelle du payload>", "..."],
    "angle_propose_fr": "<l'angle 90s proposé>",
    "sous_mode": "informatif"|"humour",
    "clip_background_candidates": [
      {"desc_fr": "<description du moment/clip>", "source_hint": "<url ou chaîne>"}
    ],
    "checklist_viabilite_ok": <bool>,
    "checklist_viralite_ok": <bool>,
    "viral_checks": {"accroche_3s": <bool>, "emotion_forte": <bool>,
                     "personne_identifiable": <bool>,
                     "declencheur_conversationnel": <bool>,
                     "micro_sujet": <bool>, "visuel_fort": <bool>,
                     "boucle_de_clic": <bool>, "reference_culturelle": <bool>,
                     "partageable": <bool>, "pas_de_barriere": <bool>}
  } ]}
- Au moins 2 sujets en sous_mode "humour" si le mode demandé est "humour",
  sinon au moins 1 sujet humour parmi les 5 (le Warsmith décide ensuite).
"""


def _build_user_prompt(niche: str | None, hot: bool, mode: str,
                       freshness: str, payload: dict) -> str:
    """Compile le payload capteur en texte structuré pour GLM."""
    parts = []
    parts.append(f"RÉGLAGE : niche={niche or 'aucune (actu brûlante)'} "
                 f"| mode={mode} | fraîcheur={freshness} | "
                 f"hot_mode={hot}")
    parts.append("=== RÉSUMÉ DES OBSERVATIONS RÉELLES (payload capteurs) ===")
    parts.append(json.dumps(payload, ensure_ascii=False, indent=1,
                            default=str)[:60000])
    baseline = payload.get("baseline")
    if baseline and baseline.get("scans_count", 0) > 0:
        parts.append("=== BASELINE HISTORIQUE (scans passés de F00) ===")
        parts.append(
            "Ces chiffres indiquent ce qui est NORMAL dans nos scans récents. "
            "Sers-t-en pour calibrer tes scores : un sujet au-dessus de la "
            "médiane d'une métrique mérite un score plus haut, en-dessous "
            "plus bas. N'invente JAMAIS une valeur : compare aux observations "
            "du payload actuel.")
        parts.append(json.dumps(baseline, ensure_ascii=False, indent=1))
    return "\n".join(parts)


def synthesize(niche: str | None, hot: bool, mode: str, freshness: str,
               payload: dict) -> dict:
    """Appelle GLM 5.2 et parse les 5 sujets. Retourne
    {"status","subjects","error","raw"}."""
    client = PremiumClient(_FORGE_ROOT)
    try:
        client.require_config()
    except PremiumClientError as e:
        return {"status": "error", "error": str(e), "subjects": [], "raw": ""}

    # Vérification explicite du modèle premium configuré
    model_id = client.config.get("model_id")
    if model_id and MODEL_NAME not in model_id:
        return {"status": "error",
                "error": (f"Modèle configuré ({model_id}) != attendu ({MODEL_NAME}) "
                          f"— vérifier CONTRACTS/copywriter_secrets.json"),
                "subjects": [], "raw": ""}

    user_prompt = _build_user_prompt(niche, hot, mode, freshness, payload)
    try:
        raw = client.chat(SYSTEM_PROMPT, user_prompt)
    except PremiumClientError as e:
        return {"status": "error", "error": str(e), "subjects": [], "raw": ""}

    data = client.extract_json(raw)
    try:
        parsed = json.loads(data)
    except json.JSONDecodeError as e:
        return {"status": "error",
                "error": f"JSON GLM invalide: {e}",
                "subjects": [], "raw": raw}

    subjects = parsed.get("subjects", [])
    if not isinstance(subjects, list) or len(subjects) != 5:
        return {"status": "error",
                "error": f"GLM n'a pas renvoyé 5 sujets ({len(subjects)})",
                "subjects": subjects if isinstance(subjects, list) else [],
                "raw": raw}

    return {"status": "ok", "subjects": subjects, "error": None, "raw": raw}
