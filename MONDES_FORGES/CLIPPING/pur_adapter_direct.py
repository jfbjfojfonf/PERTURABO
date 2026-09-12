#!/usr/bin/env python3
"""
pur_adapter_direct.py — Adaptateur Mode PUR direct (VOX -> F04)
================================================================
En Mode PUR, le flux est : F00B_VOX ou F00C_VOX -> F04_COPYWRITER (direct).
F01 (acquisition), F02 (verdict/angles océan bleu) et F03 (sélection segment)
sont SKIP : VOX a déjà détecté, scoré et sélectionné les moments viraux.

Cet adaptateur produit les 2 sorties que F04_COPYWRITER cherche :
  1. F02_TYRANT_CAMP/OUT/angles.json             (angles forgés en PUR)
  2. F03_SOURCE_HUNTER/OUT/source_specimen_{id}.json (specimen par candidat)

Le verdict est déjà présent dans ARCHIVUM/campaign/verdict.json (GO, run F02).

Angles PUR : famille 'reframing' (hooks_pur.json), 1 angle par candidat VOX,
reframe_dim dérivé du type de signal détecté. Le copywriting premium (kimi-k3)
fait le vrai travail de formulation.

Contrat opérateur (operator_brief) :
  --nb-videos N     nombre de vidéos finales (1-10) -> N angles/clip packs
  --asset-mode M    ranking | blur | split  (type de contenu demandé)

Usage :
  python pur_adapter_direct.py \
      --candidats F00B_VOX/OUT/candidats.json \
      --vod <url> --platform youtube_shorts --market us_young_english \
      --nb-videos 5 --asset-mode blur
"""

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "SHARED"))
from candidates_reader import CandidatesReadError, load_candidates_document  # noqa: E402


_REFLEX_DIM = {
    "punchline": "neutre_vers_dramatique",
    "trigger_word": "serieux_vers_funny",
    "energy": "neutre_vers_inspirational",
    "mixed": "personnel_vers_universel",
    "chat_spike": "neutre_vers_dramatique",
    "platform_heat": "neutre_vers_dramatique",
}


def _now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _slug(s):
    return re.sub(r'[^a-z0-9]+', '_', str(s).lower()).strip('_')


def _angle_id(idx):
    return "A{:02d}".format(idx + 1)


def load_json(p):
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    ap = argparse.ArgumentParser(description="Adaptateur PUR direct VOX -> F04")
    ap.add_argument("--candidats", required=True)
    ap.add_argument("--vod", required=True)
    ap.add_argument("--platform", default="youtube_shorts")
    ap.add_argument("--market", default="us_young_english")
    ap.add_argument("--nb-videos", type=int, default=1,
                    help="Nombre de vidéos finales (1-10) — détermine le nombre d'assets")
    ap.add_argument("--asset-mode", default="ranking",
                    choices=["ranking", "blur", "split", "overlay_only"],
                    help="Type de contenu demandé par l'opérateur")
    args = ap.parse_args()

    nb_videos = max(1, min(10, int(args.nb_videos or 1)))

    # chemins relatifs au repo (l'adaptateur vit à MONDES_FORGES/CLIPPING/)
    here = os.path.dirname(os.path.abspath(__file__))
    clip_root = here  # MONDES_FORGES/CLIPPING
    f02_out = os.path.join(clip_root, "F02_TYRANT_CAMP", "OUT")
    f03_out = os.path.join(clip_root, "F03_SOURCE_HUNTER", "OUT")
    os.makedirs(f02_out, exist_ok=True)
    os.makedirs(f03_out, exist_ok=True)

    try:
        cands = load_candidates_document(args.candidats)
    except CandidatesReadError as exc:
        print("[PUR_DIRECT] ERREUR: {}".format(exc), file=sys.stderr)
        sys.exit(1)
    candidates = cands.get("candidates", [])
    # L'opérateur décide du nombre de vidéos finales : on garde les N premiers
    # candidats (déjà triés par priorité VOX).
    candidates = candidates[:nb_videos]

    angles = []
    for i, c in enumerate(candidates):
        aid = _angle_id(i)
        sig = c.get("signal_type") or "mixed"
        intens = c.get("signal_intensity", 0.5)
        st = c.get("start_sec"); en = c.get("end_sec")
        top_words = c.get("top_words") or ""
        angles.append({
            "angle_id": aid,
            "emotion": "intrigue",
            "emotion_mode": "intrigue",
            "angle_family": "reframing",
            "reframe_dim": _REFLEX_DIM.get(sig, "personnel_vers_universel"),
            "engagement_type": "question" if sig == "trigger_word" else "hot_take",
            "duration_sec_range": {"min": int(en - st) if (en and st) else 20,
                                  "max": int(en - st) + 10 if (en and st) else 35},
            "zone": "direct",
            "keyword": _slug(top_words[:40] or "pur"),
            "weight": round(0.6 + float(intens) * 0.4, 3),
            "vox_signal_type": sig,
            "vox_intensity": intens,
            "asset_mode": args.asset_mode,
        })
        # specimen par candidat (ce que F04 attend dans F03_SOURCE_HUNTER/OUT)
        specimen = {
            "campaign_id": cands.get("campaign_id") if isinstance(cands, dict) else None,
            "mode": "pur",
            "angle_id": aid,
            "source_type": "vox_candidate",
            "vod_url": args.vod,
            "start_sec": st, "end_sec": en,
            "duration_sec": (en - st) if (en and st) else None,
            "signal_type": sig,
            "signal_intensity": intens,
            "top_words": top_words,
            "reference_clip_required": False,
            "transcript_available": True,
            "scanned_at": _now_iso(),
        }
        sp_path = os.path.join(f03_out, "source_specimen_{}.json".format(aid))
        with open(sp_path, "w", encoding="utf-8") as f:
            json.dump(specimen, f, indent=2, ensure_ascii=False)

    angles_doc = {
        "campaign_id": cands.get("campaign_id") if isinstance(cands, dict) else None,
        "n_angles": len(angles),
        "anglesmith_status": "done",
        "weighting_eligible": False,
        "sub_mode": "pur",
        "forge_mode": "premium",
        "asset_mode": args.asset_mode,
        "nb_videos_finales": nb_videos,
        "angles": angles,
    }
    ang_path = os.path.join(f02_out, "angles.json")
    with open(ang_path, "w", encoding="utf-8") as f:
        json.dump(angles_doc, f, indent=2, ensure_ascii=False)

    print("[PUR_DIRECT] angles.json -> {} ({} angles)".format(ang_path, len(angles)))
    print("[PUR_DIRECT] source_specimen_* -> {} ({} specimens)".format(f03_out, len(angles)))


if __name__ == "__main__":
    main()
