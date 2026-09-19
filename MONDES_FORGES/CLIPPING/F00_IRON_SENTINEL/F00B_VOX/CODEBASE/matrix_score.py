"""matrix_score.py — Job final de la matrice F00B : candidats depuis le transcript fusionné.
==========================================================================================

Exécuté par le job « reassemble » (perturabo_transcribe_matrix.yml), APRÈS la
fusion des 15 chunks (merge_transcripts.py). Ce script reprend la chaîne
d'analyse EXISTANTE d'auto_detector.run_auto_detect (étapes 6 → 12), avec un
seul changement : la source des mots n'est plus la transcription séquentielle
mais le transcript fusionné de la matrice.

Chaîne reprise à l'identique (zéro changement de doctrine) :
  analyze_speech → analyze_chat → fuse_candidates → build_raw_table
  → score_candidates → veto campagne → arbitrage premium → candidats.json
  → auto_detect_report.json

Le chat, si les jobs matriciels l'ont rapatrié par segment, est déjà fusionné
dans le transcript (champ chat_messages). Sinon, fallback : récupération
globale du chat replay ici (paginé une seule fois).

Usage (depuis le dépôt racine ou avec F00B_ROOT) :
  python matrix_score.py --transcript transcript.json \
      --vod-url https://www.twitch.tv/videos/2873615032 \
      --nb-clips 5 --market us_young_english --platform youtube_shorts \
      --out-dir ../OUT
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "libs"))

from auto_detector import (  # noqa: E402
    TRIGGER_WORDS,
    _log,
    _now_iso,
    analyze_chat,
    analyze_speech,
    build_candidats_json,
    fetch_chat_replay,
    fuse_candidates,
    score_candidates,
)

F00B_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Scoring global F00B depuis le transcript matriciel fusionné.",
    )
    parser.add_argument("--transcript", required=True,
                        help="transcript.json fusionné (merge_transcripts.py)")
    parser.add_argument("--vod-url", required=True)
    parser.add_argument("--nb-clips", type=int, default=5)
    parser.add_argument("--market", default="us_young_english")
    parser.add_argument("--platform", default="youtube_shorts")
    parser.add_argument("--out-dir", default=None,
                        help="Dossier OUT (défaut: <repo>/F00B_VOX/OUT)")
    parser.add_argument("--min-words", type=int, default=50)
    args = parser.parse_args()

    out_dir = args.out_dir or os.path.join(F00B_ROOT, "OUT")
    os.makedirs(out_dir, exist_ok=True)

    _log("═══ F00B MATRICE — Scoring global ═══")
    with open(args.transcript, "r", encoding="utf-8") as f:
        transcript = json.load(f)

    words = transcript.get("words") or []
    chat_messages = transcript.get("chat_messages") or []
    vod_duration = float(transcript.get("vod_duration") or 0)
    vod_title = transcript.get("vod_title", "unknown")
    upload_date = transcript.get("upload_date", "")

    _log(f"VOD: {vod_title} | {vod_duration:.0f}s | {len(words)} mots fusionnés")

    if len(words) < args.min_words:
        _log(f"❌ {len(words)} mots < seuil {args.min_words} — run matrice incomplet, STOP")
        return 1

    # ── Chat replay (fallback global si absent des chunks) ───────────────
    if not chat_messages:
        _log("💬 Chat absent des chunks — récupération globale...")
        chat_messages = fetch_chat_replay(args.vod_url)
    _log(f"💬 {len(chat_messages)} messages chat au total")

    # ── 6. Analyse speech + chat → peaks (identique run_auto_detect) ─────
    _log("🔍 Analyse speech (triggers + punchlines + densité)...")
    speech_peaks = analyze_speech(words)
    _log(f"  {len(speech_peaks)} speech peaks")

    _log("🔍 Analyse chat (pics d'engagement)...")
    chat_peaks = analyze_chat(chat_messages, vod_duration)
    _log(f"  {len(chat_peaks)} chat peaks")

    if not speech_peaks and not chat_peaks:
        _log("❌ Aucun signal détecté — impossible de générer des candidats")
        return 1

    # ── 7. Fusion → candidats ────────────────────────────────────────────
    _log(f"🎯 Fusion des pics → {args.nb_clips * 2} candidats max...")
    candidates = fuse_candidates(speech_peaks, chat_peaks, args.nb_clips)
    _log(f"  {len(candidates)} candidats après fusion + déduplication")

    # ── 8. Scoring multicritère ──────────────────────────────────────────
    _log("📊 Scoring multicritère...")
    scored = score_candidates(candidates, words, chat_messages, args.vod_url)

    # ── 8b. Veto directive campagne (P1) ─────────────────────────────────
    try:
        from campaign_veto import (
            find_campaign_directive_md, load_campaign_directive, apply_campaign_veto,
        )
        forge_root = os.path.dirname(os.path.dirname(os.path.dirname(F00B_ROOT)))
        md_path = find_campaign_directive_md(forge_root)
        if md_path:
            with open(md_path, "r", encoding="utf-8") as f:
                directive = load_campaign_directive(f.read())
            _log(f"🛡️  Directive campagne: {directive.get('campaign_id')} "
                 f"| plateformes={directive.get('platforms')}")
            scored, veto_n = apply_campaign_veto(scored, directive, args.platform, upload_date)
            _log(f"  {veto_n} veto(s) campagne appliqué(s)")
        else:
            _log("  (aucune directive campagne — veto ignoré)")
    except Exception as e:
        _log(f"  ⚠️ veto campagne indisponible ({e}) — continué sans veto")

    # ── 8c. Arbitrage premium (P5) — clé NVIDIA_NIM_API_KEY ──────────────
    survivors = [c for c in scored if c["status"] == "scored"]
    try:
        from vox_premium import arbitrate
        survivors = arbitrate(survivors)
        scored = [c for c in scored if c["status"] != "scored"] + survivors
        _log(f"  🧠 Arbitrage premium: verdicts {[c.get('verdict') for c in survivors]}")
    except Exception as e:
        _log(f"  ⚠️ arbitrage premium indisponible ({e}) — continué sans premium")

    accepted = [c for c in scored if c["status"] == "scored"]
    rejected = [c for c in scored if c["status"] == "auto_rejected"]
    _log(f"  {len(accepted)} acceptés, {len(rejected)} auto-rejetés")

    # ── 9. Outputs (schéma identique au run séquentiel) ──────────────────
    candidats = build_candidats_json(scored, args.vod_url, words)
    candidats_path = os.path.join(out_dir, "candidats.json")
    with open(candidats_path, "w", encoding="utf-8") as f:
        json.dump(candidats, f, ensure_ascii=False, indent=2)
    _log(f"✅ Candidats → {candidats_path}")

    report = {
        "generated_at": _now_iso(),
        "engine": "auto_detect_matrix_v1",
        "vod_url": args.vod_url,
        "vod_title": vod_title,
        "vod_duration": vod_duration,
        "upload_date": upload_date,
        "market": args.market,
        "platform": args.platform,
        "nb_clips_requested": args.nb_clips,
        "transcription": {
            "mode": "matrix_merged",
            "total_words": len(words),
        },
        "chat": {"enabled": bool(chat_messages), "total_messages": len(chat_messages)},
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
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    _log(f"📋 Rapport → {report_path}")

    # ── 12. Résumé ───────────────────────────────────────────────────────
    _log("═══ F00B MATRICE — Terminé ═══")
    for c in accepted[:args.nb_clips]:
        _log(f"  ✓ {c['signal_start']} ({c['duration_sec']:.0f}s) "
             f"score={c['score']['final']:.1f} [{c['signal_type']}]")

    return 0


if __name__ == "__main__":
    sys.exit(main())
