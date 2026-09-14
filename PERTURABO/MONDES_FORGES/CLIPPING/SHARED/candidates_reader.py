#!/usr/bin/env python3
"""
candidates_reader.py — Lecteur tolérant du schéma canonique d'entrée PUR.

Doctrine (Note 20) : un seul schéma d'entrée du tronc.

    {"candidates": [ {candidate_id, start_sec, end_sec, duration_sec,
                      signal_type, signal_intensity, signal_start, top_words} ]}

Les lecteurs acceptent aussi :
  - la clé F00B detect ``candidats``
  - un manifeste ``perturabo.voxc.v1`` (``viral_segments``)
  - une liste brute

Forme non canonique = WARNING explicite, jamais de silence.
Document vide = erreur claire (exit), jamais 0 pack muet.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from typing import Any


VOXC_SCHEMA = "perturabo.voxc.v1"
SIGNAL_PLATFORM_HEAT = "platform_heat"

CANONICAL_FIELDS = (
    "candidate_id",
    "start_sec",
    "end_sec",
    "duration_sec",
    "signal_type",
    "signal_intensity",
    "signal_start",
    "top_words",
)


class CandidatesReadError(ValueError):
    """Aucune matière exploitable — le tronc refuse de continuer en silence."""


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _normalize_candidate(raw: dict, *, fallback_id: str, signal_start: str = "") -> dict:
    start = _as_float(raw.get("start_sec"))
    end = _as_float(raw.get("end_sec"))
    duration = raw.get("duration_sec")
    duration_sec = _as_float(duration) if duration is not None else round(max(0.0, end - start), 3)
    return {
        "candidate_id": raw.get("candidate_id") or fallback_id,
        "start_sec": start,
        "end_sec": end,
        "duration_sec": duration_sec,
        "signal_type": raw.get("signal_type") or SIGNAL_PLATFORM_HEAT,
        "signal_intensity": _as_float(raw.get("signal_intensity"), 0.0),
        "signal_start": raw.get("signal_start") or signal_start,
        "top_words": raw.get("top_words") or "",
    }


def viral_segments_to_candidates(
    segments: list[dict],
    *,
    generated_at: str | None = None,
    source: str = "",
    engine: str = "f00c_vox",
    top: int | None = None,
) -> dict:
    """Mappe ``viral_segments`` F00C vers le schéma canonique ``candidates``."""
    ranked = sorted(
        list(segments or []),
        key=lambda row: _as_float(row.get("attention_norm", row.get("attention", 0))),
        reverse=True,
    )
    if top is not None and top > 0:
        ranked = ranked[:top]
    ranked.sort(key=lambda row: _as_float(row.get("start_sec")))
    stamp = generated_at or _now_iso()
    candidates = []
    for index, seg in enumerate(ranked):
        rank = seg.get("rank") or (index + 1)
        start = _as_float(seg.get("start_sec"))
        end = _as_float(seg.get("end_sec"))
        candidates.append({
            "candidate_id": "voxc-{}".format(rank),
            "start_sec": start,
            "end_sec": end,
            "duration_sec": round(max(0.0, end - start), 3),
            "signal_type": SIGNAL_PLATFORM_HEAT,
            "signal_intensity": _as_float(seg.get("attention_norm")),
            "signal_start": stamp,
            "top_words": "",
        })
    return {
        "generated_at": stamp,
        "source": source,
        "engine": engine,
        "total_candidates_raw": len(segments or []),
        "total_accepted": len(candidates),
        "candidates": candidates,
    }


def detect_form(raw: Any) -> str:
    """Identifie la forme d'entrée : canonical | f00b_detect | voxc_manifest | list | unknown."""
    if isinstance(raw, list):
        return "list"
    if not isinstance(raw, dict):
        return "unknown"
    if isinstance(raw.get("candidates"), list):
        return "canonical"
    if isinstance(raw.get("candidats"), list):
        return "f00b_detect"
    schema = str(raw.get("schema_version") or "")
    if schema == VOXC_SCHEMA or isinstance(raw.get("viral_segments"), list):
        return "voxc_manifest"
    return "unknown"


def extract_candidates(raw: Any, *, source_label: str = "") -> tuple[str, list[dict], dict]:
    """Retourne (forme, candidates_normalisés, document_enveloppe)."""
    form = detect_form(raw)
    stamp = _now_iso()
    if form == "canonical":
        items = raw.get("candidates") or []
        candidates = [
            _normalize_candidate(item if isinstance(item, dict) else {}, fallback_id="cand-{}".format(i + 1),
                                 signal_start=stamp)
            for i, item in enumerate(items)
        ]
        envelope = dict(raw)
        envelope["candidates"] = candidates
        return form, candidates, envelope
    if form == "f00b_detect":
        items = raw.get("candidats") or []
        candidates = [
            _normalize_candidate(item if isinstance(item, dict) else {}, fallback_id="cand-{}".format(i + 1),
                                 signal_start=stamp)
            for i, item in enumerate(items)
        ]
        envelope = dict(raw)
        envelope["candidates"] = candidates
        return form, candidates, envelope
    if form == "voxc_manifest":
        source = ""
        if isinstance(raw.get("source"), dict):
            source = raw["source"].get("reference") or raw["source"].get("id") or ""
        elif isinstance(raw.get("source"), str):
            source = raw["source"]
        doc = viral_segments_to_candidates(
            raw.get("viral_segments") or [],
            generated_at=raw.get("generated_at") or stamp,
            source=source or source_label,
            engine="f00c_vox",
        )
        envelope = dict(raw)
        envelope["candidates"] = doc["candidates"]
        envelope.setdefault("engine", "f00c_vox")
        return form, doc["candidates"], envelope
    if form == "list":
        candidates = [
            _normalize_candidate(item if isinstance(item, dict) else {}, fallback_id="cand-{}".format(i + 1),
                                 signal_start=stamp)
            for i, item in enumerate(raw)
        ]
        return form, candidates, {"candidates": candidates, "generated_at": stamp}
    raise CandidatesReadError(
        "forme d'entrée inconnue{} — attendu 'candidates', 'candidats' ou manifeste {}.".format(
            " ({})".format(source_label) if source_label else "",
            VOXC_SCHEMA,
        )
    )


def warn_non_canonical(form: str, source_label: str = "") -> None:
    if form == "canonical":
        return
    where = source_label or "entrée"
    print(
        "[CANDIDATES] WARNING: forme '{}' détectée dans {} — normalisée vers la clé "
        "'candidates'. Tout nouveau capteur DOIT émettre le schéma canonique "
        "{{\"candidates\": [...]}}.".format(form, where),
        file=sys.stderr,
    )


def load_candidates_document(path: str, *, allow_empty: bool = False) -> dict:
    """Charge un JSON et le normalise. Raise si vide (sauf allow_empty)."""
    with open(path, "r", encoding="utf-8") as handle:
        raw = json.load(handle)
    form, candidates, envelope = extract_candidates(raw, source_label=path)
    warn_non_canonical(form, path)
    if not candidates and not allow_empty:
        raise CandidatesReadError(
            "0 candidat dans {} (forme {}). Pont vide — refus de continuer en silence. "
            "Vérifier le capteur (F00B auto_detect / F00C --to-candidats avec heatmap).".format(
                path, form
            )
        )
    envelope["candidates"] = candidates
    envelope["_input_form"] = form
    return envelope
