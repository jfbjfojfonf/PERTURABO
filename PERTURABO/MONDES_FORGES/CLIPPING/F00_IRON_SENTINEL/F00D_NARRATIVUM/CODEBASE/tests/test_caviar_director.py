"""Tests F00D_NARRATIVUM — hors-ligne (aucun réseau, aucun média requis)."""
import importlib.util
import json
import sys
from pathlib import Path

MODULE_PATH = Path(__file__).parents[1] / "caviar_director.py"
spec = importlib.util.spec_from_file_location("caviar_director", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

BUDGET = module.load_budget()


def _doc(style="reframing", duration=30.0, peaks_norm=0.95):
    return {
        "candidate": {"candidate_id": "t1", "run_id": "run_x",
                      "duration_sec": duration, "score": 90.0},
        "segment_heatmap": [
            {"start_sec": 0.0, "end_sec": duration * 0.33, "attention_norm": 0.4},
            {"start_sec": duration * 0.33, "end_sec": duration * 0.66, "attention_norm": peaks_norm},
            {"start_sec": duration * 0.66, "end_sec": duration, "attention_norm": 0.3},
        ],
        "constraints": {"style": style},
    }


def test_schema_and_time_reference():
    m, why = module.compose(_doc(), media="", budget=BUDGET)
    assert m is not None, why
    assert m["schema_version"] == "caviar.v1"
    assert m["time_reference"] == "segment_relative_seconds"


def test_budget_within_ceiling_and_breathing_floor():
    m, _ = module.compose(_doc(), media="", budget=BUDGET)
    st = m["budget_state"]
    assert st["spent_units"] <= st["ceiling_units"] <= 55
    assert st["breathing_units"] >= 45
    assert st["counts"]["broll"] <= BUDGET["events"]["broll_trio"]["max_per_clip"]


def test_trio_inseparable_flash_and_sfx():
    m, _ = module.compose(_doc(), media="", budget=BUDGET)
    for b in m["events"]["broll"]:
        assert b["entry_flash"] is True
        assert b["sfx"]  # SFX obligatoire si flash
        assert b["duration_frames"] <= BUDGET["events"]["broll_trio"]["max_duration_frames"]


def test_no_events_after_resolution():
    m, _ = module.compose(_doc(duration=45.0), media="", budget=BUDGET)
    res = m["narrative"]["resolution_at"]
    for b in m["events"]["broll"]:
        assert b["start_sec"] < res
    for p in m["events"]["punch_ins"]:
        assert p["at_sec"] < res


def test_styles_change_composition():
    m_ref, _ = module.compose(_doc("reframing"), media="", budget=BUDGET)
    m_rank, _ = module.compose(_doc("ranking", duration=40.0), media="", budget=BUDGET)
    assert m_ref["narrative"]["hook_type"] == "climax_first"
    assert len(m_rank["events"]["smash_audio"]) >= 2  # l'item #1 a son smash en plus


def test_blur_style_composition():
    m, why = module.compose(_doc("blur", duration=45.0), media="", budget=BUDGET)
    assert m is not None, why
    assert m["style"] == "blur"
    assert m["narrative"]["hook_type"] == "climax_first"
    brolls = m["events"]["broll"]
    assert brolls, "le style blur doit poser des panneaux broll_blur"
    for b in brolls:
        assert b["kind"] == "broll_blur"
        assert b["entry_flash"] is True and b["sfx"]  # trio inséparable
        assert b["blur_radius_px"] > 0 and b["crop_zoom"] > 1
    st = m["budget_state"]
    assert st["spent_units"] <= st["ceiling_units"] and st["caps_respected"]


def test_blur_short_clip_no_panel():
    # Clip < 15 s : pas de panneau blur (trop court), repli gracieux
    m, why = module.compose(_doc("blur", duration=12.0), media="", budget=BUDGET)
    assert m is not None, why
    assert m["events"]["broll"] == []  # pas de panneau possible sur 12 s


def test_unknown_style_refused():
    m, why = module.compose(_doc("hollywood"), media="", budget=BUDGET)
    assert m is None and "style inconnu" in why


def test_caps_truncate_not_crash():
    # 15 pics d'amplitude simulés → caps tronquent, pas de crash, budget respecté
    doc = _doc(peaks_norm=0.99)
    doc["segment_heatmap"] = [
        {"start_sec": i * 2.0, "end_sec": (i + 1) * 2.0, "attention_norm": 0.99}
        for i in range(15)]
    m, why = module.compose(doc, media="", budget=BUDGET)
    assert m is not None or "saturé" in why
    if m:
        st = m["budget_state"]
        assert st["caps_respected"] and st["spent_units"] <= st["ceiling_units"]


def test_silence_map_tolerates_missing_media():
    assert module.silence_map("/chemin/inexistant.mp4") == []
    assert module.amplitude_peaks("/chemin/inexistant.mp4") == []
