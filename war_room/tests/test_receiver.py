"""Tests WAR ROOM receiver — hors-ligne (aucun réseau)."""
import importlib.util
import json
import sys
from pathlib import Path

MODULE_PATH = Path(__file__).parents[1] / "receiver.py"
spec = importlib.util.spec_from_file_location("war_room_receiver", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


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
