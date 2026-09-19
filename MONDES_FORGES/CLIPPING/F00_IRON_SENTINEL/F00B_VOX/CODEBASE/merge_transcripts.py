"""merge_transcripts.py — Fusion des chunks matriciels F00B → transcript global.
===============================================================================

Chaque job de la matrice (perturabo_transcribe_matrix.yml) transcrit UN
segment de la VOD et uploade un artefact :

  chunk_NNN_words.json   {"words": [{"word","start","end"}, ...]}
                         Timestamps DÉJÀ GLOBAUX (le service Modal ajoute
                         l'offset du segment — voir MODAL/transcribe.py).
                         Peut être {"words": []} ou absent si transcription vide.
  chat_chunk_NNN.json    {"messages": [{"content_offset_seconds": int, ...}, ...]}
                         Optionnel — le chat replay est paginé par segment.

Ce script (job « reassemble ») fusionne tout :

  1. Words       : tri global par (start, end), déduplication EXACTE par
                   (start, end) — la même zone de 3 s d'overlap a été transcrite
                   par 2 segments voisins ; les timestamps globaux identiques
                   désignent le même mot, on n'en garde qu'une copie.
  2. Chat        : tri par content_offset_seconds, dédoublonnage sur
                   (offset, auteur, contenu).
  3. Sortie      : schéma IDENTIQUE à auto_detector.run_auto_detect
                   (transcript.json) pour que detect/score/gate continuent de
                   fonctionner sans aucune modification.

Usage :
  python merge_transcripts.py --chunks-dir chunks/ --out transcript.json \
      --vod-url https://www.twitch.tv/videos/2873615032 \
      --vod-title "..." --duration 10954.0
"""

import argparse
import glob
import json
import os
import sys


def _log(msg: str) -> None:
    print(f"[merge_transcripts] {msg}", flush=True)


def _load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def merge_words(chunks_dir: str) -> list:
    """Fusionne + déduplique les mots de tous les chunk_*_words.json."""
    paths = sorted(glob.glob(os.path.join(chunks_dir, "chunk_*_words.json")))
    _log(f"{len(paths)} fichiers chunk_*_words.json trouvés")
    if not paths:
        return []

    seen = set()
    words = []
    for p in paths:
        try:
            data = _load_json(p)
        except (OSError, json.JSONDecodeError) as e:
            _log(f"⚠️  illisible {os.path.basename(p)}: {e}")
            continue
        for w in data.get("words") or []:
            try:
                start = round(float(w.get("start", 0)), 3)
                end = round(float(w.get("end", 0)), 3)
            except (TypeError, ValueError):
                continue
            key = (start, end)
            if key in seen:
                continue  # doublon d'overlap — même instant global
            seen.add(key)
            words.append({
                "word": str(w.get("word", "")),
                "start": start,
                "end": end,
            })

    words.sort(key=lambda w: (w["start"], w["end"]))
    return words


def merge_chat(chunks_dir: str) -> list:
    """Fusionne + déduplique les messages de tous les chat_chunk_*.json."""
    paths = sorted(glob.glob(os.path.join(chunks_dir, "chat_chunk_*.json")))
    _log(f"{len(paths)} fichiers chat_chunk_*.json trouvés")
    if not paths:
        return []

    seen = set()
    messages = []
    for p in paths:
        try:
            data = _load_json(p)
        except (OSError, json.JSONDecodeError) as e:
            _log(f"⚠️  illisible {os.path.basename(p)}: {e}")
            continue
        for m in data.get("messages") or []:
            try:
                offset = round(float(m.get("content_offset_seconds", 0)), 3)
            except (TypeError, ValueError):
                continue
            key = (offset, m.get("display_name") or m.get("user", ""),
                   m.get("message_body") or m.get("message", ""))
            if key in seen:
                continue  # paginé 2× (overlap de pagination)
            seen.add(key)
            messages.append(m)

    messages.sort(key=lambda m: m.get("content_offset_seconds", 0))
    return messages


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fusion des chunks matriciels F00B → transcript.json global.",
    )
    parser.add_argument("--chunks-dir", required=True,
                        help="Dossier contenant chunk_*_words.json + chat_chunk_*.json")
    parser.add_argument("--out", required=True, help="transcript.json de sortie")
    parser.add_argument("--vod-url", default="unknown")
    parser.add_argument("--vod-title", default="unknown")
    parser.add_argument("--upload-date", default="")
    parser.add_argument("--duration", type=float, default=0.0,
                        help="Durée RÉELLE de la VOD (du job prepare — obligatoire : "
                             "le scoring chat se normalise par la durée)")
    parser.add_argument("--min-words", type=int, default=50,
                        help="Échec si moins de mots fusionnés (défaut: 50)")
    args = parser.parse_args()

    if not os.path.isdir(args.chunks_dir):
        _log(f"❌ dossier introuvable: {args.chunks_dir}")
        return 1

    words = merge_words(args.chunks_dir)
    chat = merge_chat(args.chunks_dir)

    _log(f"Total mots fusionnés : {len(words)}")
    _log(f"Total messages chat : {len(chat)}")

    # Vérification de cohérence : les mots doivent être temporellement triés
    for a, b in zip(words, words[1:]):
        if a["start"] > b["start"] + 0.001:
            _log("❌ mots non triés après fusion — bug de déduplication")
            return 1

    if len(words) < args.min_words:
        _log(f"❌ {len(words)} mots < seuil {args.min_words} — transcription trop incomplète")
        return 1

    # Un mot dont end < start est une anomalie Whisper rare ; on filtre.
    words = [w for w in words if w["end"] >= w["start"]]

    if args.duration <= 0:
        _log("❌ durée VOD absente (--duration) — scoring chat impossible, STOP")
        return 1

    transcript = {
        "generated_at": __import__("datetime").datetime.utcnow().isoformat() + "Z",
        "mode": "matrix_merged",
        "vod_url": args.vod_url,
        "vod_title": args.vod_title,
        "upload_date": args.upload_date,
        "vod_duration": args.duration,
        "transcription_mode": "words",
        "total_words": len(words),
        "words": words,
        "segments": None,
        "chat_messages": chat,
    }
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(transcript, f, ensure_ascii=False)

    # Transcript texte lisible (contrôle humain au gate)
    txt_path = os.path.splitext(args.out)[0] + ".txt"
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(" ".join(w["word"] for w in words))
    _log(f"✅ transcript → {args.out} (+ {txt_path})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
