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
# Source opérateur : la frégate ne dépend plus de YouTube seul — l'opérateur
# dépose ici un transcript complet de la vidéo (SRT/VTT/TXT, FR et/ou EN),
# prioritaire sur tout téléchargement. Autonomie garantie face au rate-limit.
OPERATOR_DIR = REPO_ROOT / "war_room" / "transcripts_in"
# Cookies (Netscape format) — jamais versionnés : l'opérateur dépose ici le
# cookies.txt exporté depuis un navigateur connecté (compte dédié de service).
# Sert uniquement à fiabiliser yt-dlp (rate-limit) — jamais requis pour tourner.
COOKIES_FILE = REPO_ROOT / "war_room" / "cookies.txt"
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


# ── Source opérateur (transcripts_in) ────────────────────────────────────────

def parse_srt_or_vtt(text: str) -> list[dict]:
    """Parse un sous-titrage SRT ou VTT déposé par l'opérateur.

    Tolérant : en-tête WEBVTT optionnel, index numériques SRT ignorés,
    point ou virgule dans les timestamps, blocs séparés par lignes vides.
    """
    cues: list[dict] = []
    pattern = re.compile(
        r"(\d{1,2}:\d{2}:\d{2}[.,]\d{1,3}|\d{1,2}:\d{2}[.,]\d{1,3})"
        r"\s*-->\s*"
        r"(\d{1,2}:\d{2}:\d{2}[.,]\d{1,3}|\d{1,2}:\d{2}[.,]\d{1,3})")
    for block in re.split(r"\n\s*\n", text):
        lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
        # trouve la ligne d'horodatage dans le bloc (index SRT ou en-tête avant)
        idx = next((i for i, ln in enumerate(lines) if "-->" in ln), None)
        if idx is None:
            continue
        m = pattern.search(lines[idx])
        if not m:
            continue
        start, end = _ts_to_sec(m.group(1).replace(",", ".")), \
            _ts_to_sec(m.group(2).replace(",", "."))
        text = _clean_cue_text(" ".join(lines[idx + 1:]))
        if text and end > start:
            cues.append({"start": start, "end": end, "text": text})
    return cues


_TS_LINE = re.compile(r"^\[(\d{1,2}:\d{2}(?::\d{2})?)\]\s*(.*)$")


def parse_plain_text(text: str, sec_per_line: float = 3.0) -> list[dict]:
    """Parse un transcript brut (TXT) déposé par l'opérateur.

    Deux formats reconnus :
    - horodaté : "[00:01:23] texte" ou "[01:23] texte" (export « transcription »
      de YouTube) — fin du cue = début de la ligne suivante, précision exacte ;
    - brut : 1 ligne = 1 cue de `sec_per_line` secondes (fallback).
    """
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines:
        return []
    stamped = [_TS_LINE.match(ln) for ln in lines]
    if sum(1 for m in stamped if m) >= max(2, len(lines) // 2):
        items: list[list] = []
        for ln, m in zip(lines, stamped):
            if m:
                items.append([_ts_to_sec(m.group(1)), _clean_cue_text(m.group(2))])
            elif items:
                items[-1][1] = (items[-1][1] + " " + _clean_cue_text(ln)).strip()
        cues: list[dict] = []
        for i, (start, txt) in enumerate(items):
            if not txt:
                continue
            end = items[i + 1][0] if i + 1 < len(items) else start + sec_per_line
            if end <= start:
                end = start + 0.5
            cues.append({"start": start, "end": end, "text": txt})
        return cues
    cues = []
    for n, line in enumerate(lines):
        clean = _clean_cue_text(line)
        if not clean:
            continue
        cues.append({"start": n * sec_per_line, "end": (n + 1) * sec_per_line,
                     "text": clean})
    return cues


def _operator_files_for(source_url: str) -> dict[str, Path]:
    """Fichiers opérateur pour cette vidéo → {"fr": path?, "en": path?}.

    Convention de nommage : transcripts_in/{video_id}.fr.srt|vtt|txt
    (idem .en) — le video_id est extrait de l'URL YouTube.
    """
    vid = _youtube_video_id(source_url)
    out: dict[str, Path] = {}
    if not vid:
        return out
    for lang in ("fr", "en"):
        for ext in ("srt", "vtt", "txt"):
            p = OPERATOR_DIR / f"{vid}.{lang}.{ext}"
            if p.is_file():
                out[lang] = p
                break
    return out


def _youtube_video_id(source_url: str) -> str:
    m = re.search(r"(?:v=|youtu\.be/|shorts/|embed/)([A-Za-z0-9_-]{6,20})", source_url or "")
    return m.group(1) if m else ""


def _detect_language(text: str) -> str:
    """Détection heuristique FR vs EN (mots fonctionnels) — suffisant ici."""
    low = f" {text.lower()} "
    fr_marks = [" le ", " la ", " les ", " un ", " une ", " des ", " et ",
                " je ", " tu ", " il ", " elle ", " on ", " nous ", " vous ",
                " est ", " pas ", " que ", " qui ", " pour ", " avec ",
                " dans ", " mais ", " c'est ", " j'ai ", " ça ", " oui ",
                " très ", " être ", " fait ", " on "]
    en_marks = [" the ", " a ", " an ", " and ", " or ", " i ", " you ", " he ",
                " she ", " it ", " we ", " they ", " is ", " are ", " was ",
                " not ", " that ", " this ", " with ", " for ", " to ",
                " of ", " don't ", " i'm ", " yeah ", " right ", " know "]
    score_fr = sum(low.count(w) for w in fr_marks)
    score_en = sum(low.count(w) for w in en_marks)
    return "fr" if score_fr >= score_en else "en"


def _load_operator_cues(source_url: str, lang_prefix: str) -> list[dict] | None:
    """Charge le transcript opérateur d'une langue si déposé. Cues dédoublonnés."""
    path = _operator_files_for(source_url).get(lang_prefix)
    if path is None:
        return None
    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    cues = parse_srt_or_vtt(raw) if path.suffix.lower() in (".srt", ".vtt") \
        else parse_plain_text(raw)
    return _merge_duplicates(cues) if cues else None


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


def _with_cookies(cmd: list[str]) -> list[str]:
    """Ajoute --cookies au fichier déposé par l'opérateur, s'il existe."""
    env_path = os.environ.get("YT_DLP_COOKIES_FILE")
    cookie_path = Path(env_path) if env_path else COOKIES_FILE
    if cookie_path.is_file():
        return cmd + ["--cookies", str(cookie_path)]
    return cmd


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
        cmd = _with_cookies(cmd + [
            "--skip-download", "--write-subs", "--write-auto-subs",
            "--sub-langs", LANG_GLOB, "--sub-format", "vtt/srt/best",
            "-o", str(out_dir / "src"), source_url])
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


# ── Filet de sécurité Whisper (transcription locale, optionnelle) ───────────

def _whisper_available() -> bool:
    try:
        import faster_whisper  # noqa: F401,PLC0415 — import paresseux, optionnel
        return True
    except ImportError:
        return False


def _download_audio_short(source_url: str, timeout: int = 90) -> Path:
    """Télécharge la piste audio seule (fenêtre courte, jamais bloquant).

    Si le téléchargement dépasse `timeout` → RuntimeError lisible ; le fichier
    partiel sera repris au prochain passage (préchauffage en fond).
    """
    key = hashlib.sha1(source_url.encode()).hexdigest()[:12]
    out_dir = SUBS_DIR / key
    out_dir.mkdir(parents=True, exist_ok=True)
    existing = sorted(out_dir.glob("audio.*"))
    if existing:
        return existing[0]
    cooldown = out_dir / ".cooldown"
    if cooldown.exists():
        try:
            until = float(cooldown.read_text().strip())
            if time.time() < until:
                raise RuntimeError("rate-limit actif — audio pas encore téléchargeable")
            cooldown.unlink()
        except ValueError:
            cooldown.unlink(missing_ok=True)
    cmd, cmd_env = _resolve_yt_dlp()
    cmd = _with_cookies(cmd + ["-f", "bestaudio", "-o", str(out_dir / "audio.%(ext)s"), source_url])
    try:
        subprocess.run(cmd, capture_output=True, text=True,
                       timeout=timeout, env=cmd_env)
    except subprocess.TimeoutExpired:
        raise RuntimeError("audio pas encore prêt — le préchauffage le récupère en fond")
    except FileNotFoundError:
        raise RuntimeError("yt-dlp introuvable — audio indisponible")
    audio = sorted(out_dir.glob("audio.*"))
    if not audio:
        raise RuntimeError("téléchargement audio impossible (plateforme)")
    return audio[0]


def _whisper_cues(source_url: str, sec_per_cue: float = 2.0) -> list[dict]:
    """Transcrit l'audio localement (faster-whisper CPU) → cues horodatés.

    Une seule exécution par vidéo : le résultat est mis en cache en VTT
    (audio.whisper.vtt) et relu ensuite comme n'importe quel sous-titre.
    """
    if not _whisper_available():
        raise RuntimeError("Whisper non installé sur ce poste — filet inactif")
    key = hashlib.sha1(source_url.encode()).hexdigest()[:12]
    out_dir = SUBS_DIR / key
    cache_vtt = out_dir / "audio.whisper.vtt"
    if cache_vtt.is_file():
        cues = parse_vtt_cues(cache_vtt.read_text(encoding="utf-8", errors="replace"))
        if cues:
            return _merge_duplicates(cues)
    from faster_whisper import WhisperModel  # noqa: PLC0415 — déjà vérifié dispo
    audio_path = _download_audio_short(source_url)
    model = WhisperModel("base", device="cpu", compute_type="int8")
    segments, _info = model.transcribe(str(audio_path), vad_filter=True)
    lines = ["WEBVTT", ""]
    for seg in segments:
        def _stamp(t: float) -> str:
            h, rem = divmod(t, 3600)
            m, s = divmod(rem, 60)
            return f"{int(h):02d}:{int(m):02d}:{s:06.3f}"
        text = _clean_cue_text(seg.text or "")
        if not text:
            continue
        lines.append(f"{_stamp(seg.start)} --> {_stamp(seg.end)}")
        lines.append(text)
        lines.append("")
    cache_vtt.write_text("\n".join(lines), encoding="utf-8")
    cues = parse_vtt_cues(cache_vtt.read_text(encoding="utf-8", errors="replace"))
    return _merge_duplicates(cues)


def _cache_path(run_id: str, candidate_id: str, lang: str) -> Path:
    return TRANSCRIPTS_DIR / _slug(run_id) / f"{_slug(candidate_id)}.{lang}.json"


def _slice_lines(cues: list[dict], start: float, end: float) -> list[dict]:
    """Découpe des cues dans la fenêtre [start, end] du clip → lignes affichables."""
    window = [c for c in cues if c["start"] < end and c["end"] > start]
    return [{
        "t_abs": round(c["start"], 2),
        "t_rel": round(max(c["start"] - start, 0.0), 2),
        "end_rel": round(min(c["end"], end) - start, 2),
        "text": c["text"],
    } for c in _chunk_lines(window)]


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
    operator = _operator_files_for(source_url)
    if operator:
        result["operator_sources"] = {k: p.name for k, p in operator.items()}

    for lang, prefix in (("fr", "fr"), ("en", "en")):
        cache = _cache_path(run_id, cand_id, lang)

        # 1) source opérateur — prioritaire, jamais écrasée par un cache négatif
        if lang in operator:
            cues = _load_operator_cues(source_url, prefix)
            if cues:
                lines = _slice_lines(cues, start, end)
                result[lang] = {"available": bool(lines), "lines": lines,
                                "provider": "operator"}
                _write_cache(cache, source_url, run_id, cand_id, start, end,
                             lang, bool(lines), lines, provider="operator")
                if lines:
                    langs_found += 1
                continue
            # fichier présent mais illisible → on retombe sur YouTube

        # 2) cache (résultat d'un précédent téléchargement YouTube)
        if cache.exists():
            try:
                result[lang] = json.loads(cache.read_text(encoding="utf-8"))
                if result[lang].get("available"):
                    langs_found += 1
                continue
            except (json.JSONDecodeError, OSError):
                pass  # cache corrompu → rebuild

        # 3) YouTube (yt-dlp) — un échec réseau ne doit JAMAIS tuer les autres
        #    sources : l'opérateur garde son transcript même si YouTube rate.
        try:
            if subs_dir is None:
                subs_dir = _download_subs(source_url)
            cues = _load_lang_cues(subs_dir, prefix)
        except Exception as exc:  # noqa: BLE001 — 429, réseau, timeout…
            result[lang] = {"available": False, "lines": [],
                            "provider": "youtube", "error": str(exc)}
            continue
        if not cues:
            result[lang] = {"available": False, "lines": [], "provider": "youtube"}
            _write_cache(cache, source_url, run_id, cand_id, start, end, lang,
                         False, [])
            continue
        lines = _slice_lines(cues, start, end)
        result[lang] = {"available": bool(lines), "lines": lines,
                        "provider": "youtube"}
        _write_cache(cache, source_url, run_id, cand_id, start, end, lang,
                     bool(lines), lines)
        if lines:
            langs_found += 1

    # 4) filet Whisper — uniquement si aucune langue n'a été obtenue
    if langs_found == 0 and "whisper_attempted" not in result:
        result["whisper_attempted"] = True
        try:
            cues = _whisper_cues(source_url)
            if cues:
                lang = _detect_language(" ".join(c["text"] for c in cues))
                lines = _slice_lines(cues, start, end)
                result[lang] = {"available": bool(lines), "lines": lines,
                                "provider": "whisper"}
                _write_cache(_cache_path(run_id, cand_id, lang), source_url,
                             run_id, cand_id, start, end, lang,
                             bool(lines), lines, provider="whisper")
                if lines:
                    langs_found += 1
        except Exception as exc:  # noqa: BLE001 — le filet ne casse jamais la chaîne
            result["whisper_note"] = f"filet Whisper inactif : {exc}"

    result["available"] = langs_found > 0
    if not result["available"]:
        result["note"] = ("aucun transcript FR/EN (ni opérateur, ni YouTube) — "
                          "déposez un transcript dans war_room/transcripts_in/ "
                          "ou attendez la fin du rate-limit")
    elif langs_found == 1:
        missing = "FR" if (result["fr"] is None or not result["fr"]["available"]) else "EN"
        result["note"] = f"transcript {missing} indisponible — une seule langue affichée"
    return result


def _write_cache(path: Path, source_url: str, run_id: str, cand_id: str,
                 start: float, end: float, lang: str, available: bool,
                 lines: list[dict], provider: str = "youtube") -> None:
    doc = {
        "candidate_id": cand_id, "run_id": run_id, "lang": lang,
        "source": source_url, "window": {"start": start, "end": end},
        "provider": provider, "available": available, "lines": lines,
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
