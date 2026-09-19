"""segment_vod.py — Découpe une VOD Twitch en segments pour la matrice F00B.
===========================================================================

Le workflow GitHub Actions matricé (perturabo_transcribe_matrix.yml) lance
15 jobs de transcription en parallèle. Ce script est exécuté UNE fois par le
job « prepare » : il mesure la durée de la VOD et produit la matrice des
segments, publiée en output GitHub Actions.

Chevauchement (overlap) : chaque segment télécharge 3 s de plus de part et
d'autre de ses bornes intérieures. Les mots de la zone de recouvrement sont
ensuite dédupliqués au moment de la fusion (merge_transcripts.py) par
timestamp global identique. Sans overlap, les mots qui tombent pile sur une
frontière seraient coupés en deux — et souvent au milieu d'une punchline.

Offset : chaque segment porte `offset` = début RÉEL de la tranche téléchargée
(`download_start`). Le service Modal (transcribe.py, champ `offset`) ajoute
cet offset aux timestamps word-level : les mots reviennent déjà GLOBAUX
(position dans la VOD complète). La fusion n'a donc aucun recalcul à faire.

Sortie JSON :
  {
    "vod_url": "...", "duration_sec": 10954.0,
    "nb_segments": 15, "overlap_sec": 3.0,
    "segments": [
      {"id": 0, "start": 0.0,   "end": 730.3,  "download_start": 0.0,  "download_end": 733.3,  "offset": 0.0},
      {"id": 1, "start": 730.3, "end": 1460.5, "download_start": 727.3, "download_end": 1463.5, "offset": 727.3},
      ...
    ]
  }

Usage :
  python segment_vod.py --vod-url https://www.twitch.tv/videos/2873615032 \
      --nb-segments 15 --overlap-sec 3 --out segments.json
  # + option --github-output : écrit aussi la chaîne matrice pour GITHUB_OUTPUT
"""

import argparse
import json
import subprocess
import sys


def _log(msg: str) -> None:
    print(f"[segment_vod] {msg}", flush=True)


def get_metadata(vod_url: str, timeout: int = 60) -> tuple:
    """Métadonnées VOD via yt-dlp --dump-single-json (aucun téléchargement).

    Retourne (duration, title, upload_date, channel). La durée est OBLIGATOIRE
    (le scoring chat se normalise par la durée) ; le reste est best-effort.
    """
    cmd = [
        "yt-dlp", "--dump-single-json", "--skip-download",
        "--no-warnings", vod_url,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as e:
        raise RuntimeError(f"yt-dlp timeout ({timeout}s) sur {vod_url}") from e
    if result.returncode != 0:
        raise RuntimeError(
            f"yt-dlp a échoué (rc={result.returncode}): {result.stderr[:300]}"
        )
    try:
        meta = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Sortie yt-dlp illisible: {e}") from e
    duration = float(meta.get("duration") or 0)
    if duration <= 0:
        raise RuntimeError("Durée VOD inconnue (duration<=0)")
    title = str(meta.get("title") or "unknown")
    upload_date = str(meta.get("upload_date") or "")
    channel = str(meta.get("uploader") or meta.get("channel") or "")
    return duration, title, upload_date, channel


def build_segments(duration: float, nb_segments: int, overlap: float) -> list:
    """Bornes égales ; overlap uniquement sur les bornes INTÉRIEURES.

    - start/end   : bornes logiques du segment (couverture exacte, sans doublon)
    - dl_start/dl_end : bornes réelles de téléchargement (avec overlap)
    - offset      : dl_start — relocalisation Modal → timestamps globaux
    """
    if nb_segments < 1:
        raise ValueError("nb_segments doit être >= 1")
    if overlap < 0:
        overlap = 0.0
    step = duration / nb_segments
    segments = []
    for i in range(nb_segments):
        start = round(i * step, 2)
        end = round(duration if i == nb_segments - 1 else (i + 1) * step, 2)
        dl_start = round(max(0.0, start - (overlap if i > 0 else 0.0)), 2)
        dl_end = round(min(duration, end + (overlap if i < nb_segments - 1 else 0.0)), 2)
        segments.append({
            "id": i,
            "start": start,
            "end": end,
            "download_start": dl_start,
            "download_end": dl_end,
            "offset": dl_start,
        })
    return segments


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Découpe une VOD en segments pour la matrice F00B.",
    )
    parser.add_argument("--vod-url", required=True, help="URL de la VOD Twitch")
    parser.add_argument("--nb-segments", type=int, default=15,
                        help="Nombre de segments (défaut: 15)")
    parser.add_argument("--overlap-sec", type=float, default=3.0,
                        help="Chevauchement entre segments en secondes (défaut: 3)")
    parser.add_argument("--out", default="segments.json",
                        help="Fichier JSON de sortie (défaut: segments.json)")
    parser.add_argument("--github-output", metavar="NAME",
                        help="Publie aussi la chaîne matrice sous NAME "
                             "(format GitHub Actions: name=[...json...])")
    args = parser.parse_args()

    _log(f"Mesure de la VOD : {args.vod_url}")
    duration, title, upload_date, channel = get_metadata(args.vod_url)
    _log(f"Titre: {title}")
    _log(f"Durée: {duration:.0f}s ({duration / 3600:.2f}h) | upload: {upload_date}")

    segments = build_segments(duration, args.nb_segments, args.overlap_sec)
    payload = {
        "vod_url": args.vod_url,
        "vod_title": title,
        "upload_date": upload_date,
        "channel": channel,
        "duration_sec": duration,
        "nb_segments": len(segments),
        "overlap_sec": args.overlap_sec,
        "segments": segments,
    }

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    _log(f"{len(segments)} segments écrits → {args.out}")
    for s in segments:
        _log(f"  seg {s['id']:02d}: {s['start']:9.1f} → {s['end']:9.1f} "
             f"(dl {s['download_start']:.1f} → {s['download_end']:.1f})")

    if args.github_output:
        matrix = json.dumps(segments, ensure_ascii=False, separators=(",", ":"))
        with open(args.github_output, "a", encoding="utf-8") as f:
            f.write(f"matrix={matrix}\n")
            f.write(f"duration={duration}\n")
            f.write(f"title={title}\n")
            f.write(f"upload_date={upload_date}\n")
        _log(f"Matrice + métadonnées publiées → {args.github_output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
