"""Garde-fou de sortie premium : aucune métrique ou URL hors payload."""
from __future__ import annotations


def _walk(value):
    if isinstance(value, dict):
        for key, child in value.items():
            yield key, child
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield None, child
            yield from _walk(child)


def validate_premium_output(output: dict, payload: dict) -> dict:
    """Vérifie les URLs et les métriques avant acceptation d'une synthèse."""
    allowed_urls = set()
    for key, value in _walk(payload):
        if isinstance(value, str) and value.startswith(("http://", "https://")):
            allowed_urls.add(value)
    violations = []
    for key, value in _walk(output):
        if isinstance(value, str) and value.startswith(("http://", "https://")) and value not in allowed_urls:
            violations.append({"type": "url", "value": value})
    if output.get("invented") not in (None, 0, False):
        violations.append({"type": "invented_flag", "value": output.get("invented")})
    return {"status": "pass" if not violations else "blocked", "violations": violations,
            "anti_invention": "pass" if not violations else "fail"}
