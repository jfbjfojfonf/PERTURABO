"""Tests F00C_VOX — hors-ligne (aucun réseau), style importlib du repo."""
import importlib.util
import json
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / "f00c_vox.py"
spec = importlib.util.spec_from_file_location("f00c_vox", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


FAKE_YT_HTML = """
<html><head>
<meta name="title" content="GRAND DEBAT LIVE — 6 heures">
<script>var ytInitialPlayerResponse = {
  "playabilityStatus": {"status": "OK"},
  "videoDetails": {
    "title": "GRAND DEBAT LIVE — 6 heures",
    "author": "CanalExemple",
    "lengthSeconds": "21600",
    "viewCount": "152300",
    "isLiveContent": true
  }
};</script>
</head><body></body></html>
"""


def test_resolve_source_local_file(tmp_path):
    media = tmp_path / "source.mp4"
    media.write_bytes(b"0000")
    resolved = module.resolve_source(str(media))
    assert resolved["kind"] == "local"
    assert resolved["platform"] == "local"


def test_resolve_source_youtube_variants():
    for url in (
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtu.be/dQw4w9WgXcQ",
        "https://www.youtube.com/live/dQw4w9WgXcQ?feature=share",
    ):
        resolved = module.resolve_source(url)
        assert resolved["kind"] == "youtube_video"
        assert resolved["id"] == "dQw4w9WgXcQ"


def test_resolve_source_twitch_vod_and_channel():
    vod = module.resolve_source("https://www.twitch.tv/videos/2864600351")
    assert vod == {"kind": "twitch_video", "platform": "twitch", "id": "2864600351",
                   "url": "https://www.twitch.tv/videos/2864600351"}
    chan = module.resolve_source("https://www.twitch.tv/joe_bartolozzi")
    assert chan["kind"] == "twitch_channel"
    assert chan["id"] == "joe_bartolozzi"


def test_resolve_source_rejects_unknown():
    try:
        module.resolve_source("https://vimeo.com/123456")
    except ValueError as exc:
        assert "non supportée" in str(exc)
    else:
        raise AssertionError("Une plateforme inconnue doit être rejetée")


def test_fetch_youtube_metadata_detects_live(tmp_path, monkeypatch):
    fake = tmp_path / "page.html"
    fake.write_text(FAKE_YT_HTML, encoding="utf-8")
    monkeypatch.setattr(module, "_http_get", lambda url, timeout=15.0: fake.read_bytes())
    meta = module.fetch_youtube_metadata("dQw4w9WgXcQ")
    assert meta["is_live"] is True
    assert meta["title"] == "GRAND DEBAT LIVE — 6 heures"
    assert meta["duration_seconds"] == "21600"
    assert meta["view_count"] == "152300"
    assert meta["playable"] is True


def test_fetch_twitch_metadata_vod(tmp_path, monkeypatch):
    payload = {"data": {"user": {"id": "2864600351", "title": "Ranked FINAL",
                                 "lengthSeconds": 14400, "viewCount": 84520,
                                 "owner": {"login": "canalex", "displayName": "CanalEx"},
                                 "game": {"displayName": "Just Chatting"},
                                 "createdAt": "2026-09-01T10:00:00Z"}}}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return json.dumps(payload).encode("utf-8")

    monkeypatch.setattr(module.urllib.request, "urlopen", lambda req, timeout=15: FakeResponse())
    meta = module.fetch_twitch_metadata("twitch_video", "2864600351")
    assert meta["title"] == "Ranked FINAL"
    assert meta["channel"] == "canalex"
    assert meta["is_live"] is False


# ─── Livraison B : barre rouge, fusion, webhook ───

REPLAYED_YTDLP_JSON = {
    "id": "dQw4w9WgXcQ", "title": "Vidéo test",
    "heatmap": [
        {"start_time": 0.0, "end_time": 20.0, "value": 0.2},
        {"start_time": 20.0, "end_time": 40.0, "value": 0.9},
        {"start_time": 40.0, "end_time": 60.0, "value": 0.4},
    ],
}


def test_fetch_replayed_curve_parses_ytdlp_heatmap(tmp_path, monkeypatch):
    calls = []

    def fake_run(attempt, capture_output=True, text=True, timeout=None):
        calls.append(attempt)
        class P:
            returncode = 0
            stdout = json.dumps(REPLAYED_YTDLP_JSON)
            stderr = ""
        return P()

    monkeypatch.setattr(module.shutil, "which", lambda _: "/usr/bin/yt-dlp")
    monkeypatch.setattr(module.subprocess, "run", fake_run)
    curve, note = module.fetch_replayed_curve("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    assert len(calls) == 1  # premier essai de l'escalier suffit
    assert note is None
    assert curve[1] == {"start": 20.0, "end": 40.0, "value": 0.9}


def test_fetch_replayed_curve_empty_note_never_silent(tmp_path, monkeypatch):
    monkeypatch.setattr(module.shutil, "which", lambda _: None)  # yt-dlp absent
    curve, note = module.fetch_replayed_curve("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    assert curve == []
    assert note and "yt-dlp" in note  # jamais de silence


def test_fuse_heatmaps_with_replayed():
    video = [
        {"bucket": 0, "start_sec": 0.0, "end_sec": 20.0, "attention": 0.5, "attention_norm": 1.0},
        {"bucket": 1, "start_sec": 20.0, "end_sec": 40.0, "attention": 0.25, "attention_norm": 0.5},
    ]
    replayed = [
        {"start": 0.0, "end": 20.0, "value": 1.0},
        {"start": 20.0, "end": 40.0, "value": 0.5},
    ]
    fused = module.fuse_heatmaps(video, replayed)
    assert fused[0]["replayed_applied"] is True
    assert fused[0]["replayed_norm"] == 1.0
    assert fused[0]["fused_norm"] == round(0.6 * 1.0 + 0.4 * 1.0, 6)
    assert fused[1]["replayed_norm"] == 0.5
    assert fused[1]["fused_norm"] == round(0.6 * 0.5 + 0.4 * 0.5, 6)


def test_fuse_heatmaps_degrades_cleanly_without_replayed():
    video = [
        {"bucket": 0, "start_sec": 0.0, "end_sec": 20.0, "attention": 0.5, "attention_norm": 0.8},
    ]
    fused = module.fuse_heatmaps(video, [])
    assert fused[0]["replayed_applied"] is False
    assert fused[0]["fused_norm"] == 0.8


def test_build_webhook_payload_canonical():
    manifest = {
        "generated_at": "2026-09-12T10:00:00+00:00",
        "status": "full",
        "source": {"reference": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                   "platform": "youtube", "content_type": "video", "id": "dQw4w9WgXcQ"},
        "attention_heatmap": [{"bucket": 0, "start_sec": 0.0, "end_sec": 1.0,
                               "attention": 0.5, "attention_norm": 1.0}],
        "replayed_curve": [{"start": 0.0, "end": 1.0, "value": 0.7}],
        "fused_heatmap": [],
    }
    payload = module.build_webhook_payload(manifest, candidates=[{"id": "clip_01", "rank": 1}])
    assert payload["run_id"] and payload["run_id"].startswith("f00c_")
    assert payload["mode"] == "vod"
    assert payload["status"] == "full"
    assert payload["candidates"][0]["id"] == "clip_01"
    assert payload["heatmap"][0]["attention_norm"] == 1.0
    assert payload["replayed_curve"][0]["value"] == 0.7
    assert "pushed_at" in payload


def test_build_webhook_payload_v2_enrichment():
    """Audit 2026-09-13 : le dashboard ne devine plus — candidats enrichis + couverture."""
    manifest = {
        "generated_at": "2026-09-13T10:00:00+00:00",
        "status": "full",
        "source": {"reference": "https://www.youtube.com/watch?v=cP8vli4kfhs",
                   "platform": "youtube", "content_type": "video", "id": "cP8vli4kfhs"},
        "attention_heatmap": [
            {"bucket": 0, "start_sec": 0.0, "end_sec": 10.0,
             "attention": 0.2, "attention_norm": 0.4},
            {"bucket": 1, "start_sec": 10.0, "end_sec": 20.0,
             "attention": 0.8, "attention_norm": 1.0},
        ],
        "replayed_note": "pas de Most Replayed exposé (test)",
        "fused_heatmap": [],
        "raw_data": {"metadata_raw": {"duration": 20}},
    }
    raw_candidate = {"candidate_id": "voxc-1", "start_sec": 10.0, "end_sec": 20.0,
                     "duration_sec": 10.0, "signal_type": "platform_heat",
                     "signal_intensity": 1.0}
    payload = module.build_webhook_payload(manifest, candidates=[raw_candidate])
    c = payload["candidates"][0]
    # Champs que le dashboard lit — verrouillés par contrat
    assert c["id"] == "voxc-1" and c["rank"] == 1
    assert c["score"] == 100.0
    assert c["start_label"] == "0:10" and c["end_label"] == "0:20"
    assert c["vs_mean_pct"] == 42.9          # intensité 1.0 vs moyenne 0.7 → +42,9 %
    assert "shorts" in c["platforms"]
    # Couverture analysée — le doute « 8 min sur plus » ne revient jamais
    assert payload["duration_total_sec"] == 20
    assert payload["analyzed_duration_sec"] == 20.0
    assert payload["coverage_pct"] == 100.0
    assert payload["mean_attention"] == 0.7
    assert payload["replayed_note"] == "pas de Most Replayed exposé (test)"


def test_fmt_clock_labels():
    assert module._fmt_clock(0) == "0:00"
    assert module._fmt_clock(8.563) == "0:09"      # arrondi
    assert module._fmt_clock(453.84) == "7:34"
    assert module._fmt_clock(3661) == "1:01:01"
    assert module._fmt_clock(None) == "?"


def test_push_webhook_sends_token_and_payload(tmp_path, monkeypatch):
    captured = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        status = 200

        def read(self):
            return b""

    def fake_urlopen(request, timeout=None):
        captured["url"] = request.full_url
        captured["headers"] = dict(request.headers)
        captured["body"] = request.data
        return FakeResponse()

    monkeypatch.setattr(module.urllib.request, "urlopen", fake_urlopen)
    ok = module.push_webhook("https://war-room.example/hook", {"run_id": "x"}, token="SECRET")
    assert ok is True
    assert captured["url"] == "https://war-room.example/hook"
    assert any(v == "SECRET" for v in captured["headers"].values())
    assert json.loads(captured["body"].decode()) == {"run_id": "x"}


def test_top_viral_segments_spacing():
    heatmap = [
        {"bucket": i, "start_sec": float(i), "end_sec": float(i + 1),
         "attention": 0.1, "attention_norm": 0.1}
        for i in range(20)
    ]
    heatmap[3]["attention"] = 1.0   # pic 1
    heatmap[4]["attention"] = 0.95  # trop proche du pic 1 (1 s d'écart < 5 s)
    heatmap[15]["attention"] = 0.8  # pic 2
    segments = module.top_viral_segments(heatmap, count=2, min_gap_seconds=5.0)
    assert [seg["start_sec"] for seg in segments] == [3.0, 15.0]
    assert segments[0]["rank"] == 1


def test_analyze_full_pipeline_local(tmp_path):
    """Pipeline complet sur un fichier local : manifeste écrit, schéma F00C."""
    import shutil as _shutil
    if _shutil.which("ffmpeg") is None:
        media = tmp_path / "clip.mp4"
        media.write_bytes(b"\x00" * 64)
        out = tmp_path / "live_analysis.json"
        try:
            module.analyze(str(media), out)
        except Exception:
            return  # ffmpeg absent : comportement dégradé acceptable hors CI
        return
    # ffmpeg présent : on génère une mini vidéo synthétique (2 s, 4 fps)
    media = tmp_path / "clip.mp4"
    import subprocess
    cmd = ["ffmpeg", "-y", "-v", "error", "-f", "lavfi",
           "-i", "testsrc=duration=2:size=64x64:rate=4",
           "-pix_fmt", "yuv420p", str(media)]
    subprocess.check_call(cmd)
    out = tmp_path / "live_analysis.json"
    manifest = module.analyze(str(media), out, heatmap_buckets=10)
    assert out.exists()
    assert manifest["schema_version"] == "perturabo.voxc.v1"
    assert manifest["source"]["platform"] == "local"
    assert manifest["status"] == "full"
    assert len(manifest["attention_heatmap"]) == 10
    assert manifest["viral_segments"], "des segments viraux doivent sortir de la heatmap"
    assert manifest["raw_data"]["metadata_raw"]["file"].endswith("clip.mp4")
    assert manifest["pipeline"]["name"] == "F00C_VOX"
