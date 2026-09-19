"""transcribe_segment.py — Transcrit UN segment matriciel via le service Modal.
=============================================================================

Exécuté par CHAQUE job de la matrice (perturabo_transcribe_matrix.yml).

Pourquoi des pièces ? Un segment de ~12 min transcrit sur CPU dépasse le
timeout de requête Modal (408). Ce script découpe donc le segment en pièces
courtes (défaut 480 s ≈ 8 min ≈ 9 Mo) et envoie chaque pièce AVEC son offset
global réel (cumulé via ffprobe, pas nominal) — les mots reviennent déjà
globaux, la fusion au reassemble ne change rien.

Robustesse : 3 tentatives par pièce sur 408/429/5xx/URLError (backoff 15 s).

Usage (workflow) :
  python transcribe_segment.py --segment chunk_out/segment.m4a \
      --offset 727.27 --seg-id 1 --out chunk_001_words.json \
      --modal-url "$MODAL_URL" --token "$MODAL_TOKEN_ID" --piece-sec 480
"""

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid


def _log(msg: str) -> None:
    print(f"[transcribe_segment] {msg}", flush=True)


def _probe_duration(path: str) -> float:
    """Durée réelle du conteneur audio (ffprobe) — pas la durée nominale."""
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True, timeout=60,
    )
    try:
        return float(out.stdout.strip())
    except ValueError:
        return 0.0


def _split(segment_path: str, piece_sec: float, workdir: str) -> list:
    """Découpe le segment en pièces stream-copy (aucune recompression)."""
    os.makedirs(workdir, exist_ok=True)
    for f in os.listdir(workdir):
        if f.endswith(".m4a"):
            os.remove(os.path.join(workdir, f))
    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error",
        "-i", segment_path,
        "-f", "segment", "-segment_time", str(piece_sec),
        "-reset_timestamps", "1", "-c", "copy", "-y",
        os.path.join(workdir, "piece_%03d.m4a"),
    ]
    subprocess.run(cmd, check=True, capture_output=True, timeout=300)
    pieces = sorted(
        os.path.join(workdir, f) for f in os.listdir(workdir) if f.endswith(".m4a")
    )
    if not pieces:
        raise RuntimeError("ffmpeg n'a produit aucune pièce")
    return pieces


def _post(url: str, token: str, audio_path: str, offset: float,
          language: str, timeout: int, retries: int = 3):
    """POST multipart d'une pièce au service Modal (avec retries)."""
    boundary = uuid.uuid4().hex
    with open(audio_path, "rb") as f:
        audio = f.read()

    fields = {
        "model": "whisper-medium",
        "response_format": "verbose_json",
        "timestamp_granularities[]": "word",
        "offset": str(offset),
    }
    if language:
        fields["language"] = language

    body = b""
    for k, v in fields.items():
        body += f"--{boundary}\r\n".encode()
        body += f'Content-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
    body += f"--{boundary}\r\n".encode()
    body += b'Content-Disposition: form-data; name="file"; filename="piece.m4a"\r\n'
    body += b"Content-Type: audio/m4a\r\n\r\n" + audio + b"\r\n"
    body += f"--{boundary}--\r\n".encode()

    last_err = None
    for attempt in range(1, retries + 1):
        req = urllib.request.Request(url, data=body, method="POST", headers={
            "Authorization": f"Bearer {token or 'perturabo'}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "User-Agent": "PERTURABO-F00B-MATRIX",
        })
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace")[:200]
            last_err = f"HTTP {e.code}: {detail}"
            if e.code in (408, 429, 500, 502, 503, 504) and attempt < retries:
                _log(f"  ⚠️ {last_err} (essai {attempt}/{retries}) — retry dans 15 s")
                time.sleep(15)
                continue
            raise RuntimeError(last_err)
        except urllib.error.URLError as e:
            last_err = f"URLError: {e.reason}"
            if attempt < retries:
                _log(f"  ⚠️ {last_err} (essai {attempt}/{retries}) — retry dans 15 s")
                time.sleep(15)
                continue
            raise RuntimeError(last_err)
    raise RuntimeError(last_err or "échec inconnu")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Transcription matricielle d'un segment (pièces + offset global).",
    )
    parser.add_argument("--segment", required=True, help="Audio du segment (.m4a)")
    parser.add_argument("--offset", type=float, required=True,
                        help="Début GLOBAL du segment dans la VOD (secondes)")
    parser.add_argument("--seg-id", required=True, help="ID du segment (matrice)")
    parser.add_argument("--out", required=True, help="chunk_NNN_words.json de sortie")
    parser.add_argument("--modal-url", default=os.environ.get("MODAL_URL", ""))
    parser.add_argument("--token", default=os.environ.get("MODAL_TOKEN_ID", ""))
    parser.add_argument("--language", default="en")
    parser.add_argument("--piece-sec", type=float, default=480,
                        help="Durée d'une pièce (défaut 480 s — évite le 408 Modal)")
    parser.add_argument("--workdir", default="pieces_tmp")
    parser.add_argument("--request-timeout", type=int, default=900)
    args = parser.parse_args()

    if not args.modal_url:
        print("❌ MODAL_URL manquant (--modal-url ou env)", flush=True)
        return 1

    url = args.modal_url.rstrip("/") + "/audio/transcriptions"
    pieces = _split(args.segment, args.piece_sec, args.workdir)
    _log(f"segment {args.seg_id}: {len(pieces)} pièce(s) de ≤{args.piece_sec:.0f}s")

    words = []
    piece_offset = float(args.offset)
    for i, p in enumerate(pieces, 1):
        dur = _probe_duration(p)
        _log(f"  pièce {i}/{len(pieces)} ({os.path.getsize(p)/(1024*1024):.1f} Mo, "
             f"{dur:.0f}s) — offset global {piece_offset:.1f}s")
        try:
            result = _post(url, args.token, p, piece_offset, args.language,
                           args.request_timeout)
        except RuntimeError as e:
            _log(f"  ❌ pièce {i} échouée après retries: {e}")
            return 1

        pw = result.get("words") or []
        # Filet : si le service ignore l'offset (version ancienne), les
        # timestamps sont locaux (max << offset) → relocalisation.
        if pw and piece_offset > 0 and max(w["start"] for w in pw) <= piece_offset:
            for w in pw:
                w["start"] = round(w["start"] + piece_offset, 3)
                w["end"] = round(w["end"] + piece_offset, 3)
        words.extend(pw)
        piece_offset += dur  # cumul RÉEL (ffprobe), pas nominal

    if not words:
        _log("⚠️  0 mot transcrit (segment peut-être silencieux) — fichier vide écrit")
    else:
        _log(f"✅ segment {args.seg_id}: {len(words)} mots, "
             f"dernier start {max(w['start'] for w in words):.1f}s")

    payload = {
        "words": words,
        "segment_id": int(args.seg_id),
        "offset": float(args.offset),
        "pieces": len(pieces),
    }
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(payload, f)
    return 0


if __name__ == "__main__":
    sys.exit(main())
