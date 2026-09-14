"""
virality_scorer.py — Score de viralité + checklists (F00_CAPTEURS)
==================================================================
CROISEMENT des 4 signaux captés (evidence over guess, jamais d'invention) :
    vue     (YouTube)  30%
    tendance (Trends)  25%
    fraîcheur (RSS)    20%
    demande (Suggest)  15%
    couverture (RSS)   10%

Valeurs normalisées 0..1 par signal, pondérées, -> score 0..100.
Quand un signal est absent (capteur KO), la pondération est re-pondérée
sur les signaux disponibles (pas de pénalité, mais on le signale).

CHECKLISTS :
  - la checklist "viabilité" (8 points) : la matière peut-elle devenir un
    sujet CLIPPING conforme aux contrats ?
  - la checklist "viralité" (10 points) : le sujet a-t-il les déclencheurs
    de la courbe de viralité (accroche 3s, émotion, saillance, boucle) ?
"""

# Points de la checklist viabilité — requis (False -> refuser le sujet)
VIABILITY_CHECKS = [
    ("Fraîcheur", "daté < 5h (brûlant) ou < 24h (frais) et vérifiable"),
    ("Sources", "au moins 1 source vérifiable, non-suite de rumeur"),
    ("Saillance", "le sujet est identifiable en 1 phrase par un non-initié"),
    ("Conflit/émotion", "contient un élément de tension ou d'émotion"),
    ("Personnage", "au moins un protagoniste reconnaissable (personne/marque)"),
    ("Valeur", "apporte info OU humour (fits sous-mode informatif/humour)"),
    ("Conformité", "respecte les contrats CLIPPING (pas de politique, sujet illégal, harcèlement)"),
    ("Aucune auto-promo", "ne sert pas une marque/un produit commandité"),
]

# Points de la checklist viralité — requis pour score >= 70
VIRALITY_CHECKS = [
    ("Accroche 3s", "un hook (titre + première image) qui stoppe le scroll"),
    ("Émotion forte", "surprise, rire, admiration, indignation (ou combinaison)"),
    ("Personne identifiable", "le public peut mettre un visage sur le sujet"),
    ("Déclencheur conversationnel", "les gens en parlent (commentaires natifs)"),
    ("Micro-sujet", "une piste de 90 secondes max, pas un sujet de fond"),
    ("Visuel fort", "un moment/image/clip qui se suffit à lui-même"),
    ("Boucle de clic", "l'utilisateur veut savoir la suite (question ouverte)"),
    ("Référence culturelle", "le public de la niche reconnaît le contexte"),
    ("Partageable", "on a envie de le montrer à un ami en 5 secondes"),
    ("Pas de barrière", "pas besoin d'explications pour comprendre"),
]


def _renorm(weights: dict[str, float], available: list[str]) -> dict[str, float]:
    """Re-pondère sur les signaux disponibles."""
    total = sum(w for k, w in weights.items() if k in available)
    if total <= 0:
        return {}
    return {k: (w / total) for k, w in weights.items() if k in available}


BASE_WEIGHTS = {
    "vues_youtube": 0.30,
    "tendance": 0.25,
    "fraicheur": 0.20,
    "demande": 0.15,
    "couverture": 0.10,
}


def normalize_metrics(metrics: dict, window_hours: int = 5) -> dict:
    """Transforme les métriques brutes d'un sujet en signaux normalisés 0..1.

    La normalisation est déterministe (jamais d'avis) :
      vues_youtube : échelle log — 0 vue -> 0, 1M vues -> 1.0
      tendance     : growth 7j — 1.0 -> 0.17, 2.0 -> 1.0
      fraicheur    : 1 - (heures / fenêtre)
      demande      : demand_score / 100
      couverture   : domaines distincts / 5 (plafonné à 1)
    """
    sig = {}
    views = metrics.get("top_video_views")
    if views:
        import math
        sig["vues_youtube"] = min(1.0, (math.log10(views) / 6.0)) if views else 0.0
    growth = metrics.get("trend_growth_7d")
    if growth:
        sig["tendance"] = min(1.0, max(0.0, (float(growth) - 0.8) / 1.2))
    hours = metrics.get("freshness_hours")
    if hours is not None:
        sig["fraicheur"] = max(0.0, min(1.0, 1.0 - (float(hours) / window_hours)))
    demand = metrics.get("demand_score")
    if demand:
        sig["demande"] = float(demand) / 100.0
    coverage = metrics.get("coverage_media_count")
    if coverage:
        sig["couverture"] = min(1.0, float(coverage) / 5.0)
    return sig


def score_subject_from_metrics(metrics: dict, window_hours: int = 5) -> dict:
    """Score mécanique complet (0-100) directement depuis les métriques brutes
    d'un sujet : normalisation déterministe + pondération 5 signaux.
    Retourne {score, detail, missing, note}."""
    sig = normalize_metrics(metrics, window_hours=window_hours)
    return score_subject(sig)


def score_subject(signals: dict) -> dict:
    """Signaux normalisés 0..1 par clé. Retourne score + détail.

    Exemple de signaux :
      {"vues_youtube": 0.8, "tendance": 0.6, "fraicheur": 0.9,
       "demande": 0.7, "couverture": 0.5}
    """
    available = [k for k, v in signals.items() if v is not None and v > 0]
    weights = _renorm(BASE_WEIGHTS, available)
    if not weights:
        return {"score": 0, "detail": {}, "missing": list(signals.keys()),
                "note": "aucun signal exploitable"}
    detail = {}
    total = 0.0
    for k, w in weights.items():
        v = max(0.0, min(1.0, float(signals.get(k, 0.0) or 0.0)))
        contrib = v * w
        detail[k] = {"value": round(v, 2), "weight": round(w, 2),
                     "contribution": round(contrib, 3)}
        total += contrib
    score = round(min(100.0, total * 100.0), 1)
    return {
        "score": score,
        "detail": detail,
        "missing": [k for k in BASE_WEIGHTS if k not in available],
        "note": None,
    }


def run_viability_checklist(subject_meta: dict) -> dict:
    """Valide la matière contre les 8 points de viabilité.

    subject_meta attend : {freshness_hours, source_url, summary,
    angle, protagonist, value, contract_ok, sponsored_ok}.
    Retourne {passed: bool, checks: [{label, ok, reason}]}.
    """
    checks = []
    ok = True
    for label, desc in VIABILITY_CHECKS:
        passed, reason = _check_viability(label, subject_meta)
        if not passed:
            ok = False
        checks.append({"label": label, "ok": passed, "reason": reason})
    return {"passed": ok, "checks": checks}


def _check_viability(label: str, m: dict) -> tuple[bool, str]:
    if label == "Fraîcheur":
        max_h = 5 if m.get("freshness") == "brulant" else 24
        h = m.get("freshness_hours")
        if h is None:
            return False, "âge inconnu"
        return (h <= max_h), f"{h}h (max {max_h}h)"
    if label == "Sources":
        if not m.get("source_url"):
            return False, "aucune source"
        return True, m["source_url"]
    if label == "Saillance":
        return bool(m.get("summary") and len(m["summary"]) >= 20), \
            "résumé présent" if m.get("summary") else "résumé manquant"
    if label == "Conflit/émotion":
        return bool(m.get("angle")), f"angle: {m.get('angle')}"
    if label == "Personnage":
        return bool(m.get("protagonist")), f"protagoniste: {m.get('protagonist')}"
    if label == "Valeur":
        return m.get("value") in ("informatif", "humour"), \
            f"valeur: {m.get('value')}"
    if label == "Conformité":
        return bool(m.get("contract_ok")), "conforme aux contrats" \
            if m.get("contract_ok") else "conflit contrat"
    if label == "Aucune auto-promo":
        return bool(m.get("sponsored_ok", True)), \
            "pas d'auto-promo" if m.get("sponsored_ok", True) else "commandité"
    return True, ""


def run_virality_checklist(subject_meta: dict) -> dict:
    """Note le sujet sur les 10 déclencheurs de viralité."""
    checks = []
    for label, _desc in VIRALITY_CHECKS:
        passed = _check_virality(label, subject_meta)
        checks.append({"label": label, "ok": passed})
    score_10 = sum(1 for c in checks if c["ok"])
    return {"score_10": score_10, "passed": score_10 >= 7, "checks": checks}


def _check_virality(label: str, m: dict) -> bool:
    return bool(m.get(f"viral_{_slug(label)}", False))


def _slug(label: str) -> str:
    return label.lower().replace(" ", "_").replace("3s", "3")
