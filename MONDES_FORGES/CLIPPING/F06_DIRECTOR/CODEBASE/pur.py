#!/usr/bin/env python3
"""
PUR Mode — Script principal
Extraction de moments viraux depuis des podcasts/long-forms.
Connecté au réseau CLIPPING via ARCHIVUM et EXPORT.
"""

import json
import os
import sys
import argparse
from datetime import datetime
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).parent.parent
IN_DIR = BASE_DIR / "IN"
OUT_DIR = BASE_DIR / "OUT"
ARCHIVUM_DIR = BASE_DIR.parent / "ARCHIVUM"
EXPORT_DIR = BASE_DIR.parent / "EXPORT"

# Ensure dirs exist
OUT_DIR.mkdir(exist_ok=True)


def load_json(path):
    """Load a JSON file."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(data, path):
    """Save data to JSON."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"✅ Saved: {path}")


def cmd_start_siege(args):
    """Initialize a new PUR siege."""
    siege_id = f"PUR-SIEGE-{datetime.now().strftime('%Y%m%dT%H%M%S')}"
    siege_data = {
        "siege_id": siege_id,
        "style": args.style,
        "started_at": datetime.now().isoformat(),
        "current_gate": 0,
        "gates_status": {
            "gate_1_verdict": "pending",
            "gate_2_select": "pending",
            "gate_3_text": "pending",
            "gate_4_assemble": "pending"
        }
    }
    save_json(surge_data, OUT_DIR / "siege_state.json")
    print(f"🏴 Siege started: {siege_id}")
    print(f"   Style: {args.style}")


def cmd_verdict(args):
    """Gate 1: Verdict (GO/NO-GO) on the podcast."""
    print("🚪 Gate 1: Verdict...")

    # Load transcript
    transcript_path = IN_DIR / "transcript.json"
    if not transcript_path.exists():
        print("❌ transcript.json not found in IN/")
        return

    transcript = load_json(transcript_path)

    # Basic clipability check
    total_segments = len(transcript.get("segments", []))
    total_duration = transcript.get("total_duration_sec", 0)

    # Score clipability
    score = 0
    if total_segments > 50:
        score += 30
    if total_duration > 300:  # > 5 min
        score += 30
    if total_segments > 100:
        score += 20
    if total_duration > 1800:  # > 30 min
        score += 20

    verdict = "GO" if score >= 40 else "NO-GO"
    reason = f"Clipability score: {score}/100 ({total_segments} segments, {total_duration}s)"

    verdict_data = {
        "verdict": verdict,
        "reason": reason,
        "clipability_score": score,
        "total_segments": total_segments,
        "total_duration_sec": total_duration,
        "timestamp": datetime.now().isoformat()
    }

    save_json(verdict_data, OUT_DIR / "campaign_verdict.json")
    print(f"   Verdict: {verdict} — {reason}")


def cmd_select(args):
    """Gate 2: Select viral moments from transcript."""
    print("🚪 Gate 2: Selecting viral moments...")

    transcript_path = IN_DIR / "transcript.json"
    if not transcript_path.exists():
        print("❌ transcript.json not found")
        return

    transcript = load_json(transcript_path)
    segments = transcript.get("segments", [])
    n_moments = args.n_moments

    # Score each segment for viral potential
    scored_segments = []
    for i, seg in enumerate(segments):
        text = seg.get("text", "").lower()
        score = 0

        # Visual trigger words
        visual_words = ["look", "see", "imagine", "picture", "this guy", "she said", "he told"]
        for w in visual_words:
            if w in text:
                score += 3
                break

        # Emotion words
        emotion_words = ["shocking", "insane", "crazy", "unbelievable", "wow", "omg"]
        for w in emotion_words:
            if w in text:
                score += 2
                break

        # Controversy
        controversy_words = ["controversy", "scandal", "lie", "cheat", "fight"]
        for w in controversy_words:
            if w in text:
                score += 2
                break

        # Engagement
        engagement_words = ["wait", "stop", "listen", "pay attention"]
        for w in engagement_words:
            if w in text:
                score += 1
                break

        if score > 0:
            scored_segments.append({
                "segment_id": f"S{i+1:03d}",
                "index": i,
                "start": seg.get("start", 0),
                "duration": seg.get("duration", 0),
                "text": seg.get("text", ""),
                "score": score
            })

    # Sort by score and take top N
    scored_segments.sort(key=lambda x: x["score"], reverse=True)
    top_moments = scored_segments[:n_moments]

    # Add moment IDs
    for i, m in enumerate(top_moments):
        m["moment_id"] = f"M{i+1:02d}"

    moments_data = {
        "n_moments": len(top_moments),
        "moments": top_moments,
        "timestamp": datetime.now().isoformat()
    }

    save_json(moments_data, OUT_DIR / "viral_moments.json")
    print(f"   Found {len(top_moments)} viral moments")
    for m in top_moments:
        print(f"   {m['moment_id']}: score={m['score']} — {m['text'][:60]}...")


def cmd_text(args):
    """Gate 3: Generate text payloads + B-roll prompts."""
    print("🚪 Gate 3: Generating texts + B-roll...")

    moments_path = OUT_DIR / "viral_moments.json"
    if not moments_path.exists():
        print("❌ viral_moments.json not found (run --select first)")
        return

    moments = load_json(moments_path)
    style = args.style

    # Load style patterns
    style_path = ARCHIVUM_DIR / "montage" / "patterns" / f"style_{style}.json"
    if style_path.exists():
        style_patterns = load_json(style_path)
        print(f"   Loaded style: {style}")
    else:
        style_patterns = {}
        print(f"   ⚠️ Style {style} not found, using defaults")

    # Load B-roll scoring rules
    broll_path = ARCHIVUM_DIR / "montage" / "patterns" / "broll_integration.json"
    broll_rules = load_json(broll_path) if broll_path.exists() else {}

    # Load PUR copywriting rules
    copywriting_path = ARCHIVUM_DIR / "montage" / "patterns" / "copywriting_pur.json"
    copywriting_rules = load_json(copywriting_path) if copywriting_path.exists() else {}

    # Load PUR hooks psychology
    hooks_pur_path = ARCHIVUM_DIR / "montage" / "patterns" / "hooks_pur.json"
    hooks_pur = load_json(hooks_pur_path) if hooks_pur_path.exists() else {}

    # Title rules by style
    title_config = copywriting_rules.get("title_generation", {}).get(style, {})
    max_words = title_config.get("max_words", 4) if style == "ranking" else None
    max_lines = title_config.get("max_lines", 2) if style != "ranking" else None

    # Countdown order rules (ranking only)
    countdown_rules = copywriting_rules.get("countdown_order", {}) if style == "ranking" else {}

    # Generate text payloads for each moment
    text_payloads = []
    for i, moment in enumerate(moments.get("moments", [])):
        # Ranking: clip label (1 word) — the reframing title of each clip
        clip_label = None
        if style == "ranking":
            # Label generated by Oracle, here placeholder from transcript
            clip_label = moment.get("text", "").split()[0] if moment.get("text") else f"clip{i+1}"

        payload = {
            "moment_id": moment["moment_id"],
            "title": f"VIRAL MOMENT #{moment['moment_id'][-2:]}",
            "clip_label": clip_label,
            "hook_text": moment.get("text", "")[:50],
            "captions": [
                {"text": moment.get("text", ""), "start": 0, "end": moment.get("duration", 3)}
            ],
            "broll_schedule": [],  # To be scored
            "copywriting_rules": {
                "style": style,
                "title_max_words": max_words,
                "title_max_lines": max_lines,
                "narrative_reframing": True,
                "oracle_generates": True,
                "warsmith_validates": True,
                "countdown_order": countdown_rules.get("rule", "") if countdown_rules else "",
                "language": "operator_chosen"
            },
            "metadata": {
                "title": f"Viral Moment - {moment['moment_id']}",
                "description": f"Check out this viral moment! {moment.get('text', '')[:100]}",
                "tags": ["viral", "moment", "clip"]
            }
        }
        text_payloads.append(payload)

    payload_data = {
        "style": style,
        "n_payloads": len(text_payloads),
        "payloads": text_payloads,
        "timestamp": datetime.now().isoformat()
    }

    save_json(payload_data, OUT_DIR / "text_payload.json")
    print(f"   Generated {len(text_payloads)} text payloads")


def cmd_assemble(args):
    """Gate 4: Assemble the PUR production pack."""
    print("🚪 Gate 4: Assembling PUR pack...")

    moments_path = OUT_DIR / "viral_moments.json"
    text_path = OUT_DIR / "text_payload.json"

    if not moments_path.exists() or not text_path.exists():
        print("❌ Missing inputs (run --select and --text first)")
        return

    moments = load_json(moments_path)
    texts = load_json(text_path)
    style = args.style

    # Load anti-detection rules
    anti_path = ARCHIVUM_DIR / "montage" / "patterns" / "anti_detection.json"
    anti_rules = load_json(anti_path) if anti_path.exists() else {}

    # Assemble production pack
    packs = []
    for payload in texts.get("payloads", []):
        # Anti-detection config (shared)
        anti_detection = {
            "mirror": style == "ranking",
            "zoom": {
                "type": "punch" if style == "ranking" else "slow_push_in" if style == "reframing" else "breathing" if style == "blur" else "slow_push_in",
                "start_pct": 100,
                "end_pct": 115 if style == "ranking" else 108 if style == "reframing" else 110 if style == "blur" else 108
            },
            "speed": {"base": 1.0, "variations": [{"at_sec": 15, "speed": 1.05, "duration_sec": 3}]},
            "sfx": [
                {"type": "whoosh", "at_sec": 3.0, "volume_db": -18},
                {"type": "boom", "at_sec": 15.0, "volume_db": -15}
            ],
            "crop": {"top": 0.02, "bottom": 0.02, "left": 0.01, "right": 0.01}
        }

        pack = {
            "clip_id": f"pur_{payload['moment_id'].lower()}",
            "style": style,
            "segment": next(
                (m for m in moments.get("moments", []) if m["moment_id"] == payload["moment_id"]),
                {}
            ),
            "text_payload": payload,
            "broll_schedule": payload.get("broll_schedule", []),
            "anti_detection": anti_detection,
            "montage_instructions": {
                "hook_duration_sec": 3,
                "total_duration_sec": 30,
                "pacing": "fast",
                "energy_curve": ["hook_100", "build_70", "punchline_100", "outro_50"]
            }
        }

        # Split Scene specific: add layout info
        if style == "split_scene":
            pack["split_scene"] = {
                "layout": {
                    "top": "podcast_clip_source",
                    "center": "title_hook",
                    "bottom": "variable_content"
                },
                "sub_layout": "A_image_ia",  # Default, operator overrides
                "broll_behavior": "full_screen_overlay",
                "gif_behavior": "loop_if_single"
            }

        packs.append(pack)

    pack_data = {
        "siege_id": datetime.now().strftime("PUR-SIEGE-%Y%m%dT%H%M%S"),
        "style": style,
        "n_packs": len(packs),
        "packs": packs,
        "timestamp": datetime.now().isoformat()
    }

    save_json(pack_data, OUT_DIR / "production_pack_pur.json")
    print(f"   Assembled {len(packs)} packs")


def cmd_direct(args):
    """Gate 5 (Split Scene): Enrich with F06_DIRECTOR instructions."""
    print("🚪 Gate 5: Split Scene enrichment...")

    pack_path = OUT_DIR / "production_pack_pur.json"
    if not pack_path.exists():
        print("❌ production_pack_pur.json not found (run --assemble first)")
        return

    packs = load_json(pack_path)
    style = packs.get("style", "")

    if style != "split_scene":
        print(f"   ⚠️ Style is '{style}', not split_scene. Skipping split enrichment.")
        return

    # Load split scene pattern
    split_pattern_path = ARCHIVUM_DIR / "montage" / "patterns" / "style_split_scene.json"
    if split_pattern_path.exists():
        split_pattern = load_json(split_pattern_path)
        print(f"   Loaded split_scene pattern")
    else:
        split_pattern = {}
        print(f"   ⚠️ style_split_scene.json not found")

    # Load hooks psychology for title generation
    hooks_path = ARCHIVUM_DIR / "montage" / "patterns" / "hooks_psychology.json"
    hooks_rules = load_json(hooks_path) if hooks_path.exists() else {}

    # Enrich each pack with split_scene specific instructions
    enriched_packs = []
    for pack in packs.get("packs", []):
        enriched = pack.copy()
        enriched["split_scene"] = {
            "layout": {
                "top": {
                    "source": "podcast_clip",
                    "instruction": "Extraire le segment du podcast, speaker face visible"
                },
                "center": {
                    "type": "title_hook",
                    "instruction": "Generer un titre narratif qui transforme le sens du clip",
                    "format": "hooks_psychology.json - court, narratif, hook fort"
                },
                "bottom": {
                    "type": pack.get("split_scene", {}).get("sub_layout", "A_image_ia"),
                    "instruction": "Contenu variable selon le sous-layout choisi"
                }
            },
            "broll_fullscreen": {
                "rule": "Quand broll intervient, couvre TOUT l'ecran",
                "format": "split -> broll_fullscreen -> split",
                "timing_scoring": "broll_integration.json"
            },
            "anti_detection": pack.get("anti_detection", {}),
            "gif_behavior": {
                "single": "loop_continue",
                "ranking": "un_gif_par_numero"
            },
            "composability": {
                "ranking_composition": "Tous les segments en split si mode ranking+split"
            }
        }
        enriched_packs.append(enriched)

    enriched_data = {
        "siege_id": packs.get("siege_id", ""),
        "style": "split_scene",
        "n_packs": len(enriched_packs),
        "packs": enriched_packs,
        "timestamp": datetime.now().isoformat(),
        "gate": "5_direct"
    }

    save_json(enriched_data, OUT_DIR / "production_pack_pur.json")
    print(f"   Enriched {len(enriched_packs)} packs with split_scene instructions")


def cmd_export(args):
    """Export the production pack to EXPORT/."""
    print("📦 Exporting to EXPORT/...")

    pack_path = OUT_DIR / "production_pack_pur.json"
    if not pack_path.exists():
        print("❌ production_pack_pur.json not found (run --assemble first)")
        return

    export_path = EXPORT_DIR / "production_pack_pur.json"
    export_path.parent.mkdir(exist_ok=True)

    import shutil
    shutil.copy2(pack_path, export_path)
    print(f"   ✅ Exported to: {export_path}")


def cmd_status(args):
    """Show current siege status."""
    state_path = OUT_DIR / "siege_state.json"
    if state_path.exists():
        state = load_json(state_path)
        print(f"🏴 Siege: {state.get('siege_id', 'unknown')}")
        print(f"   Style: {state.get('style', 'unknown')}")
        print(f"   Gate: {state.get('current_gate', 0)}")
    else:
        print("❌ No active siege")


def main():
    parser = argparse.ArgumentParser(description="PUR Mode — Viral moment extraction")
    subparsers = parser.add_subparsers(dest="command")

    # start-siege
    p_start = subparsers.add_parser("start-siege")
    p_start.add_argument("--style", default="ranking", choices=["ranking", "reframing", "blur", "split_scene"])

    # verdict
    subparsers.add_parser("verdict")

    # select
    p_select = subparsers.add_parser("select")
    p_select.add_argument("--n-moments", type=int, default=5)

    # text
    p_text = subparsers.add_parser("text")
    p_text.add_argument("--style", default="ranking", choices=["ranking", "reframing", "blur", "split_scene"])

    # assemble
    p_assemble = subparsers.add_parser("assemble")
    p_assemble.add_argument("--style", default="ranking", choices=["ranking", "reframing", "blur", "split_scene"])
    p_assemble.add_argument("--finalize", action="store_true")

    # direct (split scene enrichment)
    subparsers.add_parser("direct")

    # export
    subparsers.add_parser("export")

    # status
    subparsers.add_parser("status")

    args = parser.parse_args()

    if args.command == "start-siege":
        cmd_start_siege(args)
    elif args.command == "verdict":
        cmd_verdict(args)
    elif args.command == "select":
        cmd_select(args)
    elif args.command == "text":
        cmd_text(args)
    elif args.command == "assemble":
        cmd_assemble(args)
    elif args.command == "direct":
        cmd_direct(args)
    elif args.command == "export":
        cmd_export(args)
    elif args.command == "status":
        cmd_status(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
