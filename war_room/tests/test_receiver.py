"""Tests WAR ROOM receiver — hors-ligne (aucun réseau, état réel jamais touché)."""
import importlib.util
import json
import sys
from pathlib import Path

MODULE_PATH = Path(__file__).parents[1] / "receiver.py"
spec = importlib.util.spec_from_file_location("war_room_receiver", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

# Les tests écrivent dans un fichier temporaire — JAMAIS dans docs/data/war_room.json
import tempfile
_TMP = tempfile.mkdtemp(prefix="war_room_tests_")
module.DATA_PATH = Path(_TMP) / "war_room.json"


def _sample(mode="vod", status="full"):
    return {
        "run_id": "f00c_test_1",
        "siege_id": "SOPHIE_RAIN_TEST",
        "mode": mode,
        "status": status,
        "source": {"reference": "https://www.youtube.com/watch?v=qm3E3cchBmQ",
                   "platform": "youtube", "content_type": "video"},
        "heatmap": [{"bucket": 0, "start_sec": 0.0, "end_sec": 1.0,
                     "attention": 0.5, "attention_norm": 1.0}],
        "replayed_curve": [{"start": 0.0, "end": 1.0, "value": 0.8}],
        "fused_heatmap": [],
        "candidates": [{"id": "clip_01", "rank": 1, "score": 0.8}],
        "pushed_at": "2026-09-12T22:00:00+00:00",
    }


def test_validate_accepts_canonical_payload():
    ok, reason = module.validate_payload(_sample())
    assert ok, reason


def test_validate_accepts_live_mode():
    ok, reason = module.validate_payload(_sample(mode="live"))
    assert ok, reason


def test_validate_rejects_missing_keys():
    ok, reason = module.validate_payload({"run_id": "x", "mode": "vod"})
    assert not ok
    assert "clés manquantes" in reason


def test_validate_rejects_unknown_mode_and_status():
    ok, reason = module.validate_payload(_sample(mode="podcast"))
    assert not ok and "mode" in reason
    ok, reason = module.validate_payload(_sample(status="green_and_vibes"))
    assert not ok and "status" in reason


def test_validate_rejects_non_list_candidates():
    sample = _sample()
    sample["candidates"] = "trois clips svp"
    ok, reason = module.validate_payload(sample)
    assert not ok and "candidates" in reason


def test_store_payload_writes_history(tmp_path, monkeypatch):
    data = tmp_path / "war_room.json"
    monkeypatch.setattr(module, "DATA_PATH", data)
    doc = module.store_payload(_sample())
    assert doc["total_runs"] == 1
    assert doc["runs"]["f00c_test_1"]["n_candidates"] == 1
    second = _sample()
    second["run_id"] = "f00c_test_2"
    doc = module.store_payload(second)
    assert doc["total_runs"] == 2
    assert json.loads(data.read_text(encoding="utf-8"))["last_run"]["run_id"] == "f00c_test_2"


def test_store_payload_survives_corrupt_existing_file(tmp_path, monkeypatch):
    data = tmp_path / "war_room.json"
    data.write_text("{corrompu", encoding="utf-8")
    monkeypatch.setattr(module, "DATA_PATH", data)
    doc = module.store_payload(_sample())
    assert doc["total_runs"] == 1  # jamais de crash sur un fichier corrompu


def test_self_test_round_trip(tmp_path, monkeypatch):
    monkeypatch.setattr(module, "DATA_PATH", tmp_path / "war_room.json")
    assert module.self_test() == 0


def test_store_gate_rejects_unknown_run(tmp_path, monkeypatch):
    monkeypatch.setattr(module, "DATA_PATH", tmp_path / "war_room.json")
    _, reason = module.store_gate("run_inconnu", "clip_01", "approved")
    assert reason.startswith("run_id inconnu")


def test_store_gate_rejects_unknown_candidate(tmp_path, monkeypatch):
    monkeypatch.setattr(module, "DATA_PATH", tmp_path / "war_room.json")
    module.store_payload(_sample())
    _, reason = module.store_gate("f00c_test_1", "clip_fantome", "approved")
    assert reason.startswith("candidate_id inconnu")


def test_store_gate_counts_are_idempotent(tmp_path, monkeypatch):
    monkeypatch.setattr(module, "DATA_PATH", tmp_path / "war_room.json")
    module.store_payload(_sample())
    doc, _ = module.store_gate("f00c_test_1", "clip_01", "approved")
    doc, _ = module.store_gate("f00c_test_1", "clip_01", "approved")  # re-vote identique
    assert doc["gate_counts"]["approved"] == 1
    doc, _ = module.store_gate("f00c_test_1", "clip_01", "rejected")  # inversion
    assert doc["gate_counts"]["approved"] == 0
    assert doc["gate_counts"]["rejected"] == 1
    assert doc["gates"]["f00c_test_1"]["clip_01"]["verdict"] == "rejected"


def test_clear_gate_revokes_verdict(tmp_path, monkeypatch):
    monkeypatch.setattr(module, "DATA_PATH", tmp_path / "war_room.json")
    module.store_payload(_sample())
    module.store_gate("f00c_test_1", "clip_01", "approved")
    doc, reason = module.clear_gate("f00c_test_1", "clip_01")
    assert reason == "ok"
    assert "clip_01" not in doc["gates"]["f00c_test_1"]
    assert doc["gate_counts"]["approved"] == 0
    assert "f00c_test_1/clip_01" not in doc["last_verdicts"]


def test_clear_gate_without_verdict_fails_cleanly(tmp_path, monkeypatch):
    monkeypatch.setattr(module, "DATA_PATH", tmp_path / "war_room.json")
    module.store_payload(_sample())
    _, reason = module.clear_gate("f00c_test_1", "clip_01")
    assert "pas de verdict" in reason


def test_reset_all_purges_gates_keeps_runs(tmp_path, monkeypatch):
    monkeypatch.setattr(module, "DATA_PATH", tmp_path / "war_room.json")
    module.store_payload(_sample())
    module.store_gate("f00c_test_1", "clip_01", "approved")
    doc = module.reset_all(full=False)
    assert doc.get("gates") is None and doc.get("last_verdicts") is None
    assert doc.get("gate_counts", {}).get("approved", 0) == 0
    assert doc.get("last_run", {}).get("run_id") == "f00c_test_1"  # runs conservés


def test_reset_full_purges_runs(tmp_path, monkeypatch):
    monkeypatch.setattr(module, "DATA_PATH", tmp_path / "war_room.json")
    module.store_payload(_sample())
    doc = module.reset_all(full=True)
    assert doc.get("last_run") is None and doc.get("runs") is None


def test_store_gate_rejects_unknown_style(tmp_path, monkeypatch):
    monkeypatch.setattr(module, "DATA_PATH", tmp_path / "war_room.json")
    module.store_payload(_sample())
    _, reason = module.store_gate("f00c_test_1", "clip_01", "approved", "hollywood")
    assert reason.startswith("style inconnu")


def test_store_gate_keeps_style_and_rerouting(tmp_path, monkeypatch):
    """GO avec style → style acté ; changer le style re-acte (idempotence par couple)."""
    monkeypatch.setattr(module, "DATA_PATH", tmp_path / "war_room.json")
    module.store_payload(_sample())
    doc, reason = module.store_gate("f00c_test_1", "clip_01", "approved", "blur")
    assert reason == "ok"
    entry = doc["gates"]["f00c_test_1"]["clip_01"]
    assert entry["verdict"] == "approved" and entry["style"] == "blur"
    # re-vote identique (même verdict, même style) : pas de double comptage
    doc, _ = module.store_gate("f00c_test_1", "clip_01", "approved", "blur")
    assert doc["gate_counts"]["approved"] == 1
    # GO sans style → style conservé (pas de perte au cockpit)
    doc, _ = module.store_gate("f00c_test_1", "clip_01", "approved")
    assert doc["gates"]["f00c_test_1"]["clip_01"]["style"] == "blur"


def test_emit_caviar_for_gate_emits_with_chosen_style(tmp_path, monkeypatch):
    """Boucle complète cockpit → F00D : GO + style blur → manifeste style blur."""
    monkeypatch.setattr(module, "DATA_PATH", tmp_path / "war_room.json")
    sample = _sample()
    sample["run_id"] = "f00c_emit_test"
    sample["candidates"] = [{"id": "voxc-9", "rank": 1, "score": 88.0,
                              "start_sec": 0.0, "end_sec": 45.0,
                              "duration_sec": 45.0, "signal_intensity": 0.9}]
    sample["fused_heatmap"] = [{"bucket": 0, "start_sec": 0.0, "end_sec": 22.5,
                                 "attention_norm": 0.9, "fused_norm": 0.8},
                                {"bucket": 1, "start_sec": 22.5, "end_sec": 45.0,
                                 "attention_norm": 0.5, "fused_norm": 0.4}]
    module.store_payload(sample)
    out_dir = tmp_path / "caviar_out"
    monkeypatch.setattr(module, "CAVIAR_DIR", out_dir)
    note = module.emit_caviar_for_gate("f00c_emit_test", "voxc-9", "blur")
    assert note["status"] == "emitted", note
    man = json.loads((out_dir / "caviar_manifest_voxc-9.json").read_text(encoding="utf-8"))
    assert man["style"] == "blur"
    assert man["source"]["gate"] == "approved"
    assert man["budget_state"]["caps_respected"] is True
    # l'index cockpit pointe vers le manifeste émis
    idx = json.loads(module.CAVIAR_INDEX.read_text(encoding="utf-8"))
    assert idx["manifests"]["voxc-9"].endswith("caviar_manifest_voxc-9.json")
