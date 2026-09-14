"""Tests Note 20 — pont F00C → tronc PUR + lecteur tolérant (3 formes)."""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path


CODEBASE = Path(__file__).parents[1]
CLIPPING = CODEBASE.parents[2]
SHARED = CLIPPING / "SHARED"
F00C = CODEBASE / "f00c_vox.py"

sys.path.insert(0, str(SHARED))
import candidates_reader as reader  # noqa: E402

spec = importlib.util.spec_from_file_location("f00c_vox", F00C)
f00c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(f00c)


def _canonical_item(i=1, start=10.0, end=25.0):
    return {
        "candidate_id": "cand-{}".format(i),
        "start_sec": start,
        "end_sec": end,
        "duration_sec": end - start,
        "signal_type": "chat_spike",
        "signal_intensity": 0.9,
        "signal_start": "2026-09-11T00:00:00Z",
        "top_words": "hello world",
    }


def test_reader_canonical_form(tmp_path):
    path = tmp_path / "candidats.json"
    path.write_text(json.dumps({"candidates": [_canonical_item()]}), encoding="utf-8")
    doc = reader.load_candidates_document(str(path))
    assert doc["_input_form"] == "canonical"
    assert len(doc["candidates"]) == 1
    assert doc["candidates"][0]["candidate_id"] == "cand-1"


def test_reader_f00b_detect_key(tmp_path, capsys):
    path = tmp_path / "candidats.json"
    path.write_text(json.dumps({
        "generated_at": "2026-09-11T00:00:00",
        "total_candidats": 1,
        "candidats": [_canonical_item()],
    }), encoding="utf-8")
    doc = reader.load_candidates_document(str(path))
    err = capsys.readouterr().err
    assert doc["_input_form"] == "f00b_detect"
    assert "candidates" in doc
    assert len(doc["candidates"]) == 1
    assert "WARNING" in err
    assert "f00b_detect" in err


def test_reader_voxc_manifest(tmp_path, capsys):
    path = tmp_path / "live_analysis.json"
    path.write_text(json.dumps({
        "schema_version": "perturabo.voxc.v1",
        "generated_at": "2026-09-11T12:00:00Z",
        "source": {"reference": "https://youtu.be/dQw4w9WgXcQ", "id": "dQw4w9WgXcQ"},
        "viral_segments": [
            {"start_sec": 3.0, "end_sec": 8.0, "attention_norm": 1.0, "rank": 1},
            {"start_sec": 20.0, "end_sec": 26.0, "attention_norm": 0.7, "rank": 2},
        ],
    }), encoding="utf-8")
    doc = reader.load_candidates_document(str(path))
    err = capsys.readouterr().err
    assert doc["_input_form"] == "voxc_manifest"
    assert "WARNING" in err
    cands = doc["candidates"]
    assert len(cands) == 2
    assert cands[0]["candidate_id"] == "voxc-1"
    assert cands[0]["signal_type"] == "platform_heat"
    assert cands[0]["signal_intensity"] == 1.0
    assert cands[0]["top_words"] == ""
    assert cands[1]["duration_sec"] == 6.0


def test_reader_empty_raises_clear_error(tmp_path):
    path = tmp_path / "empty.json"
    path.write_text(json.dumps({"candidates": []}), encoding="utf-8")
    try:
        reader.load_candidates_document(str(path))
    except reader.CandidatesReadError as exc:
        assert "0 candidat" in str(exc)
        assert "silence" in str(exc)
    else:
        raise AssertionError("un document vide doit échouer, pas produire 0 pack")


def test_reader_unknown_form_raises(tmp_path):
    path = tmp_path / "weird.json"
    path.write_text(json.dumps({"foo": 1}), encoding="utf-8")
    try:
        reader.load_candidates_document(str(path))
    except reader.CandidatesReadError as exc:
        assert "inconnue" in str(exc)
    else:
        raise AssertionError("forme inconnue doit échouer")


def test_emit_candidats_maps_segments(tmp_path):
    manifest = {
        "schema_version": "perturabo.voxc.v1",
        "generated_at": "2026-09-11T12:00:00Z",
        "source": {"reference": "local.mp4", "id": "local"},
        "viral_segments": [
            {"start_sec": 1.0, "end_sec": 4.0, "attention_norm": 0.4, "rank": 2},
            {"start_sec": 10.0, "end_sec": 15.0, "attention_norm": 0.9, "rank": 1},
        ],
    }
    out = tmp_path / "candidats.json"
    doc = f00c.emit_candidats(manifest, out, top=None)
    assert out.exists()
    assert [c["candidate_id"] for c in doc["candidates"]] == ["voxc-2", "voxc-1"]
    assert all(c["signal_type"] == "platform_heat" for c in doc["candidates"])
    loaded = json.loads(out.read_text(encoding="utf-8"))
    assert "candidates" in loaded
    assert loaded["engine"] == "f00c_vox"


def test_emit_candidats_top_n(tmp_path):
    manifest = {
        "generated_at": "2026-09-11T12:00:00Z",
        "source": {"id": "x"},
        "viral_segments": [
            {"start_sec": 1.0, "end_sec": 2.0, "attention_norm": 0.2, "rank": 3},
            {"start_sec": 5.0, "end_sec": 7.0, "attention_norm": 1.0, "rank": 1},
            {"start_sec": 9.0, "end_sec": 12.0, "attention_norm": 0.5, "rank": 2},
        ],
    }
    doc = f00c.emit_candidats(manifest, tmp_path / "c.json", top=1)
    assert len(doc["candidates"]) == 1
    assert doc["candidates"][0]["signal_intensity"] == 1.0


def test_pur_adapter_direct_accepts_voxc_manifest(tmp_path):
    manifest = tmp_path / "live_analysis.json"
    manifest.write_text(json.dumps({
        "schema_version": "perturabo.voxc.v1",
        "generated_at": "2026-09-11T12:00:00Z",
        "source": {"reference": "https://youtu.be/dQw4w9WgXcQ"},
        "viral_segments": [
            {"start_sec": 3.0, "end_sec": 8.0, "attention_norm": 1.0, "rank": 1},
            {"start_sec": 20.0, "end_sec": 26.0, "attention_norm": 0.7, "rank": 2},
        ],
    }), encoding="utf-8")
    adapter = CLIPPING / "pur_adapter_direct.py"
    work = tmp_path / "clip"
    (work / "F02_TYRANT_CAMP" / "OUT").mkdir(parents=True)
    (work / "F03_SOURCE_HUNTER" / "OUT").mkdir(parents=True)
    (work / "SHARED").mkdir()
    import shutil
    shutil.copy(SHARED / "candidates_reader.py", work / "SHARED" / "candidates_reader.py")
    shutil.copy(adapter, work / "pur_adapter_direct.py")
    result = subprocess.run(
        [sys.executable, str(work / "pur_adapter_direct.py"),
         "--candidats", str(manifest), "--vod", "https://youtu.be/dQw4w9WgXcQ",
         "--nb-videos", "5"],
        cwd=str(work), capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    angles = json.loads((work / "F02_TYRANT_CAMP" / "OUT" / "angles.json").read_text(encoding="utf-8"))
    assert angles["n_angles"] == 2
    assert angles["angles"][0]["vox_signal_type"] == "platform_heat"


def test_pur_adapter_direct_empty_manifest_fails(tmp_path):
    manifest = tmp_path / "empty.json"
    manifest.write_text(json.dumps({
        "schema_version": "perturabo.voxc.v1",
        "viral_segments": [],
    }), encoding="utf-8")
    adapter = CLIPPING / "pur_adapter_direct.py"
    work = tmp_path / "clip"
    (work / "F02_TYRANT_CAMP" / "OUT").mkdir(parents=True)
    (work / "F03_SOURCE_HUNTER" / "OUT").mkdir(parents=True)
    (work / "SHARED").mkdir()
    import shutil
    shutil.copy(SHARED / "candidates_reader.py", work / "SHARED" / "candidates_reader.py")
    shutil.copy(adapter, work / "pur_adapter_direct.py")
    result = subprocess.run(
        [sys.executable, str(work / "pur_adapter_direct.py"),
         "--candidats", str(manifest), "--vod", "https://youtu.be/x"],
        cwd=str(work), capture_output=True, text=True,
    )
    assert result.returncode != 0
    assert "0 candidat" in result.stderr
    assert not (work / "F02_TYRANT_CAMP" / "OUT" / "angles.json").exists()
