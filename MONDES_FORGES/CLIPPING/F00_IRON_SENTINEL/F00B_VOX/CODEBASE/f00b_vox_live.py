#!/usr/bin/env python3
"""
f00b_vox_live — La session LIVE de VOX (branche v2-live).

Le VOD est le passé. Le live est maintenant.

Flow d'une session :
  1. Lecture de IN/live_input.json (chaînes, durée, gate hybride)
  2. Démarrage du Radar (chat_pulse) — IRC Twitch anonyme, multi-chaînes
  3. Chaque MOMENT détecté :
       - clip serveur Helix capté IMMÉDIATEMENT (si TWITCH_TOKEN présent)
       - bornes converties en HH:MM:SS relatifs au début du stream
       - fenêtre candidat générée au format EXACT de IN/signals.json
       - scoring réutilisé TEL QUEL depuis f00b_vox.py (6 critères + bonus/malus)
       - GATE HYBRIDE :
           * score >= auto_score_min ET intensité >= auto_intensity_min
             → auto-approuvé (le live n'attend pas)
           * sinon → file d'attente Warsmith (validable depuis le téléphone)
  4. Écriture continue de OUT/live_status.json (le board docs/index.html le lit)
  5. Fin de session : candidats_live.json + scoring_live.json + trail.json
     (même schéma que le mode VOD → F04/F06 ne voient AUCUNE différence)

Hérésies interdites :
❌ Jamais de trail sans verdict (auto ou Warsmith)
❌ Jamais deux moments hors bornes du stream (clip après started_at)
❌ Jamais de dépendance pip (stdlib uniquement)
"""

import json
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

CODEBASE_DIR = Path(__file__).resolve().parent
_LIBS_DIR = CODEBASE_DIR / "libs"
if _LIBS_DIR.exists():
    sys.path.insert(0, str(_LIBS_DIR))

from chat_pulse import Radar, log_line  # noqa: E402
import campaign_gate as cgate  # noqa: E402 — le Garde de Fer des campagnes

# Réutilisation stricte du moteur VOX existant (même scoring, même doctrine)
import f00b_vox as vox  # noqa: E402

BASE = CODEBASE_DIR.parent          # F00B_VOX/
IN_DIR = BASE / "IN"
OUT_DIR = BASE / "OUT"


# ─── Helpers ─────────────────────────────────────────────────────────────────
def load_json(path):
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    log_line(f"💾 {path}")


def stream_started_epoch(stream_info):
    """started_at ISO 8601 UTC → epoch secondes."""
    iso = stream_info.get("started_at")
    if not iso:
        return None
    dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    return dt.timestamp()


def epoch_to_stream_time(epoch, started_epoch):
    """Epoch absolu → HH:MM:SS relatif au début du stream (format signaux VOX)."""
    if started_epoch is None:
        started_epoch = epoch  # fallback : démarrage inconnu = maintenant
    sec = max(0, epoch - started_epoch)
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = int(sec % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def helix_enabled():
    try:
        import helix_clipper
        return helix_clipper.is_token_ready()
    except Exception:  # noqa: BLE001
        return False


def helix_capture(moment):
    """Capture un clip serveur Helix pour ce moment. Retourne dict ou None."""
    if not helix_enabled():
        return None
    try:
        import helix_clipper as hx
        info = hx.get_stream_info(moment["channel"])
        if not info or not info.get("is_live"):
            return None
        clip = hx.create_clip(info["broadcaster_id"])
        if clip:
            log_line(f"🎬 Clip Helix capté : {clip['clip_id']} ({moment['channel']})")
            return clip
    except Exception as exc:  # noqa: BLE001 — jamais tuer la session pour un clip raté
        log_line(f"⚠️ Helix fail ({moment['channel']}) : {exc}")
    return None


# ─── Gate hybride ────────────────────────────────────────────────────────────
def hybrid_gate(scored, cfg):
    """
    Applique le gate hybride à un candidat scoré.
    Retourne (verdict_status, motif).
      - auto_approved : score + intensité au-dessus des seuils → trail immédiat
      - pending_warsmith : file d'attente (validation téléphone)
      - auto_rejected : hors critères durs
    """
    thresholds = cfg.get("gate_hybrid", {})
    s_min = thresholds.get("auto_score_min", 8.5)
    i_min = thresholds.get("auto_intensity_min", 0.9)
    max_pending = thresholds.get("max_pending_warsmith", 12)

    if scored["status"] == "auto_rejected":
        return "rejected", "auto: " + ", ".join(scored.get("rejection_reasons", []))
    if scored["final_score"] >= s_min and (scored.get("signal_intensity") or 0) >= i_min:
        return "approved", "auto_approve: score {:.2f} >= {} + intensite {:.2f} >= {}".format(
            scored["final_score"], s_min, scored.get("signal_intensity") or 0, i_min)
    if scored["final_score"] >= thresholds.get("pending_score_min", 6.0):
        if max_pending > 0:
            return "pending_warsmith", "file d'attente Warsmith"
    return "rejected", "auto: sous les seuils du gate hybride"


# ─── Session ─────────────────────────────────────────────────────────────────
def run_session(cfg):
    channels = cfg.get("twitch_channels", [])
    if not channels:
        log_line("❌ Aucune chaîne dans twitch_channels. Rien à écouter.")
        sys.exit(1)

    # ─── Garde de Fer des campagnes (registry → mode de session) ───
    resolved = cgate.resolve_channels(channels)
    mode = cgate.session_mode(resolved)
    override = (cfg.get("session_mode") or "").strip()
    if override in ("", "auto"):
        override = None
    for ch, r in resolved.items():
        log_line(f"🏛️ {ch} → {r['reason']}")
    if mode == "mixed" and override != "technical_test":
        log_line("❌ Session MIXTE interdite (chaînes éligibles + non éligibles). "
                 "Relance en une seule catégorie, ou avec mode_override=technical_test.")
        sys.exit(1)
    if override == "technical_test":
        log_line("🧪 Override opérateur : session TECHNIQUE — clips marqués non soumissables.")
        mode = "technical_test"
    elif override == "campaign" and mode != "campaign":
        log_line("❌ Override 'campaign' demandé mais aucune chaîne éligible "
                 "(registry absente ou cycle expiré). Vérifier live_campaigns.json.")
        sys.exit(1)
    # La session entière porte son mode (verdicts + board)
    cfg["_campaign"] = {
        "session_mode": mode,
        "channels": {
            ch: {"campaign_id": r.get("campaign_id"), "eligible": r.get("eligible"),
                 "reason": r.get("reason")}
            for ch, r in resolved.items()
        },
    }
    log_line(f"🎯 Mode session : {mode}"
             + (" — clips soumissibles (campagne active)" if mode == "campaign"
                else " — NON soumissible"))

    duration_min = cfg.get("session_duration_min", 240)
    deadline = time.time() + duration_min * 60
    status_every = cfg.get("status_every_sec", 180)
    last_status = 0.0

    stream_started = {}   # channel → epoch (depuis Helix si dispo)
    for ch in channels:
        if helix_enabled():
            try:
                import helix_clipper as hx
                info = hx.get_stream_info(ch)
                if info and info.get("is_live"):
                    stream_started[ch] = stream_started_epoch(info)
                    log_line(f"📡 {ch} en LIVE depuis {info['started_at']} "
                             f"({info['viewers']} viewers, {info['game']})")
                    continue
            except Exception:  # noqa: BLE001
                pass
        log_line(f"📡 {ch} : démarrage live inconnu (bornes relatives au début de session)")

    radar = Radar(
        twitch_channels=channels,
        kick_channels=cfg.get("kick_channels"),
        config=cfg.get("radar", {}),
    ).start()
    log_line(f"🛰️ Radar armé sur {len(channels)} chaîne(s) — session max {duration_min} min")
    log_line(f"🔑 Helix : {'ACTIF (clips serveur immédiats)' if helix_enabled() else 'inactif (TWITCH_TOKEN absent) — timestamps seuls'}")

    moments_all = []
    candidats_live = []
    scored_all = []
    verdicts_all = []
    clips_all = []

    try:
        while time.time() < deadline:
            now = time.time()

            # Statut pour le board (toutes les N secondes)
            if now - last_status >= status_every:
                write_status(channels, radar, moments_all, verdicts_all, clips_all,
                             deadline, stream_started, cfg=cfg)
                last_status = now

            # Moments détectés (bloque 5s max)
            moments = radar.drain(block_timeout=5.0)
            for moment in moments:
                moments_all.append(moment)
                ch = moment["channel"]
                started = stream_started.get(ch)

                # 1. Clip serveur immédiat
                clip = helix_capture(moment)
                if clip:
                    moment["helix_clip"] = clip
                    clips_all.append({"moment": moment, "clip": clip})

                # 2. Conversion en fenêtre signal VOX (format EXACT IN/signals.json)
                s_start = moment.get("start_epoch", now - 10)
                s_end = moment.get("end_epoch", now + 30)
                sig = {
                    "start": epoch_to_stream_time(s_start, started),
                    "end": epoch_to_stream_time(s_end, started),
                    "type": "chat_spike",
                    "intensity": moment.get("intensity", 0.8),
                }
                cand = build_candidate(sig, moment, cfg)

                # 3. Scoring live calibré (force réelle du pic) — moteur VOD intact
                scored = compute_score_live(cand, moment)
                scored_all.append(scored)

                # 4. Gate hybride
                status, motif = hybrid_gate(scored, cfg)
                verdict = {
                    "candidate_id": scored["candidate_id"],
                    "status": status,
                    "score": scored["final_score"],
                    "motif": motif,
                    "start_sec": scored["start_sec"],
                    "end_sec": scored["end_sec"],
                    "duration_sec": scored["duration_sec"],
                    "signal_type": scored["signal_type"],
                    "channel": ch,
                    "detected_at": moment.get("detected_at"),
                    "helix_clip_id": (clip or {}).get("clip_id"),
                }
                # Éligibilité campagne (Garde de Fer) : la session technique
                # dégrade TOUT en non soumissible, même une chaîne connue.
                camp_f = cgate.campaign_fields(ch, resolved)
                if mode != "campaign":
                    camp_f["campaign_eligible"] = False
                    camp_f["campaign_state"] = camp_f["campaign_state"] or "technical_test"
                verdict.update(camp_f)
                verdicts_all.append(verdict)
                if status == "approved":
                    log_line(f"⚡ AUTO-APPROUVÉ {verdict['candidate_id']} "
                             f"(score {verdict['score']}) → trail immédiat")
                elif status == "pending_warsmith":
                    log_line(f"🚪 En attente Warsmith : {verdict['candidate_id']} "
                             f"(score {verdict['score']}) — valide depuis le board")

                # 5. Candidat + verdict écrits immédiatement (crash-safe)
                write_outputs(cfg, moments_all, candidats_live + [cand],
                              scored_all, verdicts_all, clips_all, channels, radar)

    except KeyboardInterrupt:
        log_line("🛑 Interrompu — flush final")
    finally:
        # Snapshot AVANT l'arrêt du radar : sinon connected=false dans le statut final
        write_status(channels, radar, moments_all, verdicts_all, clips_all,
                     deadline, stream_started, final=True, cfg=cfg)
        radar.stop()
        write_outputs(cfg, moments_all, candidats_live, scored_all, verdicts_all,
                      clips_all, channels, radar, final=True)
        log_line(f"═══ Session terminée : {len(moments_all)} moments, "
                 f"{len(clips_all)} clips Helix, "
                 f"{sum(1 for v in verdicts_all if v['status'] == 'approved')} auto-approuvés ═══")


def build_candidate(sig, moment, cfg):
    """Fenêtre candidat au même schéma que cmd_detect (f00b_vox.py)."""
    pre = cfg.get("pre_roll_sec", 2.0)
    post = cfg.get("post_roll_sec", 2.0)
    d_cible = cfg.get("duree_cible_sec", 30)
    d_max = cfg.get("duree_max_sec", 60)

    def pt(t):
        h, m, s = t.split(":")
        return int(h) * 3600 + int(m) * 60 + int(s)

    start = max(0, pt(sig["start"]) - pre)
    end = pt(sig["end"]) + post
    dur = end - start
    if dur < d_cible:
        extend = d_cible - dur
        end += extend * 0.7
        start = max(0, start - extend * 0.3)
    if end - start > d_max:
        end = start + d_max

    cid = vox.candidate_id(moment["channel"] + str(moment.get("detected_at")), start)
    return {
        "candidate_id": cid,
        "start_sec": round(start, 2),
        "end_sec": round(end, 2),
        "duration_sec": round(end - start, 2),
        "signal_type": sig["type"],
        "signal_intensity": sig["intensity"],
        "signal_start": sig["start"],
    }


# ─── Scoring live calibré (la vraie force du pic, plus de profil fixe) ───────

def _spike_ratio(moment):
    """Ratio réel du pic : rate du chat / baseline EMA."""
    return moment.get("rate", 0) / max(moment.get("baseline", 0.5) or 0.5, 0.5)


def _hysteria_count(hot_words):
    """Nombre de mots d'hystérie collective (www*, KEKW, LUL, Pog*, lol…)."""
    import re
    pat = re.compile(r"^(w{2,}|kekw|lul|lmao|pog|lol|ha{2,}|omg|woa|no ?way)", re.I)
    return sum(1 for w in (hot_words or []) if pat.match(str(w)))


def compute_score_live(cand, moment):
    """
    Scoring VOX adapté au live : chaque critère est alimenté par la FORCE RÉELLE
    du pic (ratio vs baseline, mots chauds, clip_pressure, durée) au lieu d'un
    profil fixe. Miroir exact du bloc bonus/malus de vox.compute_score
    (moteur VOD de main intact — seule la couche live calcule différemment).
    """
    w = dict(vox.WEIGHTS)
    ratio = _spike_ratio(moment)
    pressure = moment.get("clip_pressure", 0) or 0
    hot = moment.get("hot_words") or []
    hysteria = _hysteria_count(hot)
    dur = cand.get("duration_sec", 30)

    # Intensité honnête : ratio 6+ → 1.0, ratio 3 → 0.5, ratio 1.5 → 0.25
    intensity = min(1.0, round(ratio / 6.0, 2))

    raw = {}
    # hook_force ← ratio réel (×6+ = mur qui tombe)
    if ratio >= 6:
        raw["hook_force"] = 10.0
    elif ratio >= 4:
        raw["hook_force"] = 8.5
    elif ratio >= 3:
        raw["hook_force"] = 7.5
    elif ratio >= 2:
        raw["hook_force"] = 6.0
    else:
        raw["hook_force"] = 4.5
    # emotion ← hystérie collective du chat
    if hysteria >= 3:
        raw["emotion"] = 9.5
    elif hysteria >= 1:
        raw["emotion"] = 8.0
    else:
        raw["emotion"] = 6.0 if ratio >= 3 else 5.0
    # clarity ← pic massif ET/OR demandé par le chat
    raw["clarity"] = 8.5 if (pressure >= 2 or ratio >= 4) else 6.5
    # quotability ← le chat réclame le clip
    if pressure >= 3:
        raw["quotability"] = 9.5
    elif pressure >= 1:
        raw["quotability"] = 7.5
    else:
        raw["quotability"] = 5.0 if ratio >= 4 else 4.0
    # timing ← durée de la fenêtre captée
    if 20 <= dur <= 40:
        raw["timing"] = 8.0
    elif 10 <= dur <= 50:
        raw["timing"] = 7.0
    else:
        raw["timing"] = 5.5
    # format_fit ← 9:16 toujours faisable, durée idéale courte
    raw["format_fit"] = 7.5 if dur <= 40 else (6.5 if dur <= 55 else 5.5)

    base = sum(w[k] * raw[k] for k in raw)

    # Bonus / malus — miroir de vox.compute_score, alimenté par l'intensité honnête
    bonuses, maluses = [], []
    if dur > 60:
        maluses.append({"rule": "duree_gt_60", "delta": -3.0})
    if dur < 15:
        maluses.append({"rule": "duree_lt_15", "delta": -3.0})
    if intensity >= 0.9:
        bonuses.append({"rule": "moment_unique", "delta": 1.5})
    if intensity >= 0.7:
        bonuses.append({"rule": "haute_intensite", "delta": 1.0})

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
        "signal_intensity": intensity,
        "spike_ratio": round(ratio, 2),
        "clip_pressure": pressure,
        "hot_words": hot[:6],
        "status": "scored",
    }


def _recent_scored(scored_all, verdicts):
    """10 derniers scores avec détail des critères (alimente le Scoreur du board)."""
    by_id = {s["candidate_id"]: s for s in scored_all}
    out = []
    for v in verdicts[-10:]:
        s = by_id.get(v.get("candidate_id"), {})
        out.append({
            "candidate_id": v.get("candidate_id"),
            "final_score": v.get("score"),
            "raw_scores": s.get("raw_scores", {}),
            "signal_intensity": s.get("signal_intensity"),
            "spike_ratio": s.get("spike_ratio"),
            "clip_pressure": s.get("clip_pressure"),
            "hot_words": s.get("hot_words", []),
            "channel": v.get("channel"),
            "status": v.get("status"),
            "campaign_eligible": v.get("campaign_eligible"),
            "detected_at": v.get("detected_at"),
        })
    return out


# ─── Écritures (crash-safe : chaque tick laisse des fichiers valides) ───────
def write_outputs(cfg, moments, candidats, scored_all, verdicts, clips,
                  channels, radar, final=False):
    approved = [v for v in verdicts if v["status"] == "approved"]

    save_json(OUT_DIR / "live_moments.json", {
        "generated_at": datetime.now().isoformat(),
        "mode": "v2-live",
        "total_moments": len(moments),
        "moments": moments,
    })
    save_json(OUT_DIR / "candidats_live.json", {
        "generated_at": datetime.now().isoformat(),
        "total_candidats": len(candidats),
        "candidats": candidats,
    })
    scored_sorted = sorted(scored_all, key=lambda s: s["final_score"], reverse=True)
    save_json(OUT_DIR / "scoring_live.json", {
        "generated_at": datetime.now().isoformat(),
        "formula": "score = Σ(weight_i × criteria_i) + bonus - malus (moteur VOX VOD, inchangé)",
        "total_scored": len(scored_sorted),
        "total_accepted": sum(1 for s in scored_sorted if s["status"] == "scored"),
        "total_auto_rejected": sum(1 for s in scored_sorted if s["status"] == "auto_rejected"),
        "candidates": scored_sorted,
    })
    save_json(OUT_DIR / "gate_live.json", {
        "generated_at": datetime.now().isoformat(),
        "type": "SOUS-FREGATE_GATE_HYBRIDE",
        "validateur": "auto (seuils) + Warsmith (file d'attente)",
        "regle_d_or": "Le live n'attend pas : excellents candidats auto-approuvés, le reste en file.",
        "campaign": cfg.get("_campaign", {}),
        "total_candidates": len(verdicts),
        "approved": len(approved),
        "pending_warsmith": sum(1 for v in verdicts if v["status"] == "pending_warsmith"),
        "rejected": sum(1 for v in verdicts if v["status"] == "rejected"),
        "verdicts": verdicts,
    })

    # trail.json — même schéma que le mode VOD → F04/F06 ne voient aucune différence
    trails = []
    for v in approved:
        start, end = v["start_sec"], v["end_sec"]
        duration = end - start
        hook_end = start + min(3, duration * 0.15)
        trails.append({
            "candidate_id": v["candidate_id"],
            "start_sec": round(start, 2),
            "end_sec": round(end, 2),
            "duration_sec": round(duration, 2),
            "start_time": vox.fmt_time(start),
            "end_time": vox.fmt_time(end),
            "score": v["score"],
            "hook_window": {"start_sec": round(start, 2), "end_sec": round(hook_end, 2),
                            "note": "zone hook : 0-3s ou premier 15%"},
            "internal_cuts": [],
            "cut_count": 0,
            "channel": v.get("channel"),
            "helix_clip_id": v.get("helix_clip_id"),
            "trail_spec": {"format": "9:16", "export_quality": "1080x1920",
                           "stream_copy": True,
                           "note": "Clip Helix deja serveur-side ou segment VOD a extraire"},
        })
    save_json(OUT_DIR / "trail.json", {
        "generated_at": datetime.now().isoformat(),
        "mode": "v2-live",
        "total_trails": len(trails),
        "trails": trails,
        "next_step": "F04_COPYWRITER / pur_montage_pipeline reçoivent trail.json (identique VOD)",
    })

    save_json(OUT_DIR / "helix_clips.json", {
        "generated_at": datetime.now().isoformat(),
        "total_clips": len(clips),
        "clips": [
            {"channel": c["moment"]["channel"], "detected_at": c["moment"]["detected_at"],
             **c["clip"]}
            for c in clips
        ],
    })

    if final:
        log_line(f"🏁 Finale : {len(trails)} trails prêts → OUT/trail.json")


def write_status(channels, radar, moments, verdicts, clips, deadline,
                 stream_started, final=False, cfg=None):
    save_json(OUT_DIR / "live_status.json", {
        "generated_at": datetime.now().isoformat(),
        "mode": "v2-live",
        "session_final": final,
        "seconds_remaining": max(0, int(deadline - time.time())),
        "campaign": cfg.get("_campaign", {}),
        "channels": radar.snapshot(),
        "counters": {
            "moments": len(moments),
            "helix_clips": len(clips),
            "approved": sum(1 for v in verdicts if v["status"] == "approved"),
            "pending_warsmith": sum(1 for v in verdicts if v["status"] == "pending_warsmith"),
            "rejected": sum(1 for v in verdicts if v["status"] == "rejected"),
        },
        "gate_queue": [v for v in verdicts if v["status"] == "pending_warsmith"][-12:],
        "recent_moments": moments[-8:],
        "recent_scored": _recent_scored(scored_all, verdicts),
        "clips": [
            {"clip_id": c["clip"].get("clip_id"), "url": c["clip"].get("url"),
             "channel": c["moment"]["channel"], "detected_at": c["moment"].get("detected_at"),
             "score": next((v["score"] for v in verdicts
                            if v.get("detected_at") == c["moment"].get("detected_at")
                            and v.get("channel") == c["moment"].get("channel")), None)}
            for c in clips
        ][-20:],
        "stream_started": {ch: stream_started.get(ch) for ch in channels},
    })


def main():
    cfg_file = IN_DIR / "live_input.json"
    if not cfg_file.exists():
        log_line("❌ IN/live_input.json introuvable. Copier IN/live_input.example.json.")
        sys.exit(1)
    cfg = load_json(cfg_file)
    log_line("═══ F00B_VOX — LIVE (v2-live) ═══")
    run_session(cfg)


if __name__ == "__main__":
    main()
