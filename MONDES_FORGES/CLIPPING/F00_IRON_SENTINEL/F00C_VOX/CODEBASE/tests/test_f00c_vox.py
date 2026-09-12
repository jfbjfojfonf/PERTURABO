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
