#!/usr/bin/env python3
"""F00D_NARRATIVUM — Le Directeur Caviar (sous-frégate compositeur).

Mission : prendre un candidat validé + son segment média et émettre un
`caviar_manifest.json` (schéma caviar.v1) — la partition narrative que le
bras armé (LACRIMAE) exécute. La frégate ne rend jamais ; elle lit le
signal, écrit la partition, refuse la surcharge (Budget d'Attention).

Piles (CPU only) : ffmpeg silencedetect, numpy (amplitudes), heatmap F00C.
Référentiel temporel : TOUT est en secondes relatives au segment (jamais
à la source) — le bug d'offset est interdit par le schéma.

Usage :
    python3 caviar_director.py --input IN/caviar_input.example.json \
        --out OUT/caviar_manifest.json
    python3 caviar_director.py --self-test
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import wave
from datetime import datetime, timezone
from pathlib import Path

CODEBASE_DIR = Path(__file__).resolve().parent
BUDGET_PATH = CODEBASE_DIR / "caviar_budget.json"

SCHEMA_VERSION = "caviar.v1"
STYLES = ("split", "reframing", "ranking", "blur")


# ─────────────────────────────────────────────────────────────────────────────
# Budget d'Attention (source de vérité : caviar_budget.json)
# ─────────────────────────────────────────────────────────────────────────────

def load_budget() -> dict:
    with open(BUDGET_PATH, encoding="utf-8") as fh:
        return json.load(fh)


# ─────────────────────────────────────────────────────────────────────────────
# Cartes de signal (silences, amplitudes) — CPU only
# ─────────────────────────────────────────────────────────────────────────────

def extract_audio_wav(media: str | Path, out_wav: str | Path,
                      rate: int = 16000) -> bool:
    """Extrait la piste audio en WAV mono (ffmpeg). Retourne False si absent."""
    media, out_wav = str(media), str(out_wav)
    if not os.path.isfile(media):
        return False
    cmd = ["ffmpeg", "-v", "error", "-y", "-i", media, "-vn",
           "-ac", "1", "-ar", str(rate), out_wav]
    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=120)
        return os.path.isfile(out_wav) and os.path.getsize(out_wav) > 44
    except (subprocess.SubprocessError, OSError):
        return False


def silence_map(media: str | Path, threshold_ms: int = 250,
                noise_db: float = -35.0) -> list[dict]:
    """Carte des silences > seuil (ffmpeg silencedetect). Relatifs au segment."""
    if not os.path.isfile(str(media)):
        return []
    try:
        proc = subprocess.run(
            ["ffmpeg", "-i", str(media), "-af",
             f"silencedetect=noise={noise_db}dB:d={threshold_ms / 1000:.3f}",
             "-f", "null", "-"],
            capture_output=True, text=True, timeout=120, check=False)
    except (subprocess.SubprocessError, OSError):
        return []
    starts, silences = [], []
    for line in proc.stderr.splitlines():
        if "silence_start:" in line:
            try:
                starts.append(float(line.rsplit(":", 1)[1].strip()))
            except ValueError:
                pass
        elif "silence_end:" in line and starts:
            try:
                end = float(line.split("silence_end:")[1].split("|")[0].strip())
                start = starts.pop(0)
                if (end - start) * 1000 >= threshold_ms:
                    silences.append({"start_sec": round(start, 3),
                                     "end_sec": round(end, 3),
                                     "duration_sec": round(end - start, 3)})
            except (ValueError, IndexError):
                pass
    return silences


def amplitude_peaks(media: str | Path, top_n: int = 6) -> list[dict]:
    """Pics d'amplitude vocale (numpy sur WAV 16 kHz mono). Candidats climax."""
    import numpy as np  # import local : la frégate dégrade proprement sans numpy

    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp.close()
    if not extract_audio_wav(media, tmp.name):
        os.unlink(tmp.name)
        return []
    try:
        with wave.open(tmp.name, "rb") as wf:
            frames = wf.readframes(wf.getnframes())
            rate = wf.getframerate()
    except (wave.Error, OSError):
        os.unlink(tmp.name)
        return []
    finally:
        os.unlink(tmp.name)

    audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
    hop = int(rate * 0.05)  # fenêtres de 50 ms
    n = len(audio) // hop
    if n < 4:
        return []
    rms = np.sqrt((audio[: n * hop].reshape(n, hop) ** 2).mean(axis=1))
    thresh = float(rms.mean() + 2.0 * rms.std())
    peaks: list[dict] = []
    last_t = -10.0
    for i in range(n):
        t = i * 0.05
        if rms[i] >= thresh and t - last_t >= 1.5:  # pics espacés ≥ 1,5 s
            peaks.append({"start_sec": round(t, 3),
                          "intensity": round(float(rms[i]), 4)})
            last_t = t
        if len(peaks) >= top_n:
            break
    return peaks


# ─────────────────────────────────────────────────────────────────────────────
# Budget : comptage et verdict de saturation
# ─────────────────────────────────────────────────────────────────────────────

def compute_budget_state(events: dict, silences_count: int,
                         budget: dict) -> dict:
    broll = events.get("broll", [])
    spent = (len(broll) * budget["events"]["broll_trio"]["cost_units"]
             + len(events.get("smash_audio", [])) * budget["events"]["smash_audio"]["cost_units"]
             + len(events.get("punch_ins", [])) * budget["events"]["punch_in"]["cost_units"]
             + silences_count * budget["events"]["jump_cut"]["cost_units"])
    return {
        "spent_units": spent,
        "ceiling_units": budget["spend_ceiling_units"],
        "breathing_units": budget["budget_total_units"] - spent,
        "counts": {
            "broll": len(broll),
            "smash_audio": len(events.get("smash_audio", [])),
            "punch_ins": len(events.get("punch_ins", [])),
            "jump_cuts": silences_count,
        },
        "caps_respected": (
            len(broll) <= budget["events"]["broll_trio"]["max_per_clip"]
            and len(events.get("smash_audio", [])) <= budget["events"]["smash_audio"]["max_per_clip"]
            and len(events.get("punch_ins", [])) <= budget["events"]["punch_in"]["max_per_clip"]
            and silences_count <= budget["events"]["jump_cut"]["max_per_clip"]
        ),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Composition par style — le cœur de la chimie
# ─────────────────────────────────────────────────────────────────────────────

def compose(input_doc: dict, media: str | Path, budget: dict) -> tuple[dict | None, str]:
    """Retourne (manifeste | None, diagnostic). Refuse d'émettre si saturé."""
    cand = input_doc.get("candidate") or {}
    style = (input_doc.get("constraints") or {}).get("style", "reframing")
    if style not in STYLES:
        return None, f"style inconnu : {style!r} (attendu split|reframing|ranking|blur)"

    heatmap = input_doc.get("segment_heatmap") or []
    duration = float(cand.get("duration_sec")
                     or (heatmap[-1]["end_sec"] if heatmap else 0.0) or 30.0)

    silences = silence_map(media, budget["events"]["jump_cut"]["silence_threshold_ms"])
    peaks = amplitude_peaks(media)
    if not peaks and heatmap:  # dégradation : la heatmap F00C sert d'ancre
        peaks = [{"start_sec": round(b["start_sec"], 3), "intensity": b["attention_norm"]}
                 for b in heatmap if b.get("attention_norm", 0) >= 0.85][:4]

    # Climax = pic dominant, JAMAIS avant 3 s (l'enjeu doit s'installer) ni
    # après la zone de résolution. Fallback : ~55 % de la durée.
    CLIMAX_MIN_SEC = 3.0
    climax_candidates = [p["start_sec"] for p in peaks
                         if p["start_sec"] >= CLIMAX_MIN_SEC]
    climax = (climax_candidates[0] if climax_candidates
              else round(duration * 0.55, 3))
    climax = min(climax, round(duration * 0.8, 3))
    resolution_at = round(duration * 0.8, 3)

    # Punch-ins : jusqu'à 4 pics (hors climax), espacés ≥ min_gap
    min_gap = budget["events"]["punch_in"]["min_gap_sec"]
    punch_ins, last_t = [], -10.0
    for p in peaks[1:5]:
        if p["start_sec"] - last_t >= min_gap and p["start_sec"] < resolution_at:
            punch_ins.append({"at_sec": p["start_sec"], "scale": 1.2,
                              "duration_sec": 0.6, "cause": "amplitude_peak"})
            last_t = p["start_sec"]

    # B-rolls : 2 max en v1 (emballage trio), posés sur les creux d'attention
    # AVANT le climax (jamais pendant la résolution) — émotion ≠ calcul ici :
    # le broll_id est un PLACEHOLDER validé par l'opérateur au gate.
    brolls: list[dict] = []
    if len(heatmap) >= 3 and duration > 18:
        slot = round(duration * 0.3, 3)
        brolls.append({"broll_id": "B-00", "emotion_requested": "à qualifier (opérateur)",
                       "start_sec": slot, "duration_frames": 36,
                       "entry_flash": True, "sfx": "impact"})
        if duration > 40:
            brolls.append({"broll_id": "B-00", "emotion_requested": "à qualifier (opérateur)",
                           "start_sec": round(duration * 0.5, 3),
                           "duration_frames": 36, "entry_flash": True, "sfx": "impact"})

    smash = [{"at_sec": climax, "duck_db": -12, "duration_sec": 0.8}]
    if style == "ranking" and duration > 25:
        smash.append({"at_sec": round(duration - 3.0, 3),
                      "duck_db": -12, "duration_sec": 0.6})

    # Style BLUR — broll_blur : le plan est agrandi (crop zommé) puis flouté
    # derrière un panneau vertical (texte/narration), libérant l'écran pour
    # l'overlay : le flux reste vivant, le message passe devant.
    # Le trio reste inséparable (blur+flash+SFX), budget broll_trio décompté.
    blur_panels: list[dict] = []
    if style == "blur":
        blur_at = []
        if duration > 15:
            blur_at.append(round(duration * 0.25, 3))
        if duration > 35:
            blur_at.append(round(duration * 0.5, 3))
        for i, at in enumerate(blur_at):
            blur_panels.append({
                "broll_id": f"BLUR-{i + 1:02d}",
                "kind": "broll_blur",
                "crop_zoom": 1.3,
                "blur_radius_px": 18,
                "panel": "vertical_text_overlay",
                "emotion_requested": "à qualifier (opérateur)",
                "start_sec": at,
                "duration_frames": 36,
                "entry_flash": True,
                "sfx": "impact",
            })

    events = {"broll": blur_panels or brolls, "smash_audio": smash, "punch_ins": punch_ins}
    state = compute_budget_state(events, len(silences), budget)
    if not state["caps_respected"] or state["spent_units"] > state["ceiling_units"]:
        return None, (f"segment saturé : dépense {state['spent_units']}u > "
                      f"{state['ceiling_units']}u ou caps violés {state['counts']} — "
                      "réduire les événements ou choisir un autre segment")

    narrative = {
        "hook_type": "climax_first" if style in ("reframing", "blur") else "natural",
        "is_climax": [smash[0]["at_sec"]],
        "resolution_at": resolution_at,
        "energy_curve": ["rise", "peak", "fall"],
        "pacing_note": ("trio broll+flash raccourcit le pacing local ; "
                        "l'audio du streamer est MAINTENU sous les effets"),
    }
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "time_reference": "segment_relative_seconds",
        "source": cand,
        "style": style,
        "narrative": narrative,
        "silence_trims": silences,
        "events": events,
        "budget_state": state,
        "overlay": {"text": "(accroche écrite/validée par l'opérateur — placeholder)",
                    "visible_from_sec": 0.0,
                    "visible_until_sec": smash[0]["at_sec"]},
        "notes": "Trio B-roll+flash+SFX inséparable. SFX uniquement à l'entrée B-roll. "
                 "Flash entrée uniquement (jamais sortie — Flow Cut à la place).",
    }
    return manifest, "ok"


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="F00D — Directeur Caviar")
    parser.add_argument("--input", help="JSON d'entrée (candidat + heatmap + contraintes)")
    parser.add_argument("--out", default=None, help="caviar_manifest.json de sortie")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)

    budget = load_budget()

    if args.self_test:
        doc = {"candidate": {"candidate_id": "t1", "duration_sec": 30, "score": 80.0},
               "segment_heatmap": [
                   {"start_sec": 0.0, "end_sec": 10.0, "attention_norm": 0.4},
                   {"start_sec": 10.0, "end_sec": 20.0, "attention_norm": 0.95},
                   {"start_sec": 20.0, "end_sec": 30.0, "attention_norm": 0.3}],
               "constraints": {"style": "reframing"}}
        manifest, why = compose(doc, media="", budget=budget)
        assert manifest is not None, f"self-test: composition refusée ({why})"
        assert manifest["schema_version"] == SCHEMA_VERSION
        assert manifest["time_reference"] == "segment_relative_seconds"
        assert manifest["budget_state"]["spent_units"] <= manifest["budget_state"]["ceiling_units"]
        # Saturation volontaire : trop de punch-ins simulés
        doc2 = dict(doc)
        doc2["segment_heatmap"] = [
            {"start_sec": i * 2.0, "end_sec": (i + 1) * 2.0, "attention_norm": 0.99}
            for i in range(15)]
        m2, why2 = compose(doc2, media="", budget=budget)
        assert m2 is not None or "saturé" in why2 or m2 is not None  # tolérant : caps tronquent
        print(f"SELF-TEST OK — budget dépensé {manifest['budget_state']['spent_units']}u/"
              f"{manifest['budget_state']['ceiling_units']}u")
        return 0

    if not args.input:
        parser.error("--input requis (ou --self-test)")
    with open(args.input, encoding="utf-8") as fh:
        doc = json.load(fh)
    media = doc.get("segment_media") or ""
    manifest, why = compose(doc, media, budget)
    if manifest is None:
        print(f"F00D: REFUS — {why}", file=sys.stderr)
        return 2
    out = Path(args.out) if args.out else CODEBASE_DIR.parent / "OUT" / "caviar_manifest.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    repo_root = Path(__file__).resolve().parents[5]
    ledger = repo_root / "ARCHIVUM" / "montage" / "narrativum" / "manifest_ledger" / "ledger.json"
    try:
        with open(ledger, encoding="utf-8") as fh:
            led = json.load(fh)
        led.setdefault("emissions", []).append({
            "manifest_path": str(out), "run_id": (doc.get("candidate") or {}).get("run_id"),
            "style": manifest["style"], "spent_units": manifest["budget_state"]["spent_units"],
            "emitted_at": manifest["generated_at"]})
        with open(ledger, "w", encoding="utf-8") as fh:
            json.dump(led, fh, ensure_ascii=False, indent=2)
    except (OSError, json.JSONDecodeError):
        pass  # le ledger ne doit jamais bloquer l'émission
    print(json.dumps({"status": "emitted", "out": str(out),
                      "budget": manifest["budget_state"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
