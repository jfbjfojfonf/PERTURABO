#!/usr/bin/env python3
"""
F00B_VOX — L'Oreille Absolue.
Sous-frégate de F00_CAPTEURS.

La VOD est un océan. VOX ne boit que les gouttes d'or.

Pipeline : ingest → detect → score → gate → trail
Chaque étape produit un JSON dans OUT/ ; le trail est prêt pour F03_SOURCE_HUNTER.

Hérésies interdites :
❌ Jamais de téléchargement VOD complète (segments HLS uniquement)
❌ Jamais de recompression (stream copy)
❌ Jamais de trail sans verdict gate
❌ Jamais de dépassement du nombre de clips demandés + marge
"""

import argparse
import json
import os
import subprocess
import sys
import hashlib
from datetime import datetime
from math import fabs
from pathlib import Path

# ─── Libs auto-detect (Option A) ────────────────────────────────────────────
CODEBASE_DIR = Path(__file__).resolve().parent
_LIBS_DIR = CODEBASE_DIR / "libs"
if _LIBS_DIR.exists():
    sys.path.insert(0, str(_LIBS_DIR))

# ─── Paths ───────────────────────────────────────────────────────────────────
BASE = Path(__file__).resolve().parent.parent  # F00B_VOX/
IN_DIR = BASE / "IN"
OUT_DIR = BASE / "OUT"
INGEST_DIR = BASE / "vox_ingest"

# ─── Poids scoring ──────────────────────────────────────────────────────────
WEIGHTS = {
    "hook_force": 0.30,
    "emotion": 0.25,
    "clarity": 0.15,
    "quotability": 0.15,
    "timing": 0.10,
    "format_fit": 0.05,
}

# ─── Mots déclencheurs ──────────────────────────────────────────────────────
TRIGGER_WORDS_FR = [
    "whammy", "écoute", "arrête", "jamais", "vraiment", "la vérité",
    "personne", "tout le monde", "la règle", "j'ai", "faut", "écoute",
    "regarde", "attend", "stop", "trop", "dingue", "folie", "monstre",
    "urgent", "méga", "gigantesque", "impossible", "incredible",
    "listen", "actually", "have to", "never", "stop", "truth",
    "nobody", "everybody", "insane", "crazy", "whammy", "huge",
]

TOS_RISK_WORDS = [
    "onlyfans", "of creator", "suicide", "tuer", "mort", "arme",
    "drogue", "nude", "naked", "sexe",
]

SERIES_CUES = [
    "et ensuite", "après", "la suite", "partie 2", "part 2",
    "et puis", "continuons", "on continue", "wait", "next",
]


# ─── Helpers ────────────────────────────────────────────────────────────────
def load_json(path):
    """Charge un fichier JSON. Retourne {} si absent."""
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    """Sauvegarde un fichier JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"  ✅ Sauvegardé : {path}")


def log(msg):
    """Journal console."""
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")


def parse_time(t):
    """Parse 'HH:MM:SS' ou 'HH:MM:SS.mmm' ou float secondes → float."""
    if isinstance(t, (int, float)):
        return float(t)
    s = str(t).strip()
    try:
        return float(s)
    except ValueError:
        pass
    parts = s.replace(",", ".").split(":")
    if len(parts) == 3:
        h, m, sec = parts
        return int(h) * 3600 + int(m) * 60 + float(sec)
    elif len(parts) == 2:
        m, sec = parts
        return int(m) * 60 + float(sec)
    return 0.0


def fmt_time(sec):
    """Secondes → 'HH:MM:SS.mmm'."""
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = sec % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}"


def candidate_id(vod_url, start_sec):
    """ID court unique basé sur URL + start."""
    raw = f"{vod_url}:{start_sec:.2f}"
    return hashlib.md5(raw.encode()).hexdigest()[:10]


def overlap_fraction(a_start, a_end, b_start, b_end):
    """Fraction de chevauchement entre deux fenêtres."""
    inter = max(0, min(a_end, b_end) - max(a_start, b_start))
    dur_a = a_end - a_start
    return inter / dur_a if dur_a > 0 else 0


# ─── INGEST ──────────────────────────────────────────────────────────────────
def cmd_ingest(args):
    """
    Lit IN/vox_input.json, génère les commandes yt-dlp, écrit OUT/vox_manifest.json.

    Format attendu de IN/vox_input.json :
    {
      "vod_urls": [
        {"url": "https://...", "alias": "vod_alias"}
      ],
      "segments": [
        {"alias": "vod_alias", "start": "HH:MM:SS", "end": "HH:MM:SS", "id": "seg01"}
      ],
      "nb_clips_demandes": 4,
      "plateforme": "tiktok",
      "directive_ref": "ARCHIVUM/campaign/whop_directive.md",
      "clip_ref_url": null
    }
    Budget max : 20 min (1200s) par session.
    """
    input_file = IN_DIR / "vox_input.json"
    if not input_file.exists():
        log("❌ IN/vox_input.json introuvable.")
        sys.exit(1)

    data = load_json(input_file)
    vod_urls = data.get("vod_urls", [])
    segments = data.get("segments", [])

    if not segments:
        log("❌ Aucun segment spécifié dans vox_input.json.")
        sys.exit(1)

    # Budget check
    total_sec = sum(parse_time(s["end"]) - parse_time(s["start"]) for s in segments)
    budget_max = data.get("budget_max_sec", 1200)

    if total_sec > budget_max:
        log(f"❌ Budget dépassé : {total_sec:.0f}s / {budget_max}s max")
        sys.exit(1)

    log(f"📥 Budget ingest : {total_sec:.0f}s / {budget_max}s")

    # Générer commandes yt-dlp
    url_map = {v["alias"]: v["url"] for v in vod_urls}
    commands = []
    for seg in segments:
        alias = seg.get("alias", seg.get("vod_alias", ""))
        vod_url = url_map.get(alias, alias)  # alias peut être une URL directe
        start = seg["start"]
        end = seg["end"]
        seg_id = seg.get("id", f"seg_{alias}_{start.replace(':', '')}")
        out_pattern = f"vox_ingest/{seg_id}.%(ext)s"

        cmd = (
            f'yt-dlp --download-sections "*{start}-{end}" '
            f'--force-keyframes-at-cuts '
            f'-f "bv*[height<=1080]+ba/b" '
            f'--concurrent-fragments 5 '
            f'-o "{out_pattern}" '
            f'"{vod_url}"'
        )
        commands.append({
            "segment_id": seg_id,
            "alias": alias,
            "start": start,
            "end": end,
            "duration_sec": parse_time(end) - parse_time(start),
            "command": cmd,
            "output_pattern": out_pattern,
        })

    manifest = {
        "generated_at": datetime.now().isoformat(),
        "vod_urls": vod_urls,
        "total_segments": len(commands),
        "total_duration_sec": total_sec,
        "budget_max_sec": budget_max,
        "commands": commands,
        "nb_clips_demandes": data.get("nb_clips_demandes", 4),
        "plateforme": data.get("plateforme", "tiktok"),
        "directive_ref": data.get("directive_ref"),
        "clip_ref_url": data.get("clip_ref_url"),
    }

    save_json(OUT_DIR / "vox_manifest.json", manifest)
    log(f"📋 {len(commands)} commandes générées → OUT/vox_manifest.json")
    log("⚡ Pour exécuter : lancez chaque commande ou utilisez --execute")

    if args.execute:
        INGEST_DIR.mkdir(parents=True, exist_ok=True)
        for c in commands:
            log(f"  ⏬ Exécution : {c['segment_id']}")
            subprocess.run(c["command"], shell=True, check=False)
        log("✅ Ingest terminé")


# ─── DETECT ──────────────────────────────────────────────────────────────────
def cmd_detect(args):
    """
    Détecte les candidats (fenêtres 20-40s) à partir des signaux fournis.

    Format attendu de IN/signals.json :
    {
      "signals": [
        {"start": "HH:MM:SS", "end": "HH:MM:SS", "type": "chat_spike|energy|trigger_word|punchline", "intensity": 1.0}
      ],
      "pre_roll_sec": 2.0,
      "post_roll_sec": 2.0,
      "duree_cible_sec": 30,
      "duree_max_sec": 60,
      "duree_min_sec": 15
    }
    """
    manifest = load_json(OUT_DIR / "vox_manifest.json")
    if not manifest:
        log("❌ Lancez 'ingest' d'abord (vox_manifest.json requis).")
        sys.exit(1)

    signals_file = IN_DIR / "signals.json"
    if not signals_file.exists():
        log("❌ IN/signals.json introuvable.")
        sys.exit(1)

    sdata = load_json(signals_file)
    signals = sdata.get("signals", [])
    pre_roll = sdata.get("pre_roll_sec", 2.0)
    post_roll = sdata.get("post_roll_sec", 2.0)
    duree_cible = sdata.get("duree_cible_sec", 30)
    duree_max = sdata.get("duree_max_sec", 60)
    duree_min = sdata.get("duree_min_sec", 15)

    if not signals:
        log("⚠️ Aucun signal détecté. Créez IN/signals.json avec les timestamps.")
        sys.exit(1)

    log(f"🔍 {len(signals)} signaux analysés")

    # Trier par start
    signals.sort(key=lambda s: parse_time(s["start"]))

    # Générer candidats autour de chaque signal
    candidats_bruts = []
    for sig in signals:
        sig_start = parse_time(sig["start"])
        sig_end = parse_time(sig.get("end", sig["start"]))
        sig_type = sig.get("type", "unknown")
        intensity = sig.get("intensity", 1.0)

        # Fenêtre = start - pre_roll, fin = sig_end + post_roll
        # Puis étendre à duree_cible si possible
        cand_start = max(0, sig_start - pre_roll)
        cand_end = sig_end + post_roll

        # Étendre si trop court
        current_dur = cand_end - cand_start
        if current_dur < duree_cible:
            extend = duree_cible - current_dur
            cand_end += extend * 0.7
            cand_start = max(0, cand_start - extend * 0.3)

        # Tronquer si trop long
        if cand_end - cand_start > duree_max:
            cand_end = cand_start + duree_max

        cid = candidate_id(str(sig), cand_start)
        candidats_bruts.append({
            "candidate_id": cid,
            "start_sec": round(cand_start, 2),
            "end_sec": round(cand_end, 2),
            "duration_sec": round(cand_end - cand_start, 2),
            "signal_type": sig_type,
            "signal_intensity": intensity,
            "signal_start": sig["start"],
        })

    # Dédoublonner chevauchements > 50%
    candidats = []
    candidats.sort(key=lambda c: c["start_sec"], reverse=True)

    for cand in candidats_bruts:
        merged = False
        for existing in candidats:
            if overlap_fraction(cand["start_sec"], cand["end_sec"],
                               existing["start_sec"], existing["end_sec"]) > 0.5:
                # Garder le plus intense
                if cand["signal_intensity"] > existing["signal_intensity"]:
                    candidats.remove(existing)
                    candidats.append(cand)
                merged = True
                break
        if not merged:
            candidats.append(cand)

    candidats.sort(key=lambda c: c["start_sec"])

    output = {
        "generated_at": datetime.now().isoformat(),
        "total_signals": len(signals),
        "total_candidats": len(candidats),
        "candidats": candidats,
    }

    save_json(OUT_DIR / "candidats.json", output)
    log(f"🎯 {len(candidats)} candidats détectés → OUT/candidats.json")


# ─── SCORE ───────────────────────────────────────────────────────────────────
def score_hook_force(cand):
    """Score 0-10 : force du hook (première phrase)."""
    score = 4.0
    text = cand.get("signal_type", "").lower()
    intensity = cand.get("signal_intensity", 1.0)

    if text in ("trigger_word", "punchline"):
        score += 2.5
    if intensity >= 0.8:
        score += 1.5
    if intensity >= 0.5:
        score += 1.0

    # Durée courte = hook plus percutant
    dur = cand.get("duration_sec", 30)
    if dur <= 25:
        score += 1.0
    elif dur > 50:
        score -= 1.0

    return max(0, min(10, round(score, 1)))


def score_emotion(cand):
    """Score 0-10 : intensité émotionnelle."""
    score = 3.0
    stype = cand.get("signal_type", "")
    intensity = cand.get("signal_intensity", 1.0)

    if stype in ("chat_spike", "energy"):
        score += 3.0
    if stype == "punchline":
        score += 2.0
    if intensity >= 0.8:
        score += 2.0
    elif intensity >= 0.5:
        score += 1.0

    return max(0, min(10, round(score, 1)))


def score_clarity(cand):
    """Score 0-10 : clarté sans contexte."""
    score = 6.0
    # Les signaux punchline = souvent clairs
    if cand.get("signal_type") == "punchline":
        score += 2.0
    # Intensité forte souvent = moment marquant et compréhensible
    if cand.get("signal_intensity", 0) >= 0.7:
        score += 1.0
    return max(0, min(10, round(score, 1)))


def score_quotability(cand):
    """Score 0-10 : potentiel de citation."""
    score = 3.0
    if cand.get("signal_type") == "punchline":
        score += 3.0
    if cand.get("signal_intensity", 0) >= 0.8:
        score += 2.0
    # Moments très intenses souvent citables
    if cand.get("signal_intensity", 0) >= 0.6:
        score += 1.0
    return max(0, min(10, round(score, 1)))


def score_timing(cand):
    """Score 0-10 : rythme interne."""
    score = 5.0
    dur = cand.get("duration_sec", 30)
    # Fenêtre optimale 20-35s = bon rythme
    if 20 <= dur <= 35:
        score += 2.0
    elif 15 <= dur <= 45:
        score += 1.0
    elif dur > 50:
        score -= 1.0

    # Signal intense = changement rapide d'énergie
    if cand.get("signal_intensity", 0) >= 0.7:
        score += 1.0

    return max(0, min(10, round(score, 1)))


def score_format_fit(cand):
    """Score 0-10 : adéquation format vertical 9:16."""
    score = 6.0
    # Par défaut on suppose que le recadrage est faisable
    dur = cand.get("duration_sec", 30)
    if dur <= 40:
        score += 1.5
    elif dur > 55:
        score -= 1.0
    if cand.get("signal_type") in ("punchline", "trigger_word"):
        score += 0.5
    return max(0, min(10, round(score, 1)))


SCORE_FUNCS = {
    "hook_force": score_hook_force,
    "emotion": score_emotion,
    "clarity": score_clarity,
    "quotability": score_quotability,
    "timing": score_timing,
    "format_fit": score_format_fit,
}


def compute_score(cand, weights=None):
    """Calcule le score pondéré + bonus/malus pour un candidat."""
    w = weights or WEIGHTS
    raw = {}
    for critere, func in SCORE_FUNCS.items():
        raw[critere] = func(cand)

    base = sum(w[k] * raw[k] for k in raw)

    # Bonus / malus
    bonuses = []
    maluses = []
    dur = cand.get("duration_sec", 30)

    if dur > 60:
        maluses.append({"rule": "duree_gt_60", "delta": -3.0})
    if dur < 15:
        maluses.append({"rule": "duree_lt_15", "delta": -3.0})

    intensity = cand.get("signal_intensity", 1.0)
    if intensity >= 0.9:
        bonuses.append({"rule": "moment_unique", "delta": 1.5})
    if intensity >= 0.7:
        bonuses.append({"rule": "haute_intensite", "delta": 1.0})

    # Risque TOS
    stype = cand.get("signal_type", "")
    if stype in ("trigger_word", "punchline") and intensity < 0.3:
        maluses.append({"rule": "contexte_externe_possible", "delta": -2.0})

    bonus_total = sum(b["delta"] for b in bonuses)
    malus_total = sum(m["delta"] for m in maluses)
    final = max(0, min(10, round(base + bonus_total + malus_total, 2)))

    return {
        "candidate_id": cand["candidate_id"],
        "raw_scores": raw,
        "base_score": round(base, 2),
        "bonuses": bonuses,
        "maluses": maluses,
        "bonus_total": round(bonus_total, 2),
        "malus_total": round(malus_total, 2),
        "final_score": final,
        "start_sec": cand["start_sec"],
        "end_sec": cand["end_sec"],
        "duration_sec": cand["duration_sec"],
        "signal_type": cand.get("signal_type"),
        "signal_intensity": cand.get("signal_intensity"),
        "status": "scored",
    }


def cmd_score(args):
    """Score tous les candidats détectés."""
    candidats_data = load_json(OUT_DIR / "candidats.json")
    if not candidats_data or not candidats_data.get("candidats"):
        log("❌ Lancez 'detect' d'abord (candidats.json requis).")
        sys.exit(1)

    # Poids optionnels depuis IN/score_weights.json
    weights = WEIGHTS
    weights_file = IN_DIR / "score_weights.json"
    if weights_file.exists():
        custom = load_json(weights_file)
        weights = {**WEIGHTS, **custom}
        log("📊 Poids personnalisés chargés depuis IN/score_weights.json")

    candidats = candidats_data["candidats"]
    scored = [compute_score(c, weights) for c in candidats]
    scored.sort(key=lambda s: s["final_score"], reverse=True)

    # Rejet automatique
    for s in scored:
        reasons = []
        if s["final_score"] < 6.0:
            reasons.append("score_lt_6")
        if s["duration_sec"] > 60 or s["duration_sec"] < 15:
            reasons.append("duree_hors_limites")
        if reasons:
            s["status"] = "auto_rejected"
            s["rejection_reasons"] = reasons

    output = {
        "generated_at": datetime.now().isoformat(),
        "formula": "score = Σ(weight_i × criteria_i) + bonus - malus",
        "weights": weights,
        "total_scored": len(scored),
        "total_accepted": sum(1 for s in scored if s["status"] == "scored"),
        "total_auto_rejected": sum(1 for s in scored if s["status"] == "auto_rejected"),
        "candidates": scored,
    }

    save_json(OUT_DIR / "scoring.json", output)
    log(f"📊 {output['total_accepted']} acceptés, {output['total_auto_rejected']} auto-rejetés")


# ─── GATE ────────────────────────────────────────────────────────────────────
def cmd_gate(args):
    """
    Génère gate_verdict.json — skeleton pour validation Warsmith.

    Chaque candidat scored → statut "pending_warsmith".
    Le Warsmith édite le fichier pour mettre : approve / reject / modify.
    """
    scoring = load_json(OUT_DIR / "scoring.json")
    if not scoring or not scoring.get("candidates"):
        log("❌ Lancez 'score' d'abord (scoring.json requis).")
        sys.exit(1)

    candidates = scoring["candidates"]

    verdicts = []
    for c in candidates:
        if c["status"] == "auto_rejected":
            verdicts.append({
                "candidate_id": c["candidate_id"],
                "status": "rejected",
                "score": c["final_score"],
                "motif": "auto_rejected: " + ", ".join(c.get("rejection_reasons", [])),
                "start_sec": c["start_sec"],
                "end_sec": c["end_sec"],
                "duration_sec": c["duration_sec"],
                "signal_type": c.get("signal_type"),
            })
        else:
            verdicts.append({
                "candidate_id": c["candidate_id"],
                "status": "pending_warsmith",
                "score": c["final_score"],
                "motif": None,
                "start_sec": c["start_sec"],
                "end_sec": c["end_sec"],
                "duration_sec": c["duration_sec"],
                "signal_type": c.get("signal_type"),
            })

    output = {
        "generated_at": datetime.now().isoformat(),
        "type": "SOUS-FREGATE_GATE",
        "validateur": "Warsmith",
        "regle_d_or": "Pas de clip sans verdict. Le Warsmith décide du nombre final.",
        "total_candidates": len(verdicts),
        "pending_warsmith": sum(1 for v in verdicts if v["status"] == "pending_warsmith"),
        "auto_rejected": sum(1 for v in verdicts if v["status"] == "rejected"),
        "verdicts": verdicts,
    }

    save_json(OUT_DIR / "gate_verdict.json", output)
    log(f"🚪 Gate : {output['pending_warsmith']} candidats en attente du Warsmith")
    log("   → Éditez OUT/gate_verdict.json : changez 'pending_warsmith' → 'approved' ou 'rejected'")
    log("   → Puis lancez 'trail' pour finaliser les segments validés")


def cmd_gate_apply(args):
    """
    Applique les décisions du Warsmith depuis IN/gate_decisions.json.

    Format IN/gate_decisions.json :
    {
      "decisions": [
        {"candidate_id": "abc123", "status": "approved"},
        {"candidate_id": "def456", "status": "rejected", "motif": "pas assez drôle"},
        {"candidate_id": "ghi789", "status": "approved", "adjusted_start": 12.5, "adjusted_end": 42.0}
      ]
    }
    """
    gate = load_json(OUT_DIR / "gate_verdict.json")
    if not gate:
        log("❌ Lancez 'gate' d'abord.")
        sys.exit(1)

    decisions_file = IN_DIR / "gate_decisions.json"
    if not decisions_file.exists():
        log("❌ IN/gate_decisions.json introuvable (éditez-le après 'gate').")
        sys.exit(1)

    ddata = load_json(decisions_file)
    decisions = {d["candidate_id"]: d for d in ddata.get("decisions", [])}

    updated = 0
    for v in gate["verdicts"]:
        cid = v["candidate_id"]
        if v["status"] == "rejected":
            continue  # auto-rejetés restent rejetés

        if cid in decisions:
            dec = decisions[cid]
            v["status"] = dec.get("status", v["status"])
            v["motif"] = dec.get("motif", v.get("motif"))
            if dec.get("adjusted_start") is not None:
                v["start_sec"] = dec["adjusted_start"]
            if dec.get("adjusted_end") is not None:
                v["end_sec"] = dec["adjusted_end"]
                v["duration_sec"] = v["end_sec"] - v["start_sec"]
            updated += 1

    gate["validated_at"] = datetime.now().isoformat()
    gate["total_trail_ready"] = sum(1 for v in gate["verdicts"] if v["status"] == "approved")

    save_json(OUT_DIR / "gate_verdict.json", gate)
    log(f"✅ {updated} décisions appliquées → {gate['total_trail_ready']} candidats trail_ready")


# ─── TRAIL ───────────────────────────────────────────────────────────────────
def cmd_trail(args):
    """
    Génère trail.json — segments finaux prêts pour F03_SOURCE_HUNTER.
    Seuls les candidats 'approved' (ou 'trail_ready') produisent un trail.
    """
    gate = load_json(OUT_DIR / "gate_verdict.json")
    if not gate:
        log("❌ Lancez 'gate' d'abord.")
        sys.exit(1)

    approved = [v for v in gate["verdicts"] if v["status"] in ("approved", "trail_ready")]
    if not approved:
        log("❌ Aucun candidat approuvé par le Warsmith.")
        sys.exit(1)

    scoring = load_json(OUT_DIR / "scoring.json")
    score_map = {s["candidate_id"]: s for s in scoring.get("candidates", [])}

    trails = []
    for v in approved:
        cid = v["candidate_id"]
        start = v["start_sec"]
        end = v.get("end_sec", start + v.get("duration_sec", 30))
        duration = end - start

        # Points de coupure internes (>1.5s = silence potentiel)
        # Détection heuristique :暂 placeholder — sera affiné avec analyse audio réelle
        internal_cuts = []
        # On place des cuts tous les 8-12 secondes si > 20s
        if duration > 20:
            t = start + 8
            while t < end - 3:
                internal_cuts.append({
                    "at_sec": round(t, 2),
                    "at_time": fmt_time(t),
                    "reason": "coupure potentielle (rythme interne)",
                    "action": "split_or_transition",
                })
                t += 10

        # Hook potentiel : premier tiers de la fenêtre
        hook_end = start + min(3, duration * 0.15)

        trails.append({
            "candidate_id": cid,
            "start_sec": round(start, 2),
            "end_sec": round(end, 2),
            "duration_sec": round(duration, 2),
            "start_time": fmt_time(start),
            "end_time": fmt_time(end),
            "score": v.get("score", score_map.get(cid, {}).get("final_score", 0)),
            "hook_window": {
                "start_sec": round(start, 2),
                "end_sec": round(hook_end, 2),
                "note": "zone hook : 0-3s ou premier 15%",
            },
            "internal_cuts": internal_cuts,
            "cut_count": len(internal_cuts),
            "trail_spec": {
                "format": "9:16",
                "export_quality": "1080x1920",
                "stream_copy": True,
                "note": "Trail extrait en stream copy, pas de recompression",
            },
        })

    output = {
        "generated_at": datetime.now().isoformat(),
        "total_trails": len(trails),
        "trails": trails,
        "next_step": "F03_SOURCE_HUNTER reçoit trail.json",
    }

    save_json(OUT_DIR / "trail.json", output)
    log(f"🛤️ {len(trails)} trails générés → OUT/trail.json")
    log("🚀 Prêt pour F03_SOURCE_HUNTER")


# ─── CLI ─────────────────────────────────────────────────────────────────────
def cmd_auto_detect(args):
    """
    Auto-detect : audio seul → transcription word-level → chat replay
    → scoring → candidats.json (même schéma que detect).
    Le Warsmith valide ensuite via gate.

    Nécessite : yt-dlp + ffmpeg (installés), + clé premium pour la
    transcription (CONTRACTS/f00b_secrets.json ou AI_GATEWAY_API_KEY).
    """
    try:
        from auto_detector import run_auto_detect
    except ImportError as e:
        log(f"❌ Module auto-detect indisponible : {e}")
        log("   Installer les dépendances : pip install -r requirements_f00b.txt")
        sys.exit(1)

    input_file = IN_DIR / "vox_input.json"
    if not input_file.exists():
        log("❌ IN/vox_input.json introuvable.")
        log("   Créer le fichier avec vod_urls + nb_clips_demandes minimum.")
        sys.exit(1)

    data = load_json(input_file)
    vod_urls = data.get("vod_urls", [])
    if not vod_urls:
        log("❌ Aucune URL VOD dans vox_input.json.")
        sys.exit(1)

    vod_url = vod_urls[0].get("url") if isinstance(vod_urls[0], dict) else vod_urls[0]
    nb_clips = data.get("nb_clips_demandes", args.nb_clips or 5)
    market = getattr(args, "market", None) or "us_young_english"
    platform = getattr(args, "platform", None) or data.get("plateforme", "youtube")
    keep_audio = getattr(args, "keep_audio", False)
    no_chat = getattr(args, "no_chat", False)

    # Calcul de la racine du dépôt (4 niveaux au-dessus de F00B_VOX/)
    # run_auto_detect attend la racine du dépôt pour retrouver MONDES_FORGES/.
    forge_root = str(BASE.parent.parent.parent.parent)

    run_auto_detect(
        forge_root=forge_root,
        vod_url=vod_url,
        nb_clips=nb_clips,
        market=market,
        platform=platform,
        keep_audio=keep_audio,
        no_chat=no_chat,
    )


def main():
    parser = argparse.ArgumentParser(
        description="F00B_VOX — L'Oreille Absolue. Pipeline VOD Twitch → clips trail_ready.",
    )
    parser.add_argument(
        "command",
        choices=["ingest", "detect", "score", "gate", "gate_apply",
                 "trail", "status", "auto_detect"],
        help="Étape du pipeline VOX",
    )
    parser.add_argument("--execute", action="store_true", help="Exécuter les commandes yt-dlp (ingest)")
    parser.add_argument("--keep-audio", action="store_true",
                        help="Conserver l'audio après auto_detect (debug)")
    parser.add_argument("--no-chat", action="store_true",
                        help="Ignorer le chat replay (auto_detect)")
    parser.add_argument("--market", default=None,
                        help="Marché cible (auto_detect, défaut: us_young_english)")
    parser.add_argument("--platform", default=None,
                        help="Plateforme cible (auto_detect)")
    parser.add_argument("--nb-clips", type=int, default=None,
                        help="Nombre de clips (auto_detect, défaut depuis vox_input)")

    args = parser.parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    IN_DIR.mkdir(parents=True, exist_ok=True)

    log(f"═══ F00B_VOX — {args.command.upper()} ═══")

    if args.command == "ingest":
        cmd_ingest(args)
    elif args.command == "auto_detect":
        cmd_auto_detect(args)
    elif args.command == "detect":
        cmd_detect(args)
    elif args.command == "score":
        cmd_score(args)
    elif args.command == "gate":
        cmd_gate(args)
    elif args.command == "gate_apply":
        cmd_gate_apply(args)
    elif args.command == "trail":
        cmd_trail(args)
    elif args.command == "status":
        cmd_status()


def cmd_status():
    """Affiche l'état du pipeline VOX."""
    files = {
        "manifest": OUT_DIR / "vox_manifest.json",
        "candidats": OUT_DIR / "candidats.json",
        "scoring": OUT_DIR / "scoring.json",
        "gate": OUT_DIR / "gate_verdict.json",
        "trail": OUT_DIR / "trail.json",
    }
    log("═══ ÉTAT VOX ═══")
    for name, path in files.items():
        status = "✅" if path.exists() else "—"
        print(f"  {status} {name:12s} : {path}")
    log("═══════════════")


if __name__ == "__main__":
    main()
