"""
campaign_veto.py — Filtre veto directive campagne (P1 refonte VOX)
===================================================================

P1 de la refonte : VOX doit écarter les candidats non conformes à la
directive campagne **AVANT** que l'aval ne dépense du premium.

Trois axes de conformité (doctrine « garbage in = garbage out ») :
  1. Plateforme autorisée  -> veto DUR si la plateforme n'est pas listée.
  2. Cycle campagne        -> warning si la VOD est hors période (prolongation possible).
  3. Exclusions dures      -> veto DUR si le texte du candidat contient un motif interdit
                              (OF/onlyfans, bait/misinfo, negative PR).

Aucune dépendance premium. N'importe pas auto_detector (pas de cycle d'import).
"""

import os
import re

# ─── Contrat du tableau brut (P1 — fondation) ─────────────────────────────
# Une ligne par fenêtre (~5-10s) ; chaque colonne = un signal d'un capteur.
# Les capteurs effectifs (emotes, clips, audio, visuel...) remplissent ces
# colonnes aux phases P2 à P4. P1 pose le contrat + le veto campagne.
RAW_TABLE_COLUMNS = [
    "window_id", "start_sec", "end_sec", "duration_sec",
    # Étage 0 (gratuit)
    "emote_joy", "emote_hype", "emote_negative",
    "chat_velocity", "chat_spike",
    "clips_density", "clips_views",
    "events_raid", "events_subs",
    # Étage 2 (lourd ciblé)
    "audio_laugh", "audio_applause", "audio_silence",
    "visual_face", "visual_cut",
    # Étage 1 (lexical)
    "lex_density", "lex_gap_max", "lex_hook",
    # Conformité
    "campaign_ok", "campaign_reasons",
]

# Exclusions "dures" détectables automatiquement sur le texte du candidat.
HARD_EXCLUSION_PATTERNS = [
    (r"of\s+creator", "of_creator_mention"),
    (r"only\s?fans", "onlyfans_mention"),
    (r"\bbait\b|\bmisinformation\b", "bait_misinformation"),
    (r"negative\s+pr", "negative_pr"),
]

_PLATFORM_ALIASES = {
    "tiktok": "tiktok",
    "x": "twitter_x", "twitter": "twitter_x", "x (twitter)": "twitter_x",
    "ig reels": "instagram_reels", "instagram": "instagram_reels",
    "instagram reels": "instagram_reels",
    "youtube shorts": "youtube_shorts", "yt shorts": "youtube_shorts",
    "youtube_shorts": "youtube_shorts",
}


def _norm_platform(p):
    return _PLATFORM_ALIASES.get(str(p).strip().lower(), str(p).strip().lower())


def _parse_date(d, default=None):
    """'2026-07-20' ou '20260704' -> 'YYYY-MM-DD'."""
    if not d:
        return default
    s = str(d).strip().strip("[]")
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    m = re.match(r"(\d{4})(\d{2})(\d{2})", s)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    return default


def find_campaign_directive_md(forge_root):
    """Localise le fichier directive de campagne actif dans ARCHIVUM/campaign/.
    Retourne le chemin du .md ou None."""
    campaign_dir = os.path.join(forge_root, "MONDES_FORGES", "CLIPPING",
                                "ARCHIVUM", "campaign")
    if not os.path.isdir(campaign_dir):
        return None
    candidates = []
    for fn in sorted(os.listdir(campaign_dir)):
        if not fn.lower().endswith(".md"):
            continue
        if "template" in fn.lower():
            continue
        path = os.path.join(campaign_dir, fn)
        try:
            with open(path, "r", encoding="utf-8") as f:
                text = f.read()
        except OSError:
            continue
        # Une vraie directive active possède Platforms ET un cycle campagnagn.
        if "Platforms:" in text and ("Start:" in text and "End:" in text):
            # Priorité aux campagnes Clipify (réelles) sur les directives génériques.
            score = 1 if "Clipify" in text else 0
            candidates.append((score, path))
    if not candidates:
        return None
    candidates.sort(key=lambda x: (-x[0], x[1]))
    return candidates[0][1]


def load_campaign_directive(md_text):
    """Parse léger d'une directive markdown -> dict normalisé (ne lève jamais)."""
    if not md_text:
        return {}
    d = {}

    cid = re.search(r"Campaign ID:\s*(.+)", md_text)
    d["campaign_id"] = cid.group(1).strip().strip("*") if cid else None

    pm = re.search(r"\*\*Platforms:\*\*\s*(.+)", md_text)
    if pm:
        d["platforms"] = [_norm_platform(x) for x in re.split(r",", pm.group(1)) if x.strip()]

    start = re.search(r"\*\*Start:\*\*\s*(\[?[\d\-/]+\]?)", md_text)
    end = re.search(r"\*\*End:\*\*\s*(\[?[\d\-/]+\]?)", md_text)
    d["cycle"] = {
        "start": _parse_date(start.group(1)) if start else None,
        "end": _parse_date(end.group(1)) if end else None,
    }

    d["no_reaction_clips"] = bool(re.search(r"no\s+reaction\s+clips", md_text, re.I))
    return d


def _in_cycle(campaign, upload_date):
    """upload_date 'YYYYMMDD' ou 'YYYY-MM-DD'. Retourne (bool|None, cycle_str)."""
    cyc = campaign.get("cycle", {})
    start, end = cyc.get("start"), cyc.get("end")
    cycle_str = f"{start or '?'} -> {end or '?'}"
    if not start and not end:
        return None, cycle_str
    ud = _parse_date(upload_date)
    if not ud:
        return None, cycle_str
    if start and ud < start:
        return False, cycle_str
    if end and ud > end:
        return False, cycle_str
    return True, cycle_str


def apply_campaign_veto(scored, directive, platform, upload_date=""):
    """Marque chaque candidat d'un campaign_check + veto DUR si violation certaine.
    Retourne (scored_modifié, veto_count). Non-bloquant si directive vide."""
    if not directive:
        for c in scored:
            c["campaign_check"] = {"status": "no_directive", "reasons": []}
        return scored, 0

    veto_count = 0
    allowed_platforms = directive.get("platforms") or []
    norm_platform = _norm_platform(platform)

    for c in scored:
        reasons = []
        hard_veto = False

        if allowed_platforms and norm_platform not in allowed_platforms:
            reasons.append({"axis": "plateforme", "level": "veto",
                            "detail": f"{platform} non autorisée (autorisées: {allowed_platforms})"})
            hard_veto = True

        if upload_date:
            in_cycle, cycle_str = _in_cycle(directive, upload_date)
            if in_cycle is False:
                reasons.append({"axis": "cycle", "level": "warning",
                                "detail": f"VOD hors cycle ({cycle_str}) — vérifier annonce"})
            elif in_cycle is True:
                reasons.append({"axis": "cycle", "level": "ok", "detail": f"dans cycle {cycle_str}"})

        text = (c.get("top_words") or "").lower()
        for pat, code in HARD_EXCLUSION_PATTERNS:
            if re.search(pat, text, re.I):
                reasons.append({"axis": "exclusion", "level": "veto", "detail": code})
                hard_veto = True

        if directive.get("no_reaction_clips"):
            reasons.append({"axis": "source", "level": "warning",
                            "detail": "no reaction clips — à vérifier manuellement"})

        # toujours poser `status` explicitement (robustesse)
        c["status"] = "auto_rejected" if hard_veto else c.get("status", "scored")

        if hard_veto:
            veto_count += 1
            rr = c.get("rejection_reasons") or []
            if "campaign_veto" not in rr:
                rr.append("campaign_veto")
            c["rejection_reasons"] = rr

        c["campaign_check"] = {"status": "veto" if hard_veto else "pass", "reasons": reasons}

    return scored, veto_count
