#!/usr/bin/env python3
"""F00 STAND UP — extraction déterministe de sujets depuis un transcript.

Le script ne copie pas le transcript dans des tweets. Il extrait des observations,
propose des mécanismes comiques et produit un rapport traçable que le Champion
valide avant qu’un sujet ne soit transmis à F01.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

CONTRAST = ("mais", "pourtant", "sauf", "alors que", "cependant", "en fait", "jusqu'à", "jusqu’au")
COMEDY = ("jamais", "toujours", "personne", "tout le monde", "évidemment", "vraiment", "pourquoi", "comment")


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("\r", "").strip())


def split_units(text: str) -> list[str]:
    blocks = [clean(x) for x in re.split(r"\n{2,}|(?<=[.!?])\s+", text) if clean(x)]
    return [x for x in blocks if 8 <= len(x) <= 420]


def mechanism(unit: str) -> str:
    low = unit.lower()
    if "?" in unit or any(w in low for w in ("pourquoi", "comment")):
        return "question / renversement"
    if any(w in low for w in CONTRAST):
        return "contraste / contradiction"
    if any(w in low for w in COMEDY):
        return "exagération / observation"
    if any(w in low for w in ("je ", "moi ", "mon ", "ma ")):
        return "autodérision / expérience personnelle"
    return "observation du quotidien"


def score(unit: str) -> int:
    low = unit.lower()
    value = 35
    if 35 <= len(unit) <= 180:
        value += 18
    elif len(unit) <= 260:
        value += 8
    if any(w in low for w in CONTRAST):
        value += 14
    if "?" in unit:
        value += 10
    if any(w in low for w in COMEDY):
        value += 8
    if any(w in low for w in ("je ", "moi ", "nous ")):
        value += 6
    return min(99, value)


def subject_id(index: int, unit: str) -> str:
    digest = hashlib.sha1(unit.encode("utf-8")).hexdigest()[:8]
    return f"standup-{index:03d}-{digest}"


def build_report(transcript: str, title: str, source: str) -> dict[str, Any]:
    units = split_units(transcript)
    ranked = sorted(enumerate(units), key=lambda item: score(item[1]), reverse=True)[:7]
    subjects = []
    for rank, (original_index, unit) in enumerate(ranked, start=1):
        s = score(unit)
        subjects.append({
            "rank": rank,
            "subject_id": subject_id(rank, unit),
            "title": clean(unit)[:110],
            "core_observation": unit,
            "comedy_mechanism": mechanism(unit),
            "transcript_unit_index": original_index,
            "transcript_excerpt": unit,
            "originality_check": "human_review_required",
            "virality_score": s,
            "reusability_score": min(99, s + (12 if mechanism(unit) != "observation du quotidien" else 5)),
            "trend_context": [],
            "research_status": "pending_external_context_check",
            "recommended_variants": 7,
            "ready_for_f01": False,
            "champion_decision": "pending"
        })
    return {
        "mode": "stand_up",
        "stage": "F00",
        "title": title,
        "source": source or "champion_transcript",
        "transcript_sha256": hashlib.sha256(transcript.encode("utf-8")).hexdigest(),
        "transcript_units": len(units),
        "subjects_limit": 7,
        "subjects": subjects,
        "validation": {
            "viral_guarantee": False,
            "originality_requires_review": True,
            "champion_selection_required": True,
            "next_frigate": "F01 after subject selection"
        }
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--transcript", required=True, help="Fichier texte fourni par le Champion")
    parser.add_argument("--output", required=True, help="Rapport JSON F00")
    parser.add_argument("--summary", required=True, help="Résumé Markdown F00")
    parser.add_argument("--title", default="New Stand Up Siege")
    parser.add_argument("--source", default="champion_transcript")
    args = parser.parse_args()

    transcript_path = Path(args.transcript)
    transcript = transcript_path.read_text(encoding="utf-8")
    if len(clean(transcript)) < 20:
        raise SystemExit("Transcript trop court : minimum 20 caractères")
    report = build_report(transcript, args.title, args.source)
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.summary).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        f"# F00 STAND UP — {report['title']}", "",
        f"- Mode : `stand_up`", f"- Transcript SHA-256 : `{report['transcript_sha256']}`",
        f"- Unités analysées : {report['transcript_units']}",
        "- Limite : 7 sujets maximum", "- Viralité : score indicatif, jamais une garantie",
        "- Décision Champion : requise avant F01", "", "## Sujets proposés", ""
    ]
    for s in report["subjects"]:
        lines += [
            f"### {s['rank']}. {s['title']}",
            f"- ID : `{s['subject_id']}`",
            f"- Matière brute : {s['core_observation']}",
            f"- Mécanisme : {s['comedy_mechanism']}",
            f"- Score potentiel viral : **{s['virality_score']}/99**",
            f"- Réutilisabilité : **{s['reusability_score']}/99**",
            "- Recherche contexte : en attente de validation / sources externes",
            "- Originalité : revue humaine obligatoire avant transformation finale",
            "- État : en attente de décision Champion", ""
        ]
    Path(args.summary).write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"mode": report["mode"], "subjects": len(report["subjects"]), "output": args.output}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
