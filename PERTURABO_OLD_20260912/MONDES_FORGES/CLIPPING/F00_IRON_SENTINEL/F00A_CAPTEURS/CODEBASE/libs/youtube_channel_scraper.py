"""
youtube_channel_scraper.py — Scrap de chaînes YouTube pour la base de savoir
Sous-commande CAPTEURS --scrap-youtube. Commandité par le Warsmith.
Capture transcripts + métadonnées enrichies (vues, subs, outlier) dans
ARCHIVUM/knowledge_base/transcripts/<channel_slug>/<video_id>.json —
même schéma que le core YOUTUBE. Reprise possible (vidéos déjà capturées
ignorées).
"""

import json
import os
import re
import subprocess
import time
import urllib.request
from datetime import datetime, timezone

YTDLP_OPTS = ["--no-warnings", "--no-playlist"]
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 " \
     "(KHTML, like Gecko) Chrome/125.0 Safari/537.36"


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def slugify_channel(url: str, channel_name: str | None = None) -> str:
    m = re.search(r"youtube\.com/@([\w\-\.]+)", url)
    if m:
        return m.group(1).lower().replace(".", "-")
    m = re.search(r"youtube\.com/channel/([\w\-]+)", url)
    if m:
        return m.group(1).lower()
    if channel_name:
        return re.sub(r"[^a-z0-9]+", "_", channel_name.lower()).strip("_")
    return "channel"


def list_channel_videos(channel_url: str) -> list[dict]:
    """Liste les vidéos via yt-dlp --flat-playlist (rapide, sans download)."""

    cmd = ["yt-dlp", "--flat-playlist"] + YTDLP_OPTS + [
        "--print", "%(id)s\t%(title)s\t%(url)s\t%(duration)s", channel_url]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        raise RuntimeError(f"yt-dlp flat-playlist échoué: "
                           f"{result.stderr.strip()[:300]}")
    videos = []
    for line in result.stdout.strip().split("\n"):
        if not line:
            continue
        parts = line.split("\t")
        if len(parts) >= 3:
            videos.append({
                "video_id": parts[0],
                "title": parts[1],
                "url": parts[2],
                "duration": float(parts[3]) if len(parts) > 3 and parts[3] != "NA"
                             else None,
            })
    return videos


def fetch_channel_meta(channel_url: str) -> dict:
    """Métadonnées de la chaîne (nom, id, url, subs) via une vidéo échantillon."""

    try:
        cmd = ["yt-dlp", "--dump-single-json"] + YTDLP_OPTS + [
            "--playlist-items", "0", "--flat-playlist", channel_url]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode == 0 and result.stdout.strip():
            data = json.loads(result.stdout)
            return {
                "name": data.get("channel") or data.get("uploader"),
                "id": data.get("channel_id"),
                "url": data.get("channel_url"),
                "subscriber_count": data.get("channel_follower_count"),
            }
    except Exception:
        pass
    return {}


def fetch_transcript(video_id: str, languages: list[str]) -> dict:
    """Transcript avec fallbacks : api → yt-dlp --write-subs → timedtext."""

    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        api = YouTubeTranscriptApi()
        transcript = api.fetch(video_id, languages=languages)
        segments = [{"start": s.start, "duration": s.duration,
                     "text": s.text} for s in transcript]
        if segments:
            return {"status": "OK", "segments": segments,
                    "text": " ".join(s["text"].strip() for s in segments)}
    except Exception as e:
        last_err = str(e)[:200]

    try:
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            outtmpl = os.path.join(tmpdir, "sub")
            cmd = ["yt-dlp", "--write-subs", "--write-auto-subs",
                   "--sub-lang", ",".join(languages), "--sub-format", "json3",
                   "--skip-download"] + YTDLP_OPTS + [
                "-o", outtmpl, f"https://www.youtube.com/watch?v={video_id}"]
            subprocess.run(cmd, capture_output=True, text=True, timeout=180)
            sub_file = None
            for root, _dirs, files in os.walk(tmpdir):
                for f in files:
                    if f.endswith(".json3"):
                        sub_file = os.path.join(root, f)
                        break
            if sub_file:
                with open(sub_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                events = [e for e in data.get("events", [])
                          if e.get("segs") and "tStartMs" in e]
                segments = [{"start": e["tStartMs"] / 1000.0,
                             "duration": (events[i + 1]["tStartMs"] - e["tStartMs"])
                             / 1000.0 if i + 1 < len(events) else 2.0,
                             "text": "".join(s.get("utf8", "") for s in e["segs"])}
                            for i, e in enumerate(events)]
                if segments:
                    return {"status": "OK", "segments": segments,
                            "text": " ".join(s["text"].strip() for s in segments)}
    except Exception as e:
        last_err = f"{last_err} | yt-dlp: {str(e)[:100]}"

    return {"status": "FAILED", "error": last_err, "segments": [], "text": ""}


def fetch_video_meta(video_id: str) -> dict:
    """Métadonnées vidéo via yt-dlp --dump-single-json."""

    cmd = ["yt-dlp", "--dump-single-json", "--no-warnings", "--no-playlist",
           "--skip-download", f"https://www.youtube.com/watch?v={video_id}"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0 or not result.stdout.strip():
            return {}
        data = json.loads(result.stdout)
        return {
            "title": data.get("title"),
            "description": (data.get("description") or "")[:4000],
            "view_count": data.get("view_count"),
            "like_count": data.get("like_count"),
            "comment_count": data.get("comment_count"),
            "thumbnail": data.get("thumbnail"),
            "upload_date": data.get("upload_date"),
            "duration": data.get("duration"),
            "tags": data.get("tags", [])[:20],
            "channel": data.get("channel"),
            "channel_id": data.get("channel_id"),
            "channel_url": data.get("channel_url"),
            "channel_follower_count": data.get("channel_follower_count"),
        }
    except Exception:
        return {}


def outlier_score(views, subs) -> float | None:
    if not views or not subs or subs == 0:
        return None
    return round(views / subs, 4)


class YoutubeChannelScraper:
    """Scrape une chaîne YouTube commanditée par le Warsmith."""

    def __init__(self, channel_url: str, out_dir: str,
                 max_videos: int = 20, languages: list[str] = None,
                 rate_limit_sec: float = 1.0):
        self.channel_url = channel_url
        self.out_dir = out_dir
        self.max_videos = max_videos
        self.languages = languages or ["fr", "en", "en-US"]
        self.rate_limit_sec = rate_limit_sec

    # ------------------------------------------------------------------
    def scrape(self) -> dict:
        videos = list_channel_videos(self.channel_url)
        if not videos:
            raise RuntimeError("aucune vidéo listée pour cette chaîne")

        channel_meta = fetch_channel_meta(self.channel_url)
        slug = slugify_channel(self.channel_url, channel_meta.get("name"))
        target = os.path.join(self.out_dir, slug)
        os.makedirs(target, exist_ok=True)

        captured, skipped, failed = [], [], []
        for v in videos[: self.max_videos]:
            out_path = os.path.join(target, f"{v['video_id']}.json")
            if os.path.exists(out_path):
                skipped.append(v["video_id"])
                continue
            captured.append(self._capture_video(v, channel_meta, out_path))
            time.sleep(self.rate_limit_sec)

        return {
            "channel_url": self.channel_url,
            "channel_slug": slug,
            "channel_name": channel_meta.get("name"),
            "videos_listed": len(videos),
            "max_videos": self.max_videos,
            "captured": captured,
            "skipped": skipped,
            "failed": failed,
            "out_dir": target,
            "scraped_at": now_iso(),
        }

    def _capture_video(self, v: dict, channel_meta: dict, out_path: str) -> dict:
        video_id = v["video_id"]
        transcript_data = fetch_transcript(video_id, self.languages)
        meta = fetch_video_meta(video_id)
        if transcript_data["status"] != "OK":
            failure = {"video_id": video_id, "error": transcript_data["error"]}
            return failure

        views = meta.get("view_count") or 0
        subs = meta.get("channel_follower_count") or channel_meta.get(
            "subscriber_count") or 0
        specimen = {
            "video_id": video_id,
            "title": meta.get("title") or v.get("title"),
            "channel": meta.get("channel") or channel_meta.get("name"),
            "channel_id": meta.get("channel_id") or channel_meta.get("id"),
            "channel_url": meta.get("channel_url") or channel_meta.get("url"),
            "subscriber_count": subs,
            "view_count": views,
            "outlier_score": outlier_score(views, subs),
            "thumbnail": meta.get("thumbnail"),
            "upload_date": meta.get("upload_date"),
            "duration": meta.get("duration") or v.get("duration"),
            "transcript": {
                "text": transcript_data["text"],
                "segments": transcript_data["segments"],
                "language": self.languages[0],
                "status": "OK",
                "segment_count": len(transcript_data["segments"]),
            },
            "capture_meta": {
                "captured_at": now_iso(),
                "tool": "CAPTEURS --scrap-youtube",
            },
        }
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(specimen, f, ensure_ascii=False, indent=2)
        return {"video_id": video_id, "title": specimen["title"],
                "segments": specimen["transcript"]["segment_count"]}
