"""
auto_detector.py — Détection automatique F00B_VOX (Option A)
=============================================================

Le Warsmith ne détecte plus les moments viraux, il les VALIDE.
Chaîne : audio seul → transcription word-level → chat replay Twitch
        → fusion des pics → scoring (règles campagne + patterns ARCHIVUM)
        → OUT/candidats.json (schéma identique à `detect`) → gate Warsmith.

Doctrine F00B :
- La VOD vidéo n'est JAMAIS téléchargée en entier (règle d'or).
  Seule la PISTE AUDIO est récupérée pour l'analyse (poids ~10-20x moindre),
  en stream copy (aucune recompression), puis supprimée après usage
  sauf --keep-audio.
- Les segments finaux restent extraits par `ingest --execute`
  (yt-dlp --download-sections, stream copy).
- La détection est heuristique : le GATE Warsmith reste obligatoire.

Moteur de transcription :
- Clé premium via CONTRACTS/f00b_secrets.json (même pattern que F04).
  Fallback sur AI_GATEWAY_API_KEY / AI_GATEWAY_BASE_URL.
- API OpenAI-compatible /audio/transcriptions avec word timestamps.
- Audio chunké en segments ≤ 24 MB via ffmpeg segment (stream copy).

Chat replay : endpoint public v5 Twitch (client_id web anonyme),
aucune auth requise pour une VOD publique.

Usage (depuis f00b_vox.py) :
    python f00b_vox.py auto_detect
    python f00b_vox.py auto_detect --keep-audio
    python f00b_vox.py auto_detect --no-chat
"""

import hashlib
import json
import math
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

# ─── Constants ──────────────────────────────────────────────────────────────

# Client ID web Twitch (anonyme, utilisé par les outils open-source)
_TWITCH_CLIENT_ID = "kimne78kx3ncx6brgo4mv6wki5h1ko"

TRIGGER_WORDS = [
    "listen", "actually", "never", "stop", "truth", "nobody", "everybody",
    "insane", "crazy", "huge", "huge", "impossible", "incredible",
    "whammy", "arrête", "jamais", "vraiment", "la vérité", "personne",
    "tout le monde", "faut", "regarde", "attend", "dingue", "folie",
    "monstre", "urgent", "méga", "gigantesque", "impossible", "vraiment",
]

TOS_RISK_WORDS = [
    "onlyfans", "of creator", "suicide", "nude", "naked", "sexe",
    "drogue", "arme", "mort", "tuer",
]

# Emotes Twitch indicatrices d'émotion forte
_EMOTION_EMOTES = {
    "joy": ["LUL", "KEKW", "OMEGALUL", "haHAA", "LOL", "Pog", "EZ"],
    "hype": ["PogChamp", "Poggers", "CLAP", "Kreygasm", "LETSGO"],
    "negative": ["Sadge", "peepoSad", "F", "monkaS", "weirdChamp"],
}

# Durées optimales issues des patterns ARCHIVUM
ARCHIVUM_SWEET_SPOT = {"min": 20, "max": 40, "optimal": [30, 35]}
DURATION_TARGET = 30
DURATION_MIN = 15
DURATION_MAX = 60


# ─── Helpers ────────────────────────────────────────────────────────────────

def _now_iso():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _fmt_time(sec):
    """Secondes → HH:MM:SS.mmm"""
    sec = float(sec)
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = sec % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}"


def _candidate_id(vod_url, start_sec):
    raw = f"{vod_url}:{float(start_sec):.2f}"
    return hashlib.md5(raw.encode()).hexdigest()[:10]


def _load_json(path):
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _log(msg):
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")


# ─── Premium Transcriber ───────────────────────────────────────────────────

class PremiumTranscriber:
    """Client Whisper API — même pattern que F04 premium_client.py.
    Lit CONTRACTS/f00b_secrets.json pour le model/env/base_url.
    Fallback sur AI_GATEWAY_API_KEY / AI_GATEWAY_BASE_URL."""

    def __init__(self, forge_root):
        self._forge_root = forge_root
        self._config = self._load_config()
        self._load_env_local()

    def _load_config(self):
        for name in ("f00b_secrets.json", "f00b_secrets.example.json"):
            path = os.path.join(self._forge_root, "MONDES_FORGES", "CLIPPING",
                                "F00_IRON_SENTINEL", "F00B_VOX", "CODEBASE",
                                "CONTRACTS", name)
            if not os.path.exists(path):
                path = os.path.join(self._forge_root, "MONDES_FORGES",
                                    "CLIPPING", "CONTRACTS", name)
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
        return {}

    def _load_env_local(self):
        """Charge .env.local si présent — stdlib, aucune dépendance."""
        candidates = []
        base = self._forge_root
        for _ in range(4):
            candidates.append(os.path.join(base, ".env.local"))
            base = os.path.dirname(base)
        seen = set()
        for path in candidates:
            if path in seen or not os.path.exists(path):
                continue
            seen.add(path)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#") or "=" not in line:
                            continue
                        key, _, val = line.partition("=")
                        key, val = key.strip(), val.strip().strip('"').strip("'")
                        if key and not os.environ.get(key):
                            os.environ[key] = val
            except OSError:
                continue

    def _api_key(self):
        env_var = self._config.get("env_var_name", "CLIPPING_F00B_API_KEY")
        key = os.environ.get(env_var, "")
        if key:
            return key
        fallback = self._config.get("fallback_env_var", "AI_GATEWAY_API_KEY")
        return os.environ.get(fallback, "")

    def _base_url(self):
        provider = self._config.get("provider", "openai")
        urls = {
            "openai": "https://api.openai.com/v1",
            "openrouter": "https://openrouter.ai/api/v1",
        }
        custom = self._config.get("base_url")
        if custom:
            return custom
        if provider in urls:
            return urls[provider]
        fb = self._config.get("fallback_base_url", "AI_GATEWAY_BASE_URL")
        return os.environ.get(fb, "")

    @property
    def model_id(self):
        return self._config.get("model_id", "whisper-1")

    @property
    def language(self):
        return self._config.get("language", "en")

    @property
    def max_audio_mb(self):
        return self._config.get("max_audio_mb", 24)

    def require(self):
        if not self._api_key():
            raise RuntimeError(
                "Clé premium absente — définir CLIPPING_F00B_API_KEY "
                "ou AI_GATEWAY_API_KEY (config: CONTRACTS/f00b_secrets.json)")
        if not self._base_url():
            raise RuntimeError("base_url manquant pour le moteur de transcription")

    def transcribe_chunk(self, chunk_path):
        """Upload un chunk audio via multipart/form-data stdlib → word-level."""
        self.require()
        url = self._base_url().rstrip("/") + "/audio/transcriptions"
        boundary = f"----F00B{int(time.time())}"

        with open(chunk_path, "rb") as f:
            audio_data = f.read()

        fields = {
            "model": self.model_id,
            "response_format": "verbose_json",
            "timestamp_granularities[]": "word",
        }
        if self.language:
            fields["language"] = self.language

        body = b""
        for key, val in fields.items():
            body += f"--{boundary}\r\n".encode()
            body += f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode()
            body += f"{val}\r\n".encode()

        body += f"--{boundary}\r\n".encode()
        body += (f'Content-Disposition: form-data; name="file"; '
                 f'filename="{os.path.basename(chunk_path)}"\r\n').encode()
        body += b"Content-Type: audio/m4a\r\n\r\n"
        body += audio_data
        body += b"\r\n"
        body += f"--{boundary}--\r\n".encode()

        req = urllib.request.Request(url, data=body, method="POST", headers={
            "Authorization": f"Bearer {self._api_key()}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "User-Agent": "PERTURABO-F00B-VOX",
        })
        try:
            with urllib.request.urlopen(req, timeout=300) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            snippet = e.read().decode("utf-8", errors="replace")[:500]
            raise RuntimeError(f"Whisper API HTTP {e.code}: {snippet}") from e


# ─── Chat Replay ────────────────────────────────────────────────────────────

def fetch_chat_replay(vod_url):
    """Récupère le chat replay d'une VOD Twitch publique via l'API v5."""
    m = re.search(r"videos/(\d+)", vod_url)
    if not m:
        _log("⚠️  Impossible d'extraire le video_id — chat ignoré")
        return []
    video_id = m.group(1)
    _log(f"💬 Chat replay : video_id={video_id}")

    messages = []
    offset = 0.0
    max_requests = 500  # garde-fou budget
    seen_offsets = set()

    for _ in range(max_requests):
        url = (f"https://api.twitch.tv/v5/videos/{video_id}/comments"
               f"?client_id={_TWITCH_CLIENT_ID}"
               f"&content_offset_seconds={offset}")
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "PERTURABO-F00B-VOX",
            })
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except (urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError):
            break

        comments = data.get("comments", [])
        if not comments:
            break

        for c in comments:
            body = c.get("message", {}).get("body", "")
            emotes = [e.get("text", "") for e in c.get("message", {}).get("emoticons", [])]
            offset_sec = c.get("content_offset_seconds", 0)
            messages.append({
                "offset_sec": round(offset_sec, 2),
                "body": body,
                "emotes": emotes,
            })

        next_offset = data.get("_next")
        if not next_offset or next_offset in seen_offsets:
            break
        seen_offsets.add(next_offset)
        # Le paramètre _next est un offset opaque mais on utilise
        # content_offset_seconds pour la pagination
        last_offset = comments[-1].get("content_offset_seconds", offset)
        if last_offset <= offset:
            break
        offset = last_offset + 1
        time.sleep(0.1)  # politesse

    _log(f"💬 {len(messages)} messages chat récupérés")
    return messages


# ─── Speech Analysis ────────────────────────────────────────────────────────

def analyze_speech(words, trigger_words=None):
    """Analyse word-level transcript → pics de speech (triggers, punchlines, densité).
    Retourne une liste de peaks [{start, end, type, intensity}]."""
    trigger_words = trigger_words or TRIGGER_WORDS
    peaks = []

    for w in words:
        word = w.get("word", "").strip().lower()
        start = float(w.get("start", 0))
        end = float(w.get("end", start + 0.3))

        # Détection triggers
        if any(tw in word for tw in trigger_words if len(tw) > 3):
            peaks.append({
                "start": max(0, start - 1.0),
                "end": end + 1.0,
                "type": "trigger_word",
                "intensity": 0.85,
            })

    # Punchlines : mots courts (~3-8 mots) avec ponctuation forte
    # Regrouper en phrases approximatives
    if words:
        sentence_start = float(words[0].get("start", 0))
        sentence_words = []
        for w in words:
            word = w.get("word", "")
            sentence_words.append(word)
            if any(p in word for p in (".", "!", "?")):
                text = " ".join(sentence_words).strip()
                if 3 <= len(sentence_words) <= 12:
                    start = sentence_start
                    end = float(w.get("end", start))
                    has_punch = any(p in text for p in ("!", "?", "whammy", "dingue"))
                    if has_punch:
                        peaks.append({
                            "start": start,
                            "end": end,
                            "type": "punchline",
                            "intensity": 0.9,
                        })
                sentence_words = []
                sentence_start = float(w.get("end", sentence_start)) + 0.5

    # Densité de parole : fenêtres glissantes de 30s
    if words:
        duration = float(words[-1].get("end", 0))
        window = 30.0
        step = 5.0
        t = 0.0
        while t < duration:
            w_start = t
            w_end = t + window
            words_in = [w for w in words
                        if float(w.get("start", 0)) >= w_start
                        and float(w.get("start", 0)) < w_end]
            density = len(words_in) / window if window > 0 else 0
            if density > 2.5:  # > 2.5 mots/seconde = zone très parlée
                peaks.append({
                    "start": w_start,
                    "end": w_end,
                    "type": "energy",
                    "intensity": min(1.0, density / 5.0),
                })
            t += step

    return peaks


# ─── Chat Analysis ──────────────────────────────────────────────────────────

def analyze_chat(messages, duration):
    """Analyse chat replay → pics d'engagement. Retourne peaks."""
    if not messages:
        return []

    # Regrouper par fenêtre de 30s
    bucket_sec = 30.0
    buckets = {}
    for m in messages:
        offset = m.get("offset_sec", 0)
        bucket = int(offset // bucket_sec)
        buckets[bucket] = buckets.get(bucket, 0) + 1

    if not buckets:
        return []

    rates = list(buckets.values())
    mean_rate = sum(rates) / len(rates) if rates else 1
    std_rate = (sum((r - mean_rate) ** 2 for r in rates) / len(rates)) ** 0.5 if rates else 1

    peaks = []
    for bucket, count in buckets.items():
        if count > mean_rate + 1.5 * std_rate and count >= 5:
            t_start = bucket * bucket_sec
            t_end = min(t_start + bucket_sec, duration)
            intensity = min(1.0, count / (mean_rate + 3 * std_rate)) if (mean_rate + 3 * std_rate) > 0 else 0.5
            peaks.append({
                "start": t_start,
                "end": t_end,
                "type": "chat_spike",
                "intensity": round(intensity, 2),
            })

    # Détection d'émotions dans le chat
    all_text = " ".join(m.get("body", "") for m in messages)
    emotion_scores = {}
    for emo, emotes in _EMOTION_EMOTES.items():
        count = sum(all_text.upper().count(e.upper()) for e in emotes)
        emotion_scores[emo] = count

    _log(f"💬 Émotions chat : {emotion_scores}")
    return peaks


# ─── Candidate Builder ──────────────────────────────────────────────────────

def _overlap_fraction(a_start, a_end, b_start, b_end):
    inter = max(0, min(a_end, b_end) - max(a_start, b_start))
    dur = a_end - a_start
    return inter / dur if dur > 0 else 0


def fuse_candidates(speech_peaks, chat_peaks, nb_clips,
                    pre_roll=3.0, post_roll=3.0):
    """Fusionne speech + chat peaks → fenêtres candidates (20-40s)."""
    all_peaks = speech_peaks + chat_peaks
    if not all_peaks:
        return []

    # Trier par start
    all_peaks.sort(key=lambda p: p["start"])

    # Fusionner les pics proches (< 5s d'écart)
    fused = []
    for peak in all_peaks:
        merged = False
        if fused and peak["start"] - fused[-1]["end"] < 5.0:
            # Fusionner
            fused[-1]["end"] = max(fused[-1]["end"], peak["end"])
            fused[-1]["intensity"] = max(fused[-1]["intensity"], peak["intensity"])
            fused[-1]["type"] = "mixed" if fused[-1]["type"] != peak["type"] else peak["type"]
            merged = True
        if not merged:
            fused.append(dict(peak))  # copie

    # Construire les fenêtres
    windows = []
    for peak in fused:
        start = max(0, peak["start"] - pre_roll)
        end = peak["end"] + post_roll

        # Étendre si trop court
        dur = end - start
        if dur < DURATION_TARGET:
            extend = DURATION_TARGET - dur
            end += extend * 0.7
            start = max(0, start - extend * 0.3)

        # Tronquer si trop long
        if end - start > DURATION_MAX:
            end = start + DURATION_MAX

        # Vérifier durée min
        if end - start < DURATION_MIN:
            continue

        windows.append({
            "start": round(start, 2),
            "end": round(end, 2),
            "duration": round(end - start, 2),
            "intensity": peak["intensity"],
            "type": peak["type"],
        })

    # Dédoublonner chevauchements > 50%
    windows.sort(key=lambda w: w["intensity"], reverse=True)
    kept = []
    for w in windows:
        is_dup = False
        for k in kept:
            if _overlap_fraction(w["start"], w["end"], k["start"], k["end"]) > 0.5:
                is_dup = True
                break
        if not is_dup:
            kept.append(w)

    kept.sort(key=lambda w: w["start"])

    # Garder top N*2 (marge doctrine)
    target = max(nb_clips * 2, 6)
    return kept[:target]


# ─── Scoring ────────────────────────────────────────────────────────────────

WEIGHTS = {
    "hook_force": 0.30,
    "emotion": 0.25,
    "clarity": 0.15,
    "quotability": 0.15,
    "timing": 0.10,
    "format_fit": 0.05,
}


def score_candidates(candidates, words, chat_messages, vod_url):
    """Score chaque candidat avec des critères réels (speech + chat)."""
    scored = []
    duration = float(words[-1].get("end", 0)) if words else 0

    for cand in candidates:
        start, end = cand["start"], cand["end"]
        dur = cand["duration"]

        # Mots dans la fenêtre
        win_words = [w for w in words
                     if float(w.get("start", 0)) >= start
                     and float(w.get("start", 0)) < end]
        win_text = " ".join(w.get("word", "") for w in win_words)

        # Messages chat dans la fenêtre
        win_chat = [m for m in chat_messages
                    if m.get("offset_sec", 0) >= start
                    and m.get("offset_sec", 0) < end]

        # Hook force : mots triggers dans les 3 premières secondes
        hook_zone = [w for w in win_words
                     if float(w.get("start", 0)) - start <= 3.0]
        hook_text = " ".join(w.get("word", "") for w in hook_zone).lower()
        hook_hits = sum(1 for tw in TRIGGER_WORDS if tw in hook_text)
        hook_score = min(10, 4.0 + hook_hits * 2.5 + (1.5 if cand["type"] == "punchline" else 0))

        # Émotion : intensité du chat + type de signal
        chat_intensity = cand.get("intensity", 0.5)
        chat_count = len(win_chat)
        emotion_score = min(10, 3.0 + chat_intensity * 4 + min(3, chat_count / 10))

        # Clarté : densité de mots dans la fenêtre
        word_density = len(win_words) / dur if dur > 0 else 0
        clarity_score = min(10, 5.0 + word_density * 2)

        # Quotability : punchlines + triggers
        excl_count = win_text.count("!") + win_text.count("?")
        quotability_score = min(10, 3.0 + excl_count * 1.5 + hook_hits * 1.5)

        # Timing : durée optimale
        if 20 <= dur <= 35:
            timing_score = 7.0
        elif 15 <= dur <= 45:
            timing_score = 5.0
        else:
            timing_score = 3.0

        # Format fit : durée 9:16
        format_score = min(10, 6.0 + (1.5 if dur <= 40 else 0))

        # Score de base
        raw = {
            "hook_force": hook_score,
            "emotion": emotion_score,
            "clarity": clarity_score,
            "quotability": quotability_score,
            "timing": timing_score,
            "format_fit": format_score,
        }
        base = sum(WEIGHTS[k] * raw[k] for k in raw)

        # Bonus/malus
        bonus_total = 0
        malus_total = 0
        bonuses = []
        maluses = []
        reasons = []

        if dur > 60:
            maluses.append({"rule": "duree_gt_60", "delta": -3.0})
        if dur < 15:
            maluses.append({"rule": "duree_lt_15", "delta": -3.0})
        if cand["intensity"] >= 0.9:
            bonuses.append({"rule": "moment_unique", "delta": 1.5})
        if cand["intensity"] >= 0.7:
            bonuses.append({"rule": "haute_intensite", "delta": 1.0})
        if hook_hits >= 2:
            bonuses.append({"rule": "multi_trigger", "delta": 1.0})

        # TOS risk
        tos_hits = sum(1 for tw in TOS_RISK_WORDS if tw in win_text.lower())
        if tos_hits:
            maluses.append({"rule": "tos_risk", "delta": -2.0 * tos_hits})
            reasons.append("tos_risk")

        # Silences longs (> 3s sans parole)
        if win_words:
            gaps = []
            prev_end = start
            for w in sorted(win_words, key=lambda x: float(x.get("start", 0))):
                w_start = float(w.get("start", 0))
                if w_start - prev_end > 3.0:
                    gaps.append(w_start - prev_end)
                prev_end = float(w.get("end", prev_end))
            if gaps:
                max_gap = max(gaps)
                if max_gap > 5:
                    maluses.append({"rule": "long_silence", "delta": -1.5})
                    reasons.append("long_silence")

        bonus_total = sum(b["delta"] for b in bonuses)
        malus_total = sum(m["delta"] for m in maluses)
        final = max(0, min(10, round(base + bonus_total + malus_total, 2)))

        # Statut
        status = "scored"
        if final < 4.0 or tos_hits:
            status = "auto_rejected"
            reasons.append("score_lt_4" if final < 4.0 else "tos_risk")

        scored.append({
            "candidate_id": _candidate_id(vod_url, start),
            "start_sec": round(start, 2),
            "end_sec": round(end, 2),
            "duration_sec": round(dur, 2),
            "signal_type": cand["type"],
            "signal_intensity": round(cand["intensity"], 2),
            "signal_start": _fmt_time(start),
            "score": {
                "raw": {k: round(v, 1) for k, v in raw.items()},
                "base": round(base, 2),
                "bonuses": bonuses,
                "maluses": maluses,
                "bonus_total": round(bonus_total, 2),
                "malus_total": round(malus_total, 2),
                "final": final,
            },
            "status": status,
            "rejection_reasons": reasons if reasons else None,
            "top_words": win_text[:200] if win_text else "",
        })

    # Trier par score décroissant
    scored.sort(key=lambda s: s["score"]["final"], reverse=True)
    return scored


# ─── Candidats JSON Output ─────────────────────────────────────────────────

def build_candidats_json(scored_candidates, vod_url, words):
    """Produit OUT/candidats.json au format exact de cmd_detect."""
    accepted = [c for c in scored_candidates if c["status"] == "scored"]
    rejected = [c for c in scored_candidates if c["status"] == "auto_rejected"]

    candidats_list = []
    for c in accepted:
        candidats_list.append({
            "candidate_id": c["candidate_id"],
            "start_sec": c["start_sec"],
            "end_sec": c["end_sec"],
            "duration_sec": c["duration_sec"],
            "signal_type": c["signal_type"],
            "signal_intensity": c["signal_intensity"],
            "signal_start": c["signal_start"],
        })

    return {
        "generated_at": _now_iso(),
        "source": vod_url,
        "engine": "auto_detect",
        "total_words_analyzed": len(words),
        "total_candidates_raw": len(scored_candidates),
        "total_accepted": len(accepted),
        "total_auto_rejected": len(rejected),
        "candidates": candidats_list,
    }


# ─── Main Orchestrator ─────────────────────────────────────────────────────

def run_auto_detect(forge_root, vod_url, nb_clips=5,
                    market="us_young_english", platform="youtube_shorts",
                    keep_audio=False, no_chat=False):
    """Orchestre le pipeline auto_detect complet. Retourne candidats."""

    f00b_root = os.path.join(forge_root, "MONDES_FORGES", "CLIPPING",
                              "F00_IRON_SENTINEL", "F00B_VOX")
    in_dir = os.path.join(f00b_root, "IN")
    out_dir = os.path.join(f00b_root, "OUT")
    ingest_dir = os.path.join(f00b_root, "vox_ingest")
    temp_dir = os.path.join(ingest_dir, "auto_detect")

    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(temp_dir, exist_ok=True)

    _log("═══ F00B AUTO-DETECT — Lancement ═══")

    # ── 1. Métadonnées VOD ──────────────────────────────────────────────
    _log("📡 Récupération des métadonnées VOD...")
    metadata_cmd = [
        "yt-dlp", "--dump-single-json", "--skip-download",
        "--no-warnings", vod_url,
    ]
    try:
        result = subprocess.run(metadata_cmd, capture_output=True, text=True, timeout=30)
        metadata = json.loads(result.stdout) if result.returncode == 0 else {}
    except (subprocess.TimeoutExpired, json.JSONDecodeError):
        metadata = {}

    vod_title = metadata.get("title", "unknown")
    vod_duration = float(metadata.get("duration", 0))
    upload_date = metadata.get("upload_date", "")
    _log(f"  Titre: {vod_title}")
    _log(f"  Durée: {_fmt_time(vod_duration)} ({vod_duration:.0f}s)")
    _log(f"  Upload: {upload_date}")

    # ── 2. Téléchargement audio seul ────────────────────────────────────
    audio_path = os.path.join(temp_dir, "vod_audio.m4a")
    _log("🎵 Téléchargement de la piste audio seule (stream copy)...")
    dl_cmd = [
        "yt-dlp", "-f", "ba/b",
        "--no-playlist",
        "-o", audio_path,
        "--no-warnings",
        vod_url,
    ]
    try:
        subprocess.run(dl_cmd, capture_output=True, text=True, timeout=300, check=True)
        if os.path.exists(audio_path):
            audio_size_mb = os.path.getsize(audio_path) / (1024 * 1024)
            _log(f"  Audio: {audio_size_mb:.1f} Mo")
        else:
            raise FileNotFoundError("Fichier audio non créé")
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        _log(f"❌ Échec téléchargement audio: {e}")
        raise RuntimeError("Impossible de télécharger la piste audio") from e

    # ── 3. Découpage en chunks ──────────────────────────────────────────
    _log("✂️  Découpage en chunks pour l'API de transcription...")
    chunk_dir = os.path.join(temp_dir, "chunks")
    os.makedirs(chunk_dir, exist_ok=True)
    chunk_sec = 900  # 15 min par chunk (~18 Mo à 160kbps)

    segment_cmd = [
        "ffmpeg", "-i", audio_path,
        "-f", "segment",
        "-segment_time", str(chunk_sec),
        "-c", "copy",
        "-y",
        os.path.join(chunk_dir, "chunk_%03d.m4a"),
    ]
    try:
        subprocess.run(segment_cmd, capture_output=True, timeout=60, check=True)
    except subprocess.CalledProcessError as e:
        _log(f"❌ Échec ffmpeg segment: {e}")
        raise RuntimeError("ffmpeg requis pour le découpage audio") from e

    chunks = sorted([
        os.path.join(chunk_dir, f)
        for f in os.listdir(chunk_dir) if f.endswith(".m4a")
    ])
    _log(f"  {len(chunks)} chunks créés")

    # ── 4. Transcription word-level ─────────────────────────────────────
    _log("📝 Transcription word-level (clé premium)...")
    transcriber = PremiumTranscriber(forge_root)
    all_words = []

    for i, chunk_path in enumerate(chunks):
        _log(f"  Chunk {i+1}/{len(chunks)} ({os.path.getsize(chunk_path) / (1024*1024):.1f} Mo)...")
        try:
            result = transcriber.transcribe_chunk(chunk_path)
            chunk_offset = i * chunk_sec
            for w in result.get("words", []):
                all_words.append({
                    "word": w.get("word", ""),
                    "start": round(w.get("start", 0) + chunk_offset, 3),
                    "end": round(w.get("end", 0) + chunk_offset, 3),
                })
        except Exception as e:
            _log(f"  ⚠️  Erreur chunk {i+1}: {e}")
            continue

    _log(f"  {len(all_words)} mots transcrits (durée totale: {_fmt_time(all_words[-1]['end']) if all_words else '0'})")

    # Sauvegarder le transcript
    transcript_path = os.path.join(out_dir, "transcript.json")
    _save_json(transcript_path, {
        "generated_at": _now_iso(),
        "vod_url": vod_url,
        "vod_title": vod_title,
        "vod_duration": vod_duration,
        "upload_date": upload_date,
        "total_words": len(all_words),
        "words": all_words,
    })
    _log(f"  Transcript sauvegardé → {transcript_path}")

    # ── 5. Chat replay ──────────────────────────────────────────────────
    chat_messages = []
    if not no_chat:
        _log("💬 Récupération du chat replay...")
        chat_messages = fetch_chat_replay(vod_url)
        chat_path = os.path.join(out_dir, "chat.json")
        _save_json(chat_path, {
            "generated_at": _now_iso(),
            "vod_url": vod_url,
            "total_messages": len(chat_messages),
            "messages": chat_messages,
        })
        _log(f"  Chat sauvegardé → {chat_path}")
    else:
        _log("  Chat ignoré (--no-chat)")

    # ── 6. Analyse speech + chat → peaks ────────────────────────────────
    _log("🔍 Analyse speech (triggers + punchlines + densité)...")
    speech_peaks = analyze_speech(all_words)
    _log(f"  {len(speech_peaks)} speech peaks")

    _log("🔍 Analyse chat (pics d'engagement)...")
    chat_peaks = analyze_chat(chat_messages, vod_duration)
    _log(f"  {len(chat_peaks)} chat peaks")

    # ── 7. Fusion → candidats ───────────────────────────────────────────
    _log(f"🎯 Fusion des pics → {nb_clips * 2} candidats max...")
    candidates = fuse_candidates(speech_peaks, chat_peaks, nb_clips)
    _log(f"  {len(candidates)} candidats après fusion + déduplication")

    # ── 8. Scoring ──────────────────────────────────────────────────────
    _log("📊 Scoring multicritère...")
    scored = score_candidates(candidates, all_words, chat_messages, vod_url)
    accepted = [c for c in scored if c["status"] == "scored"]
    rejected = [c for c in scored if c["status"] == "auto_rejected"]
    _log(f"  {len(accepted)} acceptés, {len(rejected)} auto-rejetés")

    # ── 9. Output candidats.json ────────────────────────────────────────
    candidats = build_candidats_json(scored, vod_url, all_words)
    candidats_path = os.path.join(out_dir, "candidats.json")
    _save_json(candidats_path, candidats)
    _log(f"✅ Candidats sauvegardés → {candidats_path}")

    # ── 10. Rapport détaillé ────────────────────────────────────────────
    report = {
        "generated_at": _now_iso(),
        "engine": "auto_detect_v1",
        "vod_url": vod_url,
        "vod_title": vod_title,
        "vod_duration": vod_duration,
        "upload_date": upload_date,
        "market": market,
        "platform": platform,
        "nb_clips_requested": nb_clips,
        "transcription": {
            "engine": transcriber.model_id,
            "provider": transcriber._config.get("provider", "unknown"),
            "total_words": len(all_words),
            "chunks_processed": len(chunks),
            "audio_size_mb": round(os.path.getsize(audio_path) / (1024*1024), 1) if os.path.exists(audio_path) else 0,
        },
        "chat": {
            "enabled": not no_chat,
            "total_messages": len(chat_messages),
        },
        "analysis": {
            "speech_peaks": len(speech_peaks),
            "chat_peaks": len(chat_peaks),
            "candidates_raw": len(candidates),
            "accepted": len(accepted),
            "auto_rejected": len(rejected),
        },
        "candidates": scored,
    }
    report_path = os.path.join(out_dir, "auto_detect_report.json")
    _save_json(report_path, report)
    _log(f"📋 Rapport sauvegardé → {report_path}")

    # ── 11. Nettoyage ───────────────────────────────────────────────────
    if not keep_audio:
        _log("🧹 Nettoyage des fichiers temporaires...")
        import shutil
        try:
            shutil.rmtree(temp_dir)
            _log("  Fichiers temporaires supprimés")
        except OSError:
            _log("  ⚠️  Impossible de supprimer les fichiers temporaires")
    else:
        _log(f"  Audio conservé dans {temp_dir}")

    # ── 12. Résumé ──────────────────────────────────────────────────────
    _log("═══ F00B AUTO-DETECT — Terminé ═══")
    for c in accepted[:nb_clips]:
        _log(f"  ✓ {c['signal_start']} ({c['duration_sec']:.0f}s) "
             f"score={c['score']['final']:.1f} [{c['signal_type']}]")

    _log(f"\n→ Étape suivante : python f00b_vox.py score")
    _log(f"  (ou vérifier OUT/candidats.json puis valider via gate)")

    return candidats
