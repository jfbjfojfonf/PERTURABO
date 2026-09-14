#!/usr/bin/env python3
"""WAR ROOM — Transcripts bilingues FR/EN par candidat.

Principe : la vidéo source (YouTube VOD) possède presque toujours des
sous-titres auto-générés dans plusieurs langues. On les télécharge UNE fois
via yt-dlp (gratuit, sans clé, timing exact de YouTube), on les découpe par
candidat et on met en cache dans docs/data/transcripts/{run_id}/.

Contrat de cache (par langue disponible) :
    docs/data/transcripts/{run_id}/{candidate_id}.{lang}.json
        {"candidate_id", "run_id", "lang", "source", "window",
         "lines": [{"t_abs", "t_rel", "end_rel", "text"}]}

Aucune dépendance lourde : yt-dlp (déjà présent), stdlib seulement.
Si la plateforme ne fournit ni sous-titres FR ni EN → disponible=False et
message propre (jamais de crash côté dashboard).
"""
from __future__ import annotations

import hashlib
import html
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TRANSCRIPTS_DIR = REPO_ROOT / "docs" / "data" / "transcripts"
SUBS_DIR = TRANSCRIPTS_DIR / "_subs"
VENDOR_DIR = Path(__file__).resolve().parent / "_vendor"  # wheel yt-dlp vendue (autonome)
YT_DLP = "yt-dlp"
DOWNLOAD_TIMEOUT = 180  # secondes — sous-titres seulement, jamais la vidéo
COOLDOWN_SEC = 600      # après un rate-limit YouTube, on laisse souffler 10 min

LANG_GLOB = "fr,fr-*,en,en-*"  # français + anglais (manuels puis auto)


def _ts_to_sec(stamp: str) -> float:
    """'01:02:03.360' ou '02:03.360' → secondes."""
    parts = stamp.strip().split(":")
    try:
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
        if len(parts) == 2:
            return int(parts[0]) * 60 + float(parts[1])
        return float(parts[0])
    except (ValueError, IndexError):
        return 0.0


def _clean_cue_text(raw: str) -> str:
    text = re.sub(r"<[^>]+>", "", raw)          # tags VTT/HTML (<c>, <00:00:01.359>…)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def parse_vtt_cues(vtt_text: str) -> list[dict]:
    """Extrait les cues [{start,end,text}] d'un fichier VTT (manuel ou auto)."""
    cues: list[dict] = []
    pattern = re.compile(
        r"^(\d{1,2}:\d{2}:\d{2}\.\d{3}|\d{1,2}:\d{2}\.\d{3})"
        r"\s*-->\s*"
        r"(\d{1,2}:\d{2}:\d{2}\.\d{3}|\d{1,2}:\d{2}\.\d{3})")
    lines = vtt_text.splitlines()
    i = 0
    while i < len(lines):
        m = pattern.match(lines[i].strip())
        if not m:
            i += 1
            continue
        start, end = _ts_to_sec(m.group(1)), _ts_to_sec(m.group(2))
        i += 1
        text_lines: list[str] = []
        while i < len(lines) and lines[i].strip() and "-->" not in lines[i]:
            text_lines.append(lines[i])
            i += 1
        text = _clean_cue_text(" ".join(text_lines))
        if text and end > start:
            cues.append({"start": start, "end": end, "text": text})
    return cues


def _merge_duplicates(cues: list[dict]) -> list[dict]:
    """Les sous-titres auto se chevauchent (rolling captions) : on dédoublonne."""
    out: list[dict] = []
    for cue in cues:
        prev = out[-1] if out else None
        if prev and prev["text"] == cue["text"] and cue["start"] < prev["end"] + 0.5:
            prev["end"] = max(prev["end"], cue["end"])
            continue
        if prev and prev["text"] in cue["text"] and cue["start"] < prev["end"] + 0.5:
            # ligne partielle répétée puis complétée : on remplace
            prev["text"] = cue["text"]
            prev["end"] = max(prev["end"], cue["end"])
            continue
        out.append(dict(cue))
    return out


def _chunk_lines(cues: list[dict], max_chars: int = 90, max_span: float = 6.0) -> list[dict]:
    """Regroupe les cues en blocs lisibles (≈1 phrase) pour l'affichage opérateur."""
    lines: list[dict] = []
    cur: dict | None = None
    for cue in cues:
        if cur is not None \
                and len(cur["text"]) + len(cue["text"]) + 1 <= max_chars \
                and cue["end"] - cur["start"] <= max_span:
            cur["text"] += " " + cue["text"]
            cur["end"] = cue["end"]
            continue
        cur = {"start": cue["start"], "end": cue["end"], "text": cue["text"]}
        lines.append(cur)
    return lines


def _vendor_wheel() -> Path | None:
    """La wheel yt-dlp vendue dans le repo (import direct via PYTHONPATH)."""
    wheels = sorted(VENDOR_DIR.glob("yt_dlp-*.whl"))
    return wheels[-1] if wheels else None


def _resolve_yt_dlp() -> tuple[list[str], dict]:
    """Trouve un yt-dlp exécutable — wheel vendue, PATH, HOME, ou module pip.

    Retour (cmd, env) : la commande complète et l'environnement à injecter
    (PYTHONPATH vers la wheel vendue pour l'exécution `python -m yt_dlp`).
    """
    env = dict(os.environ)
    wheel = _vendor_wheel()
    if wheel is not None:
        # priorité : la copie vendue dans le repo (aucune dépendance externe)
        env["PYTHONPATH"] = str(wheel) + os.pathsep + env.get("PYTHONPATH", "")
        return [sys.executable, "-m", "yt_dlp"], env
    env_path = os.environ.get("YT_DLP_PATH")
    if env_path and Path(env_path).is_file():
        return [env_path], env
    found = shutil.which(YT_DLP)
    if found:
        return [found], env
    candidates = [Path.home() / ".local" / "bin" / YT_DLP]
    candidates += sorted(Path("/home").glob("*/.local/bin/yt-dlp"))
    for cand in candidates:
        if cand.is_file():
            return [str(cand)], env
    return [sys.executable, "-m", "yt_dlp"], env  # dernier recours (module pip)


def _download_subs(source_url: str) -> Path:
    """Télécharge (une fois) les sous-titres FR/EN de la source. → dossier VTT."""
    key = hashlib.sha1(source_url.encode()).hexdigest()[:12]
    out_dir = SUBS_DIR / key
    vtt_present = list(out_dir.glob("*.vtt")) if out_dir.exists() else []
    if vtt_present:
        return out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    cooldown = out_dir / ".cooldown"
    if cooldown.exists():  # rate-limit actif : échec immédiat et lisible
        try:
            until = float(cooldown.read_text().strip())
            if time.time() < until:
                remaining = int((until - time.time()) / 60) + 1
                raise RuntimeError(
                    f"YouTube limite le débit de cette IP — nouvel essai dans ~{remaining} min")
            cooldown.unlink()
        except ValueError:
            cooldown.unlink(missing_ok=True)
    last_err = ""
    for attempt in range(3):  # 429 transitoire côté YouTube → backoff et retry
        if attempt:
            time.sleep(20 * attempt)
        cmd, cmd_env = _resolve_yt_dlp()
        cmd = cmd + [
            "--skip-download", "--write-subs", "--write-auto-subs",
            "--sub-langs", LANG_GLOB, "--sub-format", "vtt/srt/best",
            "-o", str(out_dir / "src"), source_url]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True,
                                  timeout=DOWNLOAD_TIMEOUT, env=cmd_env)
        except FileNotFoundError:
            raise RuntimeError("yt-dlp introuvable sur ce poste — transcripts indisponibles")
        except subprocess.TimeoutExpired:
            raise RuntimeError("téléchargement des sous-titres trop long (>180 s)")
        if list(out_dir.glob("*.vtt")):
            return out_dir
        last_err = (proc.stderr or "").strip().splitlines()[-1:] and \
            (proc.stderr or "").strip().splitlines()[-1] or ""
    if "429" in last_err or "Too Many Requests" in last_err:
        (out_dir / ".cooldown").write_text(str(time.time() + COOLDOWN_SEC))
        raise RuntimeError(
            f"YouTube limite le débit de cette IP — nouvel essai dans ~{COOLDOWN_SEC // 60} min")
    raise RuntimeError("aucun sous-titre FR/EN exposé par la plateforme"
                       + (f" ({last_err})" if last_err else ""))


def _load_lang_cues(subs_dir: Path, lang_prefix: str) -> list[dict] | None:
    """Charge la meilleure piste d'une langue (manuel prioritaire sur auto)."""
    candidates = sorted(
        subs_dir.glob(f"src.{lang_prefix}*.vtt"),
        key=lambda p: (".auto." in p.name, len(p.name)),  # manuel d'abord
    )
    for path in candidates:
        try:
            cues = parse_vtt_cues(path.read_text(encoding="utf-8", errors="replace"))
        except OSError:
            continue
        if cues:
            return _merge_duplicates(cues)
    return None


def _slug(candidate_id: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]", "_", candidate_id)


def _cache_path(run_id: str, candidate_id: str, lang: str) -> Path:
    return TRANSCRIPTS_DIR / _slug(run_id) / f"{_slug(candidate_id)}.{lang}.json"


def build_candidate_transcript(source_url: str, run_id: str, candidate: dict) -> dict:
    """Construit (ou relit du cache) le transcript bilingue d'un candidat.

    Retour : {"fr": {...}|None, "en": {...}|None, "available": bool, "note": str}
    Chaque langue : {"available", "lines": [{"t_abs","t_rel","end_rel","text"}]}
    """
    start = float(candidate.get("start_sec") or 0.0)
    end = float(candidate.get("end_sec") or 0.0)
    cand_id = candidate.get("id") or "candidat"

    result: dict = {"fr": None, "en": None, "available": False, "note": ""}
    langs_found = 0
    subs_dir: Path | None = None

    for lang, prefix in (("fr", "fr"), ("en", "en")):
        cache = _cache_path(run_id, cand_id, lang)
        if cache.exists():
            try:
                result[lang] = json.loads(cache.read_text(encoding="utf-8"))
                if result[lang].get("available"):
                    langs_found += 1
                continue
            except (json.JSONDecodeError, OSError):
                pass  # cache corrompu → rebuild
        if subs_dir is None:
            subs_dir = _download_subs(source_url)
        cues = _load_lang_cues(subs_dir, prefix)
        if not cues:
            result[lang] = {"available": False, "lines": []}
            _write_cache(cache, source_url, run_id, cand_id, start, end, lang,
                         False, [])
            continue
        # fenêtre du clip : tout cue qui chevauche [start, end]
        window = [c for c in cues if c["start"] < end and c["end"] > start]
        lines = [{
            "t_abs": round(c["start"], 2),
            "t_rel": round(max(c["start"] - start, 0.0), 2),
            "end_rel": round(min(c["end"], end) - start, 2),
            "text": c["text"],
        } for c in _chunk_lines(window)]
        payload = {"available": bool(lines), "lines": lines}
        result[lang] = payload
        _write_cache(cache, source_url, run_id, cand_id, start, end, lang,
                     bool(lines), lines)
        if lines:
            langs_found += 1

    result["available"] = langs_found > 0
    if not result["available"]:
        result["note"] = ("aucun sous-titre FR/EN disponible pour cette vidéo — "
                          "transcript indisponible pour ce clip")
    elif langs_found == 1:
        missing = "FR" if (result["fr"] is None or not result["fr"]["available"]) else "EN"
        result["note"] = f"sous-titres {missing} indisponibles — une seule langue affichée"
    return result


def _write_cache(path: Path, source_url: str, run_id: str, cand_id: str,
                 start: float, end: float, lang: str, available: bool,
                 lines: list[dict]) -> None:
    doc = {
        "candidate_id": cand_id, "run_id": run_id, "lang": lang,
        "source": source_url, "window": {"start": start, "end": end},
        "available": available, "lines": lines,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")


def self_test() -> int:
    """Test hors-ligne : parsing VTT (manuel + auto avec doublons) + découpage."""
    manual_vtt = """WEBVTT

00:00:00.000 --> 00:00:02.500
Hello everyone and welcome

00:00:02.500 --> 00:00:05.000
today we talk about viral clips
"""
    auto_vtt = """WEBVTT

00:00:00.000 --> 00:00:02.000
Hello everyone

00:00:01.000 --> 00:00:03.000
Hello everyone
and welcome

00:00:03.000 --> 00:00:05.500
let's go
"""
    cues = _merge_duplicates(parse_vtt_cues(manual_vtt))
    assert len(cues) == 2, f"manuel : attendu 2 cues, obtenu {len(cues)}"
    assert cues[0]["text"] == "Hello everyone and welcome"
    auto = _merge_duplicates(parse_vtt_cues(auto_vtt))
    assert auto[0]["text"] == "Hello everyone and welcome", auto[0]
    lines = _chunk_lines(auto)
    assert lines and lines[0]["text"].startswith("Hello everyone")
    # découpage par candidat (fenêtre 1.5 → 5.0)
    window = [c for c in auto if c["start"] < 5.0 and c["end"] > 1.5]
    assert window and window[0]["start"] < 5.0
    print("TRANSCRIPTS SELF-TEST OK")
    return 0


if __name__ == "__main__":
    sys.exit(self_test())
