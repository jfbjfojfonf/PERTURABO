#!/usr/bin/env python3
"""Tests War Room — sources transcript (opérateur + Whisper, hors-ligne)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import transcripts as T


def test_parse_srt_tolerance():
    srt = """1
00:00:01,000 --> 00:00:03,500
Bonjour à tous et bienvenue

2
00:00:03,500 --> 00:00:05,000
dans cette vidéo on parle viral

"""
    cues = T.parse_srt_or_vtt(srt)
    assert len(cues) == 2, cues
    assert cues[0]["text"] == "Bonjour à tous et bienvenue"
    assert abs(cues[0]["start"] - 1.0) < 0.01
    assert abs(cues[1]["end"] - 5.0) < 0.01


def test_parse_vtt_with_header():
    vtt = """WEBVTT

00:00:00.000 --> 00:00:02.000
Hello everyone

00:00:02.000 --> 00:00:04.000
let's talk about clips
"""
    cues = T.parse_srt_or_vtt(vtt)
    assert len(cues) == 2, cues
    assert cues[0]["text"] == "Hello everyone"


def test_parse_plain_text_timespan():
    txt = "première ligne du transcript\ndeuxième ligne ici\n\ntroisième ligne\n"
    cues = T.parse_plain_text(txt, sec_per_line=3.0)
    assert len(cues) == 3, cues
    assert cues[0]["start"] == 0.0 and cues[0]["end"] == 3.0
    assert cues[2]["start"] == 6.0


def test_parse_plain_text_stamped():
    """Format [MM:SS] / [HH:MM:SS] (export « transcription » YouTube) : exact."""
    txt = """[00:00:00] Bonjour à tous
[00:00:02] ici on parle viral
[00:01:10] deuxième minute
"""
    cues = T.parse_plain_text(txt)
    assert len(cues) == 3, cues
    assert cues[0]["start"] == 0.0 and abs(cues[0]["end"] - 2.0) < 0.01
    assert abs(cues[2]["start"] - 70.0) < 0.01
    assert cues[0]["text"] == "Bonjour à tous"


def test_youtube_video_id():
    assert T._youtube_video_id("https://www.youtube.com/watch?v=cP8vli4kfhs") == "cP8vli4kfhs"
    assert T._youtube_video_id("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert T._youtube_video_id("https://example.com/foo") == ""


def test_detect_language():
    assert T._detect_language("bonjour je suis ici et on va parler de montage c'est parti") == "fr"
    assert T._detect_language("hello guys today we talk about editing and cuts") == "en"


def test_operator_priority_over_youtube(tmp_path, monkeypatch):
    """Un fichier opérateur doit passer avant tout téléchargement YouTube."""
    # le moindre appel yt-dlp doit lever : si on y arrive, la priorité est cassée
    def boom(url):
        raise RuntimeError("yt-dlp ne doit PAS être appelé quand l'opérateur fournit")

    monkeypatch.setattr(T, "_download_subs", boom)
    op_dir = T.OPERATOR_DIR
    op_dir.mkdir(parents=True, exist_ok=True)
    f = op_dir / "TESTVID.fr.srt"
    f.write_text("1\n00:00:00,000 --> 00:00:10,000\nCeci vient de l'opérateur\n\n",
                 encoding="utf-8")
    try:
        cand = {"id": "test-1", "start_sec": 0.0, "end_sec": 5.0}
        out = T.build_candidate_transcript("https://www.youtube.com/watch?v=TESTVID",
                                           "run-test", cand)
        assert out["fr"]["available"] is True
        assert out["fr"]["provider"] == "operator"
        assert "opérateur" in out["fr"]["lines"][0]["text"]
    finally:
        f.unlink(missing_ok=True)
        # purge du cache écrit pendant le test
        cache = T._cache_path("run-test", "test-1", "fr")
        cache.unlink(missing_ok=True)


def test_whisper_absent_falls_back_clean(monkeypatch):
    """Sans faster-whisper ni réseau : notes propres, jamais d'exception."""
    if T._whisper_available():
        monkeypatch.setattr(T, "_download_audio_short",
                            lambda *a, **k: (_ for _ in ()).throw(RuntimeError("offline test")))
        monkeypatch.setattr(T, "_whisper_cues",
                            lambda *a, **k: (_ for _ in ()).throw(RuntimeError("offline test")))
    monkeypatch.setattr(T, "_download_subs",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("offline test")))
    cand = {"id": "tw-1", "start_sec": 0.0, "end_sec": 3.0}
    out = T.build_candidate_transcript("https://www.youtube.com/watch?v=NOTAREALVID999",
                                       "run-tw2", cand)
    assert "available" in out
    if not out["available"]:
        assert out.get("note") or out.get("whisper_note")


def test_slice_lines_window():
    cues = [
        {"start": 0.0, "end": 4.0, "text": "aaaa"},
        {"start": 5.0, "end": 9.0, "text": "bbbb"},
    ]
    lines = T._slice_lines(cues, 5.0, 9.0)
    assert len(lines) == 1 and lines[0]["text"] == "bbbb"
    assert lines[0]["t_rel"] == 0.0
