"""Directeur de prospection : planifie des interrogations réelles avant classement.

Le mode premium est facultatif. Ce module sépare toujours les questions proposées,
les réponses brutes des capteurs et l'interprétation premium. Aucune valeur n'est
créée par le fallback déterministe.
"""
from __future__ import annotations

import json
import os
import sys
import uuid
from datetime import datetime, timezone

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
F04_LIBS = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(SCRIPT_DIR))), "F04_COPYWRITER", "CODEBASE", "libs")
if F04_LIBS not in sys.path:
    sys.path.insert(0, F04_LIBS)

try:
    from premium_client import PremiumClient, PremiumClientError
except ImportError:  # pragma: no cover - fallback when optional dependency unavailable
    PremiumClient = None
    PremiumClientError = Exception

MAX_TURNS = 3
MAX_QUESTIONS_PER_TURN = 10
MAX_QUERIES_PER_QUESTION = 6


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_deterministic_questions(market: str, platform: str, horizon: str) -> list[dict]:
    """Questions sûres pour le mode sans premium ; elles ne sont pas des preuves."""
    return [
        {"question_id": "Q-001", "objective": "market_vocabulary", "question": "Quels termes et sous-thèmes sont réellement utilisés par ce marché ?", "queries": [market], "sources_allowed": ["youtube", "suggest", "trends"], "priority": "high", "expected_evidence": ["title", "url", "date", "views"], "status": "proposed"},
        {"question_id": "Q-002", "objective": "youtube_proof", "question": "Quels sous-thèmes possèdent une preuve récente sur la plateforme cible ?", "queries": [f"{market} Shorts"], "sources_allowed": ["youtube"], "priority": "high", "expected_evidence": ["title", "url", "published_at", "view_count", "channel"], "status": "proposed"},
        {"question_id": "Q-003", "objective": "demon_map", "question": "Quels créateurs, formats et hooks dominent déjà ce territoire ?", "queries": [f"{market} creators", f"{market} Shorts"], "sources_allowed": ["youtube", "reddit"], "priority": "high", "expected_evidence": ["channel", "title", "url", "view_count"], "status": "proposed"},
        {"question_id": "Q-004", "objective": "blue_ocean", "question": "Quels sous-territoires ont une demande observable mais une pression concurrentielle moindre ?", "queries": [f"{market} niche", f"{market} theory"], "sources_allowed": ["youtube", "reddit", "trends", "suggest"], "priority": "medium", "expected_evidence": ["url", "date", "demand", "competition"], "status": "proposed"},
        {"question_id": "Q-005", "objective": "deduplication", "question": "Quels candidats sont lexicalement, sémantiquement ou créativement redondants ?", "queries": [market], "sources_allowed": ["youtube", "suggest", "reddit"], "priority": "medium", "expected_evidence": ["title", "url", "cluster"], "status": "proposed"},
    ]


def validate_question_plan(plan: dict) -> dict:
    questions = plan.get("questions", []) if isinstance(plan, dict) else []
    errors = []
    for q in questions:
        if not q.get("question_id") or not q.get("objective") or not q.get("queries"):
            errors.append({"type": "invalid_question", "question": q})
        if len(q.get("queries", [])) > MAX_QUERIES_PER_QUESTION:
            errors.append({"type": "query_limit", "question_id": q.get("question_id")})
        if not set(q.get("sources_allowed", [])).issubset({"youtube", "reddit", "trends", "suggest", "rss"}):
            errors.append({"type": "source_not_allowed", "question_id": q.get("question_id")})
    if len(questions) > MAX_QUESTIONS_PER_TURN:
        errors.append({"type": "question_limit"})
    return {"status": "pass" if not errors else "blocked", "errors": errors, "questions": questions}


def build_session(market: str, platform: str, horizon: str, premium_requested: bool = False) -> dict:
    questions = build_deterministic_questions(market, platform, horizon)
    return {
        "session_id": "PROSPECT-" + uuid.uuid4().hex[:10],
        "created_at": _now(),
        "market_input": {"market": market, "platform": platform, "horizon": horizon},
        "director": {"role": "prospection_director", "premium_requested": premium_requested, "premium_status": "not_called"},
        "turns": [{"turn": 1, "questions": questions, "responses": [], "status": "proposed"}],
        "limits": {"max_turns": MAX_TURNS, "max_questions_per_turn": MAX_QUESTIONS_PER_TURN, "max_queries_per_question": MAX_QUERIES_PER_QUESTION},
        "validation": {"facts_vs_interpretation": "separated", "invented": 0, "state": "warsmith_review"},
    }


def premium_plan(session: dict) -> dict:
    """Demande au premium un plan de questions ; ne collecte aucune donnée."""
    if PremiumClient is None:
        return {"status": "unavailable", "error": "premium_client indisponible", "plan": None}
    forge_root = os.path.dirname(os.path.dirname(os.path.dirname(SCRIPT_DIR)))
    try:
        client = PremiumClient(forge_root)
        client.require_config()
        system = "Tu es le Directeur de prospection de PERTURABO. Propose uniquement un JSON de questions et requêtes. N'invente aucune métrique, URL ou résultat. Les sources autorisées sont youtube, reddit, trends, suggest, rss. Maximum 10 questions et 6 requêtes par question."
        user = json.dumps({"market": session["market_input"], "existing_session": session}, ensure_ascii=False)[:50000]
        raw = client.chat(system, user)
        parsed = json.loads(client.extract_json(raw))
        checked = validate_question_plan(parsed)
        if checked["status"] != "pass":
            return {"status": "blocked", "error": "question plan invalide", "plan": checked}
        session["director"]["premium_status"] = "planned"
        session["turns"][0]["questions"] = checked["questions"]
        return {"status": "ok", "error": None, "plan": session}
    except Exception as exc:
        return {"status": "error", "error": str(exc), "plan": None}
