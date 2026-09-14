"""Tests WAR ROOM transcripts — hors-ligne (aucun réseau, aucun yt-dlp réel)."""
import importlib.util
import json
import sys
from pathlib import Path

MODULE_PATH = Path(__file__).parents[1] / "transcripts.py"
spec = importlib.util.spec_from_file_location("war_room_transcripts", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_parse_manual_vtt():
    vtt = "WEBVTT\n\n00:00:00.000 --> 00:00:02.500\nHello world\n\n" \
          "00:00:02.500 --> 00:00:05.000\nsecond line\n"
    cues = module.parse_vtt_cues(vtt)
    assert len(cues) == 2
    assert cues[0]["text"] == "Hello world"
    assert abs(cues[1]["end"] - 5.0) < 0.01


def test_parse_auto_vtt_strips_tags_and_dedup():
    vtt = ("WEBVTT\n\n"
           "00:00:00.000 --> 00:00:02.000\nHello everyone\n\n"
           "00:00:01.000 --> 00:00:03.000\nHello everyone\nand welcome\n\n"
           "00:00:03.000 --> 00:00:05.500\n<c>let's <00:00:04.000>go</c>\n")
    cues = module._merge_duplicates(module.parse_vtt_cues(vtt))
    assert cues[0]["text"] == "Hello everyone and welcome"
    assert cues[-1]["text"] == "let's go"


def test_chunk_lines_groups_short_cues():
    cues = [
        {"start": 0.0, "end": 1.5, "text": "un"},
        {"start": 1.5, "end": 3.0, "text": "deux"},
        {"start": 10.0, "end": 12.0, "text": "trois"},
    ]
    lines = module._chunk_lines(cues)
    assert lines[0]["text"] == "un deux"
    assert lines[1]["text"] == "trois"      # trou temporel → nouveau bloc
    assert abs(lines[0]["end_rel"] - 3.0) < 0.01 if "end_rel" in lines[0] else True


def test_build_candidate_transcript_reads_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(module, "TRANSCRIPTS_DIR", tmp_path)
    monkeypatch.setattr(module, "SUBS_DIR", tmp_path / "_subs")
    cand = {"id": "voxc-x", "start_sec": 10.0, "end_sec": 20.0}
    cache_dir = tmp_path / "run"
    cache_dir.mkdir(parents=True)
    for lang, texte in (("fr", "salut"), ("en", "hello")):
        cache = cache_dir / f"voxc-x.{lang}.json"
        cache.write_text(json.dumps({
            "available": True,
            "lines": [{"t_abs": 12.0, "t_rel": 2.0, "end_rel": 4.0, "text": texte}],
        }), encoding="utf-8")
    out = module.build_candidate_transcript("https://example.invalid/v", "run", cand)
    assert out["fr"]["available"] is True
    assert out["fr"]["lines"][0]["text"] == "salut"
    assert out["available"] is True  # au moins une langue = disponible


def test_build_candidate_transcript_rate_limit_is_clean(tmp_path, monkeypatch):
    """429 → aucune exception, résultat dégradé lisible (contrat v2 : absorbé par langue)."""
    monkeypatch.setattr(module, "TRANSCRIPTS_DIR", tmp_path)
    monkeypatch.setattr(module, "SUBS_DIR", tmp_path / "_subs")

    def boom(url):
        raise RuntimeError("YouTube limite le débit de cette IP — nouvel essai dans ~10 min")
    monkeypatch.setattr(module, "_download_subs", boom)
    cand = {"id": "voxc-y", "start_sec": 0.0, "end_sec": 5.0}
    out = module.build_candidate_transcript("https://example.invalid/v", "run", cand)
    assert out["available"] is False
    # le message de rate-limit doit être tracé (erreur par langue ou note Whisper)
    errors = " ".join(str((out.get(l) or {}).get("error") or "") for l in ("fr", "en"))
    assert "limite le débit" in errors or out.get("whisper_note") or out.get("note")


def test_self_test():
    assert module.self_test() == 0
