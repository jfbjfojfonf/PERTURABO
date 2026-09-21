#!/usr/bin/env python3
"""F06_DIRECTOR — Le Directeur de Montage (PUR viral). Consomme la doctrine ARCHIVUM."""
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent.parent
ARCHIVUM = BASE / "ARCHIVUM"
MONTAGE = ARCHIVUM / "montage"
PATTERNS_DIR = MONTAGE / "patterns"
RULES_DIR = MONTAGE / "rules"
F06_OUT = BASE / "F06_DIRECTOR" / "OUT"

VIRAL_PATTERNS = [
    "zoom_patterns.json", "cut_patterns.json", "audio_presets.json",
    "energy_patterns.json", "anti_detection.json", "text_overlay_patterns.json",
    "pur_montage_rules.json", "hooks_pur.json",
]
_EMOTION = {
    "punchline": "shock", "trigger_word": "outrage", "energy": "hype",
    "chat_spike": "shock", "mixed": "intrigue",
}
_DISC = {
    "anyways", "anyway", "but", "so", "okay", "ok", "wait", "actually",
    "then", "however", "meanwhile", "besides", "look", "now", "and then",
    "the thing is", "how so",
}

def _clean_word(w):
    return (w or "").strip().lower().rstrip(",.!?;:\"'…-")

def _word_at(word_timings, t):
    anchor = ""
    for w in word_timings:
        try:
            s = float(w.get("start", 0)); e = float(w.get("end", s))
        except (TypeError, ValueError):
            continue
        if s <= t <= e:
            return (w.get("word") or "").strip()
        if s <= t:
            anchor = (w.get("word") or "").strip()
    return anchor

def _beat_analysis(word_timings, duration):
    breaths, strongs, ideas = [], [], []
    for i in range(len(word_timings) - 1):
        w = word_timings[i]; nxt = word_timings[i + 1]
        try:
            s = float(w.get("start", 0)); e = float(w.get("end", s))
            ns = float(nxt.get("start", 0))
        except (TypeError, ValueError):
            continue
        gap = round(ns - e, 2)
        if gap >= 0.55:
            breaths.append(round(e, 2))
            if gap >= 1.0:
                strongs.append((round(e, 2), gap))
        if _clean_word(w.get("word", "")) in _DISC:
            ideas.append(round(s, 2))
    strongs.sort(key=lambda x: -x[1])
    third = duration * 0.66
    late = [(t, g) for (t, g) in strongs if t >= third]
    if late:
        punch = max(late, key=lambda x: x[1])[0]
    elif strongs:
        punch = strongs[0][0]
    else:
        later = [float(w.get("start", 0)) for w in word_timings
                 if float(w.get("start", 0)) >= third]
        punch = round(later[0], 2) if later else round(duration * 0.85, 2)
    return breaths, strongs, ideas, punch

def _mk_zoom(kind, t, word_timings):
    if kind == "snap_zoom":
        z = {"type": "snap_zoom", "intensity_pct": "115-130%",
             "duration_in": "1 frame (instantane)", "duration_out": "fade 0.3s",
             "easing": "NONE", "target": "centre du visage du speaker",
             "sfx_sync": "boom (60%) + flash blanc subtil (1-2 frames)"}
    else:
        z = {"type": "brutal_impact", "intensity_pct": "108-115%",
             "duration_in": "0.1s (2-3 frames a 30fps)", "duration_out": "0.1s (retour immediat)",
             "easing": "NONE", "target": "centre du visage du speaker",
             "sfx_sync": "impact (50-60%) synchronise frame-exacte"}
    z["moment_sec"] = t
    z["word_anchor"] = _word_at(word_timings, t)
    return z

def _word_aligned_cut_plan(word_timings, duration):
    breaths, _strongs, ideas, punch = _beat_analysis(word_timings, duration)
    cuts = []
    for t in breaths[:8]:
        cuts.append({"type": "breath_cut", "moment_sec": t,
                     "word_anchor": _word_at(word_timings, t),
                     "technique": "couper exactement sur la respiration du speaker"})
    for t in ideas[:3]:
        cuts.append({"type": "idea_cut", "moment_sec": t,
                     "word_anchor": _word_at(word_timings, t),
                     "technique": "couper quand le speaker change d'idee"})
    cuts.append({"type": "smash_cut", "moment_sec": punch,
                 "word_anchor": _word_at(word_timings, punch),
                 "technique": "cut brutal zero transition sur la punchline",
                 "sfx_sync": "whoosh_fast/impact"})
    cuts.sort(key=lambda c: c["moment_sec"])
    return cuts

def _word_aligned_zoom_plan(word_timings, duration, emotion):
    shock = emotion in ("shock", "outrage")
    _breaths, strongs, _ideas, punch = _beat_analysis(word_timings, duration)
    zooms = []
    if strongs:
        zooms.append(_mk_zoom("brutal_impact", strongs[0][0], word_timings))
    if shock and punch is not None and (not zooms or abs(punch - zooms[0]["moment_sec"]) > 0.5):
        zooms.append(_mk_zoom("snap_zoom", punch, word_timings))
    if len(strongs) > 1 and len(zooms) < 2:
        zooms.append(_mk_zoom("brutal_impact", strongs[1][0], word_timings))
    zooms.sort(key=lambda z: z["moment_sec"])
    return zooms[:3]


def _load_json(path):
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def load_doctrine():
    doc = {}
    for name in VIRAL_PATTERNS:
        j = _load_json(PATTERNS_DIR / name)
        if j:
            doc[name.replace(".json", "")] = j
    pmr = _load_json(PATTERNS_DIR / "pur_montage_rules.json")
    doc["global_rules"] = pmr.get("global_rules", {})
    doc["universal"] = pmr.get("universal_ingredients", {})
    return doc

def load_platform_rules(platform):
    rules = {"platform": platform, "max_duration_sec": 60, "min_duration_sec": 15,
             "hook_duration_sec": 3, "aspect_ratio": "9:16", "resolution": "1080x1920"}
    p = RULES_DIR / f"{platform}.md"
    if not p.exists():
        return rules
    text = p.read_text(encoding="utf-8")
    def num(label, default):
        m = re.search(re.escape(label) + r"\D*(\d+)", text)
        return int(m.group(1)) if m else default
    rules["max_duration_sec"] = num("Duree max", 60)
    m = re.search(r"(\d+)\s*[:x]\s*(\d+)", text)
    if m:
        rules["aspect_ratio"] = "%s:%s" % (m.group(1), m.group(2))
    return rules

def normalize_segment(seg):
    start = seg.get("start_sec") if seg.get("start_sec") is not None else seg.get("start")
    end = seg.get("end_sec") if seg.get("end_sec") is not None else seg.get("end")
    dur = seg.get("duration_sec")
    if dur is None and start is not None and end is not None:
        dur = round(float(end) - float(start), 1)
    return {
        "id": seg.get("id") or seg.get("angle_id") or seg.get("candidate_id") or "unknown",
        "source_url": seg.get("source_url") or seg.get("vod_url") or "",
        "start_sec": start, "end_sec": end,
        "duration_sec": dur or 30,
        "signal_type": seg.get("signal_type") or "mixed",
        "signal_intensity": float(seg.get("signal_intensity", 0.5) or 0.5),
        "transcript_segment": (seg.get("transcript_segment") or seg.get("top_words") or seg.get("text") or ""),
        "word_timings": seg.get("word_timings") or [],
    }

def _emotion_of(segment):
    return _EMOTION.get(segment.get("signal_type"), "intrigue")

def _zoom_plan(duration, emotion, intensity):
    shock = emotion in ("shock", "outrage")
    zooms = []
    for ratio in (0.3, 0.6, 0.9):
        t = round(duration * ratio, 1)
        kind = "snap_zoom" if (shock and ratio >= 0.6) else "brutal_impact"
        zooms.append({
            "type": kind, "moment_sec": t,
            "intensity_pct": "115-130%" if kind == "snap_zoom" else "108-115%",
            "duration_in": "1 frame (instantane)" if kind == "snap_zoom" else "0.1s (2-3 frames a 30fps)",
            "duration_out": "fade 0.3s" if kind == "snap_zoom" else "0.1s (retour immediat)",
            "easing": "NONE", "target": "centre du visage du speaker",
            "sfx_sync": ("boom (60%) + flash blanc subtil (1-2 frames)" if kind == "snap_zoom"
                         else "impact (50-60%) synchronise frame-exacte"),
        })
    return zooms

def _cut_plan(duration, emotion, intensity):
    cuts = []
    t = 0.0
    while t < duration:
        cuts.append({"type": "breath_cut", "moment_sec": round(t, 1),
                     "technique": "couper exactement sur la respiration du speaker"})
        t += 3.0
    cuts.append({"type": "smash_cut", "moment_sec": round(duration * 0.85, 1),
                 "technique": "cut brutal zero transition sur la punchline", "sfx_sync": "whoosh_fast/impact"})
    cuts.append({"type": "idea_cut", "moment_sec": round(duration * 0.5, 1),
                 "technique": "couper quand le speaker change d'idee"})
    return cuts

def _audio_plan(doctrine, emotion):
    hierarchy = doctrine.get("audio_presets", {}).get("volume_hierarchy", {})
    return {
        "principle": "La voix du speaker est TOUJOURS prioritaire.",
        "volume_hierarchy": hierarchy,
        "sfx_events": [
            {"name": "whoosh", "when": "transition/changement de plan", "volume": "-12dB"},
            {"name": "impact", "when": "au moment exact du zoom brutal", "volume": "-8dB", "sync": "frame exacte"},
            {"name": "pop", "when": "apparition texte/chiffre", "volume": "-10dB"},
            {"name": "boom", "when": "moment de shock/twist", "volume": "-8dB", "sync": "snap_zoom + flash"},
        ],
        "music_be": {"enabled": False, "note": "pas de musique sur le hook (0-3s)"},
    }

def _anti_detection_plan(doctrine):
    return {
        "obligatoire": True,
        "principe": "Empreinte digitale unique par clip.",
        "techniques": [
            {"name": "mirror", "action": "Flip horizontal sur CHAQUE clip"},
            {"name": "speed", "action": "vitesse 1.02x-1.08x", "optimal": "1.05x"},
            {"name": "crop", "action": "crop 2-3%", "optimal": "2.5%"},
            {"name": "sfx_background_layer", "action": "bruit de fond leger continu", "volume": "10-15%"},
            {"name": "color_shift", "action": "variation de teinte 2-5 degres"},
            {"name": "trim", "action": "1-2 frames trimees au debut/fin"},
        ],
    }

def _text_plan(doctrine, text_payload, segment, platform):
    safe = doctrine.get("text_overlay_patterns", {}).get("safe_zones", {}).get(platform, {})
    overlay_title = text_payload.get("overlay_title") or text_payload.get("title") or ""
    overlay_lines = text_payload.get("overlay_lines") or 2
    transcript = segment.get("transcript_segment", "")
    return {
        "main_title": {
            "text": overlay_title,
            "font": "Montserrat ExtraBold / Bebas Neue (800-900)",
            "fallback": "Arial Black, Impact",
            "color": "#FFFFFF", "accent": "#FFD700 (jaune) ou #00FF88 (vert)",
            "outline": "#000000 (3-4px)", "shadow": "drop-shadow 2px 2px 4px rgba(0,0,0,0.8)",
            "max_lines": overlay_lines, "position": "haut vers le centre", "font_size": "64-72px",
            "animation": "pop_in (scale 0 -> 110% -> 100% en 0.2s)", "visible": "toute la duree",
        },
        "captions": {
            "source": "TRANSCRIPT du speech (word-by-word)", "text_sample": transcript[:300],
            "font": "Montserrat Bold / Poppins Bold (700)", "color": "blanc outline sombre",
            "highlight": "mots-cles en accent (jaune/vert)", "animation": "word_by_word",
        },
        "safe_zones": safe,
    }

def _energy_curve(duration, emotion):
    def fmt(s): return "%d:%02d" % (int(s)//60, int(s)%60)
    if emotion in ("shock", "outrage"):
        return [{"moment": "0:00", "energy": 100}, {"moment": fmt(duration*0.2), "energy": 70},
                {"moment": fmt(duration*0.5), "energy": 90}, {"moment": fmt(duration*0.85), "energy": 100},
                {"moment": fmt(duration), "energy": 60}]
    return [{"moment": "0:00", "energy": 100}, {"moment": fmt(duration*0.3), "energy": 60},
            {"moment": fmt(duration*0.6), "energy": 80}, {"moment": fmt(duration), "energy": 50}]

def _caviar_owned(caviar):
    """Ce que la partition caviar possède : liste stable pour tests/journal."""
    return {
        "cuts": True, "zooms": True, "sfx_events": True,
        "mirror": True, "speed": True, "crop": True,
        "panel_render": True, "audio_duck": True,
    }


def _caviar_binding(caviar, source_path=""):
    """Traçabilité : la partition caviar a commande cet output."""
    import hashlib
    checksum = ""
    if source_path and os.path.exists(source_path):
        h = hashlib.sha256()
        with open(source_path, "rb") as fh:
            h.update(fh.read())
        checksum = h.hexdigest()[:16]
    src = caviar.get("source", {})
    return {
        "bound": True,
        "run_id": src.get("run_id", "unknown"),
        "candidate_id": src.get("candidate_id", "unknown"),
        "style": caviar.get("style", "unknown"),
        "manifest_path": source_path,
        "manifest_sha256_16": checksum,
        "hierarchy": "F00D commande — F06 execute le reste (les cuts/zooms/SFX "
                     "et l'anti-detection de base appartiennent a la partition)",
    }


def _caviar_panel_events(caviar):
    """Extraire les entrées de panneaux (flash+SFX) depuis la partition.
    SFX UNIQUEMENT a l'entree des panneaux — doctrine broll_trio."""
    panels = []
    for ev in (caviar.get("events", {}).get("broll") or []):
        if ev.get("kind") != "broll_blur":
            continue
        entry = {
            "panel_id": ev.get("broll_id", "BLUR"),
            "at_sec": ev.get("start_sec"),
            "duration_frames": ev.get("duration_frames"),
            "crop_zoom": ev.get("crop_zoom"),
            "blur_radius_px": ev.get("blur_radius_px"),
            "panel": ev.get("panel", "vertical_text_overlay"),
            "emotion_requested": ev.get("emotion_requested", ""),
            "entry_flash": bool(ev.get("entry_flash")),
            "sfx": ev.get("sfx", "impact") if ev.get("entry_flash") else None,
            "owned_by": "caviar",
        }
        panels.append(entry)
    return panels


def _caviar_audio_duck(caviar):
    """Duck audio au climax — calé par la partition, pas recalculé."""
    ducks = caviar.get("events", {}).get("smash_audio") or []
    out = []
    for d in ducks:
        out.append({"at_sec": d.get("at_sec"), "duck_db": d.get("duck_db"),
                    "duration_sec": d.get("duration_sec"), "owned_by": "caviar"})
    return out


def _caviar_energy_curve(caviar, duration):
    """Courbe d'énergie alignée sur la partition (climax caviar), pas générique."""
    curve = caviar.get("narrative", {}).get("energy_curve") or ["rise", "peak", "fall"]
    climaxes = caviar.get("narrative", {}).get("is_climax") or []
    peak_at = climaxes[0] if climaxes else round(duration * 0.5, 3)
    shape = {"rise": (55, 85), "peak": (95, 100), "fall": (70, 45)}
    out = []
    for i, phase in enumerate(curve):
        lo, hi = shape.get(phase, (60, 90))
        out.append({"phase": phase, "from_sec": round(duration * i / len(curve), 2),
                    "to_sec": round(duration * (i + 1) / len(curve), 2),
                    "energy": hi if phase == "peak" else lo})
    out.append({"note": "climax_caviar_at_sec", "value": peak_at})
    return out


def _anti_detection_complementary(doctrine):
    """Seulement ce que F00D ne possède PAS : couche sonore, teinte, trim.
    miroir/vitesse/crop sont owned_by caviar — jamais dupliqués ici."""
    return {
        "obligatoire": True,
        "principe": "Complément de la partition caviar (miroir/vitesse/crop déjà possédés par F00D).",
        "techniques": [
            {"name": "sfx_background_layer", "action": "bruit de fond léger continu", "volume": "10-15%"},
            {"name": "color_shift", "action": "variation de teinte 2-5 degrés"},
            {"name": "trim", "action": "1-2 frames trimées au début/fin"},
        ],
        "owned_by_caviar": ["mirror", "speed", "crop"],
    }


def _generate_caviar_bound(caviar, seg, text_payload, context, doctrine,
                           duration, rules, now, manifest_path=""):
    hook_dur = int(rules.get("hook_duration_sec", 3))
    """Mode SOUMIS : F00D commande, F06 exécute ce qui reste.

    La partition possède : cuts, zooms, SFX, miroir/vitesse/crop, rendu des
    panneaux (blur), duck audio au climax. F06 garde : text_overlays (overlay
    F04 + captions), courbe d'énergie RECALÉE sur le climax caviar, hiérarchie
    audio SANS aucun événement SFX, outro fade/pas de CTA, compliance,
    anti-détection COMPLÉMENTAIRE (couche sonore/teinte/trim).
    """
    style = caviar.get("style", "unknown")
    platform = context.get("platform", "youtube_shorts")
    panels = _caviar_panel_events(caviar)
    duck = _caviar_audio_duck(caviar)
    # Hook : la partition gagne — un panneau posé à ~0s apparaît à 0s.
    panel_at_zero = any(p.get("at_sec") is not None and float(p["at_sec"]) <= 1.0
                        for p in panels)
    first_panel_at = panels[0]["at_sec"] if panels else None
    overlay_title = (text_payload.get("overlay_title")
                     or caviar.get("overlay", {}).get("text", ""))

    instructions = {
        "metadata": {"generated_at": now, "generator": "F06_DIRECTOR",
                     "version": "3.0.0-caviar-bound",
                     "mode": "caviar_bound",
                     "doctrine_source": "ARCHIVUM/montage/patterns/ + manifeste caviar",
                     "campaign_id": caviar.get("source", {}).get("candidate_id", context.get("campaign_id", "unknown")),
                     "angle_id": context.get("angle_id", seg.get("id", "unknown")),
                     "segment_id": seg.get("id", "unknown"),
                     "style": style},
        "caviar_binding": _caviar_binding(caviar, manifest_path),
        "caviar_owned": _caviar_owned(caviar),
        "segment": {"source_url": seg["source_url"], "start_sec": seg["start_sec"],
                    "end_sec": seg["end_sec"], "duration_sec": duration,
                    "signal_type": seg["signal_type"],
                    "signal_intensity": seg["signal_intensity"],
                    "emotion": seg.get("emotion") or context.get("emotion") or _emotion_of(seg)},
        "hook": {
            "duration_sec": hook_dur,
            "philosophy": ("la partition gagne : panneau blur posé dès l'entrée "
                           "(hook climax_first) — la philosophie « visage d'abord » s'efface"
                           if panel_at_zero else
                           "0-3s : visage speaker, PAS de B-roll, voix claire"),
            "first_panel_at_sec": first_panel_at,
            "panel_at_zero": panel_at_zero,
        },
        "body": {
            "duration_sec": round(duration, 1),
            "note": "aucun cut/zoom planifiés ici — F00D possède le geste et le rythme",
            "cuts": [],
            "zooms": [],
            "panels": panels,
            "audio_duck": duck,
            "text_overlays": _text_plan(doctrine, {
                "overlay_title": overlay_title,
                "overlay_lines": text_payload.get("overlay_lines", 2),
            }, seg, platform),
            "audio": {
                "principle": "La voix du speaker est TOUJOURS prioritaire.",
                "volume_hierarchy": doctrine.get("audio_presets", {}).get("volume_hierarchy", {}),
                "sfx_events": [],
                "sfx_note": "SFX possédés par la partition — UNIQUEMENT aux entrées de panneaux (voir body.panels[].sfx)",
                "music_be": {"enabled": False, "note": "pas de musique sur le hook (0-3s)"},
            },
            "energy_curve": _caviar_energy_curve(caviar, duration),
            "pacing": caviar.get("narrative", {}).get("pacing_note", "rapide — aucun temps mort"),
        },
        "outro": {"duration_sec": 1, "type": "fade_to_black",
                  "note": "PAS de CTA en PUR — finir sur la chute"},
        "anti_detection": _anti_detection_complementary(doctrine),
        "platform_rules": rules,
        "style": {"pacing": "fast", "energy_level": "high",
                  "color_palette": "contraste fort — blanc/accent jaune",
                  "text_treatment": "bold",
                  "panel_render": "crop-zoom + flou + panneau vertical : exécutés par le bras armé selon body.panels"},
        "compliance": {"disclosure": "#ad", "submit_deadline_min": 60, "platform": platform},
    }
    return instructions


def generate_montage_instructions(segment, text_payload, context, caviar_manifest=None,
                                  caviar_manifest_path=""):
    doctrine = load_doctrine()
    seg = normalize_segment(segment)
    platform = context.get("platform", "youtube_shorts")
    market = context.get("market", "us_young_english")
    emotion = context.get("emotion") or _emotion_of(seg)
    rules = load_platform_rules(platform)
    duration = float(seg["duration_sec"] or rules.get("max_duration_sec", 30))
    hook_dur = int(rules.get("hook_duration_sec", 3))
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    if caviar_manifest is not None:
        return _generate_caviar_bound(caviar_manifest, seg, text_payload, context,
                                      doctrine, duration, rules, now,
                                      caviar_manifest_path)

    # --- Mode legacy (aucune partition) : inchangé, warning si style blur demandé ---
    if (context.get("style") or "").lower() == "blur":
        raise ValueError("style blur exige un caviar_manifest — F00D commande le rendu, "
                         "pas de fallback silencieux (doctrine des gates).")
    word_timings = seg.get("word_timings") or []
    if word_timings:
        cuts = _word_aligned_cut_plan(word_timings, duration)
        zooms = _word_aligned_zoom_plan(word_timings, duration, emotion)
    else:
        cuts = _cut_plan(duration, emotion, seg["signal_intensity"])
        zooms = _zoom_plan(duration, emotion, seg["signal_intensity"])
    return {
        "metadata": {"generated_at": now, "generator": "F06_DIRECTOR", "version": "2.0.0-viral",
                     "doctrine_source": "ARCHIVUM/montage/patterns/",
                     "campaign_id": context.get("campaign_id", "unknown"),
                     "angle_id": context.get("angle_id", seg.get("id", "unknown")),
                     "segment_id": seg.get("id", "unknown")},
        "segment": {"source_url": seg["source_url"], "start_sec": seg["start_sec"],
                    "end_sec": seg["end_sec"], "duration_sec": duration,
                    "signal_type": seg["signal_type"], "signal_intensity": seg["signal_intensity"],
                    "emotion": emotion},
        "hook": {"duration_sec": hook_dur,
                 "philosophy": "0-3s : visage speaker, PAS de B-roll, voix claire",
                 "zoom": {"type": "brutal_impact", "intensity": "108-115%", "easing": "NONE"}},
        "body": {"duration_sec": round(duration - hook_dur, 1),
                 "cuts": cuts,
                 "zooms": zooms,
                 "text_overlays": _text_plan(doctrine, text_payload, seg, platform),
                 "audio": _audio_plan(doctrine, emotion),
                 "energy_curve": _energy_curve(duration, emotion),
                 "pacing": "rapide — aucun temps mort"},
        "outro": {"duration_sec": 1, "type": "fade_to_black",
                  "note": "PAS de CTA 'Follow for more' en PUR — finir sur la chute"},
        "anti_detection": _anti_detection_plan(doctrine),
        "platform_rules": rules,
        "style": {"pacing": "fast", "energy_level": "high",
                  "color_palette": "contraste fort — blanc/accent jaune", "text_treatment": "bold"},
        "compliance": {"disclosure": "#ad", "submit_deadline_min": 60, "platform": platform},
    }

def main():
    if len(sys.argv) >= 4:
        seg = _load_json(Path(sys.argv[1]))
        payload = _load_json(Path(sys.argv[2]))
        ctx = _load_json(Path(sys.argv[3]))
        caviar = None
        caviar_path = ""
        if len(sys.argv) >= 5:
            caviar_path = sys.argv[4]
            caviar = _load_json(Path(caviar_path))
            if not caviar:
                print(f"[F06] ERREUR: manifeste caviar illisible: {caviar_path}")
                sys.exit(2)
        F06_OUT.mkdir(parents=True, exist_ok=True)
        instructions = generate_montage_instructions(seg, payload, ctx,
                                                     caviar_manifest=caviar,
                                                     caviar_manifest_path=caviar_path)
        out = F06_OUT / "montage_instructions.json"
        out.write_text(json.dumps(instructions, ensure_ascii=False, indent=2), encoding="utf-8")
        mode = instructions.get("metadata", {}).get("mode", "legacy")
        print(f"[F06] Instructions ({mode}) -> {out}")
    else:
        print("Usage: director.py <segment.json> <text_payload.json> <context.json> [caviar_manifest.json]")
        sys.exit(1)

if __name__ == "__main__":
    main()
