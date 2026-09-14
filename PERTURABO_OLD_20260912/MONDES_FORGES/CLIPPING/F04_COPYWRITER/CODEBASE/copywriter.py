"""
copywriter.py — F04_COPYWRITER : La Plume de la Forteresse (forge CLIPPING)
===========================================================================

Frégate lourde de la Porte 3. Forge le text_payload complet pour chaque
angle : 3 titres calibrés + paragraphe reframing + caption + hashtags 3
strates + on-screen text + CTA.

SINGULARITÉ — rupture du pattern 3 phases. F04 parle DIRECT au modèle
premium (clé API dédiée). L'IRON (sandbox Claude) ordonnance seulement.

   Phase A : setup_context        (context_builder rassemble l'ARCHIVUM)
   Phase B : premium_generation   (premium_client — premium direct)
   Phase C : iron_ordonnancing    (iron_ordonnancer — validation + classement)
   Phase D : finalize + ledger    (md_renderer + check-in IW_CUSTOS)

Usage:
  python copywriter.py --init-systemprompt [--force]        # one-time
  python copywriter.py --setup-context --angle A01 [--platform p] [--market m]
  python copywriter.py --generate --angle A01 [--dry-run]
  python copywriter.py --ordonnance --angle A01 [--auto-ord]
  python copywriter.py --finalize --angle A01
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_F04_DIR = os.path.dirname(_SCRIPT_DIR)
_FORGE_ROOT = os.path.dirname(_F04_DIR)

sys.path.insert(0, os.path.join(_SCRIPT_DIR, "libs"))
from context_builder import ContextBuilder
from premium_client import PremiumClient, PremiumClientError
from iron_ordonnancer import IronOrdonnancer
from compliance_checker import ComplianceChecker
from md_renderer import MdRenderer

# Profil actif (whop | logo) — lu depuis liber_clipping.json
sys.path.insert(0, os.path.join(_FORGE_ROOT, "SHARED"))
from profile_loader import load_profile

# --- Bloc LOGO v2 (profil logo) -----------------------------------------
FAIR_USE_NOTE = (
    "Copyright Disclaimer: Under Section 107 of the Copyright Act of 1976, "
    "allowance is made for \"fair use\" for purposes such as criticism, comment, "
    "news reporting, teaching, scholarship, and research. Fair use is a use "
    "permitted by copyright statute that might otherwise be infringing. "
    "Non-profit, educational or personal use tips the balance in favor of fair use."
)
LOGO_MAX_TITLE_WORDS = 6
LOGO_MAX_PARAGRAPH_LINES = 4
LOGO_MAX_PARAGRAPH_CHARS = 400

OUT_DIR = os.path.join(_F04_DIR, "OUT")
IN_DIR = os.path.join(_F04_DIR, "IN")
CONTRACTS_DIR = os.path.join(_FORGE_ROOT, "CONTRACTS")
ARCHIVUM_DIR = os.path.join(_FORGE_ROOT, "ARCHIVUM")
F02_OUT = os.path.join(_FORGE_ROOT, "F02_TYRANT_CAMP", "OUT")
F03_OUT = os.path.join(_FORGE_ROOT, "F03_SOURCE_HUNTER", "OUT")
LIBER_PATH = os.path.join(_FORGE_ROOT, "liber_clipping.json")

SYSTEM_PROMPT_PATH = os.path.join(CONTRACTS_DIR, "copywriter_systemprompt.md")
DOCTRINE_PATH = os.path.join(CONTRACTS_DIR, "copywriting_doctrine.md")
SECRETS_PATH = os.path.join(CONTRACTS_DIR, "copywriter_secrets.json")
SECRETS_EXAMPLE_PATH = os.path.join(CONTRACTS_DIR, "copywriter_secrets.example.json")

PLACEHOLDER_MARKER = "NON GÉNÉRÉ"


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def save_json(path: str, data: dict):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


# ----------------------------------------------------------------------
# Résolution des entrées
# ----------------------------------------------------------------------
def find_angles_path() -> str:
    candidates = [
        os.path.join(F02_OUT, "angles.json"),
        os.path.join(_FORGE_ROOT, "ANGLESMITH", "OUT", "angles.json"),
    ]
    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate
    print("[F04] angles.json introuvable (F02_TYRANT_CAMP/OUT ou ANGLESMITH/OUT)")
    print("[F04] Lancer ANGLESMITH --finalize d'abord (Porte 2)")
    sys.exit(1)


def load_angles() -> list[dict]:
    data = load_json(find_angles_path())
    angles = data.get("angles", [])
    if not angles:
        print("[F04] angles.json vide")
        sys.exit(1)
    return angles


def find_angle(angle_id: str) -> dict:
    for angle in load_angles():
        if angle.get("angle_id") == angle_id:
            return angle
    print(f"[F04] Angle inconnu: {angle_id} — angles.json ne contient pas cet id")
    sys.exit(1)


def find_verdict() -> dict:
    for path in (os.path.join(ARCHIVUM_DIR, "campaign", "verdict.json"),
                 os.path.join(F02_OUT, "campaign_verdict.json")):
        if os.path.exists(path):
            return load_json(path)
    print("[F04] campaign_verdict.json introuvable — verdict vide")
    return {}


def find_specimen(angle_id: str) -> dict:
    path = os.path.join(F03_OUT, f"source_specimen_{angle_id}.json")
    if not os.path.exists(path):
        print(f"[F04] Specimen F03 introuvable: {path}")
        print("[F04] Lancer F03_SOURCE_HUNTER d'abord (Porte 3)")
        sys.exit(1)
    return load_json(path)


def warsmith_targets(args) -> tuple[str, str]:
    platform = getattr(args, "platform", None)
    market = getattr(args, "market", None)
    if not platform or not market:
        if os.path.exists(LIBER_PATH):
            inputs = load_json(LIBER_PATH).get("inputs_warsmith", {})
            platform = platform or inputs.get("platform_target")
            market = market or inputs.get("market_target")
    return platform or "youtube", market or "unknown"


# ----------------------------------------------------------------------
# LOGO v2 — helpers (profil logo)
# ----------------------------------------------------------------------
def is_logo() -> bool:
    try:
        return load_profile().mode == "logo"
    except Exception:
        return False


def _logo_campaign_inputs() -> dict:
    campaign = {}
    for name in ("reference_clip.json", "article_source.json",
                 "joke_source.json", "reference_clip_style.json"):
        path = os.path.join(ARCHIVUM_DIR, "campaign", name)
        if os.path.exists(path):
            try:
                campaign[name.replace(".json", "")] = load_json(path)
            except Exception:
                campaign[name.replace(".json", "")] = {}
    kw_path = os.path.join(ARCHIVUM_DIR, "campaign", "keyword.txt")
    if os.path.exists(kw_path):
        try:
            campaign["keyword"] = read_text(kw_path).strip()
        except OSError:
            campaign["keyword"] = None
    return campaign


def _detect_sub_mode(args) -> str:
    sm = (getattr(args, "sub_mode", None) or "").lower()
    if sm in ("informatif", "humour", "meme", "meme_v2"):
        return sm
    campaign = _logo_campaign_inputs()
    if campaign.get("joke_source"):
        return "humour"
    if campaign.get("keyword"):
        return "meme"
    return "informatif"


def _campaign_hashtags() -> list[str]:
    """Hashtags campagne (directive.md, ligne 'Hashtags:'). Jamais inventés."""
    path = os.path.join(ARCHIVUM_DIR, "campaign", "directive.md")
    if not os.path.exists(path):
        return []
    try:
        for line in read_text(path).splitlines():
            if line.strip().lower().startswith("hashtags:"):
                raw = line.split(":", 1)[1]
                return [t.strip() for t in raw.split() if t.strip().startswith("#")]
    except OSError:
        pass
    return []


def _normalize_tags(values) -> list[str]:
    """Normalise la liste de tags : str, préfixe '#', sans doublon (case
    insensible), max 15. Utilisée pour metadata.tags et la ligne hashtags."""
    seen = set()
    tags = []
    for t in values or []:
        if not isinstance(t, str):
            continue
        t = t.strip().strip("#").strip()
        if not t:
            continue
        key = t.lower().replace(" ", "")
        if key in seen:
            continue
        seen.add(key)
        tags.append(f"#{t}")
        if len(tags) >= 15:
            break
    return tags


def _active_channel_slug() -> str:
    """Slug du compte actif (ARCHIVUM/campaign/channel.txt). Retour '' sinon."""
    slug_path = os.path.join(ARCHIVUM_DIR, "campaign", "channel.txt")
    if not os.path.exists(slug_path):
        return ""
    try:
        return read_text(slug_path).strip()
    except OSError:
        return ""


def _channel_tags() -> list[str]:
    """Tags de chaîne (channel_tags.md du compte actif, bloc ``` ```) :
    liste de tags complémentaires, normalisés '#', max 15. Retour [] sinon."""
    slug = _active_channel_slug()
    if not slug:
        return []
    path = os.path.join(ARCHIVUM_DIR, "channels", slug, "channel_tags.md")
    if not os.path.exists(path):
        return []
    try:
        content = read_text(path)
    except OSError:
        return []
    lines = []
    capture = False
    for line in content.splitlines():
        if line.startswith("```"):
            capture = not capture
            continue
        if capture:
            lines.append(line)
    raw_tags = []
    for line in lines:
        raw_tags.extend(t.strip() for t in line.split(",") if t.strip())
    return _normalize_tags(raw_tags)


def _channel_base_paragraph() -> str:
    """Paragraphe de base du compte (description_base_paragraph.md dans
    ARCHIVUM/channels/<slug>/) : avertissement non-monétisation + note fair
    use, injecté en fin de chaque description vidéo. Slug lu depuis
    ARCHIVUM/campaign/channel.txt. Retour '' si absent."""
    slug_path = os.path.join(ARCHIVUM_DIR, "campaign", "channel.txt")
    if not os.path.exists(slug_path):
        return ""
    try:
        slug = read_text(slug_path).strip()
    except OSError:
        return ""
    if not slug:
        return ""
    para_path = os.path.join(ARCHIVUM_DIR, "channels", slug,
                             "description_base_paragraph.md")
    if not os.path.exists(para_path):
        return ""
    try:
        content = read_text(para_path)
    except OSError:
        return ""
    lines = []
    capture = False
    for line in content.splitlines():
        if line.startswith("```"):
            capture = not capture
            continue
        if capture:
            lines.append(line)
    return "\n".join(lines).strip()


def _ordonnance_logo(raw: dict, angle: dict, sub_mode: str,
                     platform: str, market: str,
                     campaign_id: str = None) -> tuple[dict, list[str]]:
    notes = []
    title = str(raw.get("title") or "").strip()
    words = len(title.split())
    if words > LOGO_MAX_TITLE_WORDS:
        notes.append(f"titre {words} mots > {LOGO_MAX_TITLE_WORDS} — tronqué au "
                     f"{LOGO_MAX_TITLE_WORDS}e mot")
        title = " ".join(title.split()[:LOGO_MAX_TITLE_WORDS])

    viral = str(raw.get("viral_paragraph") or "").strip()
    lines = viral.count("\n") + 1 if viral else 0
    if lines > LOGO_MAX_PARAGRAPH_LINES:
        notes.append(f"paragraphe {lines} lignes > {LOGO_MAX_PARAGRAPH_LINES}")
    if len(viral) > LOGO_MAX_PARAGRAPH_CHARS:
        notes.append(f"paragraphe {len(viral)} chars > {LOGO_MAX_PARAGRAPH_CHARS} — "
                     f"tronqué à {LOGO_MAX_PARAGRAPH_CHARS}")
        viral = viral[:LOGO_MAX_PARAGRAPH_CHARS].rstrip()

    meta = raw.get("metadata") or {}
    description = str(meta.get("description") or viral).strip()
    if sub_mode in ("informatif", "meme"):
        lower = description.lower()
        if "fair use" not in lower and "illustration" not in lower:
            description = f"{description}\n\n{FAIR_USE_NOTE}".strip()
            notes.append("note fair use ajoutée à la description")
    base_para = _channel_base_paragraph()
    if base_para:
        lower = description.lower()
        if "not monetized" not in lower and "not monetised" not in lower:
            description = f"{description}\n\n{base_para}".strip()
            notes.append("paragraphe de base du compte ajouté à la description")
    tags = _normalize_tags(meta.get("tags") or raw.get("tags") or [])
    for ht in _campaign_hashtags():
        if ht not in tags:
            tags.append(ht)
    for ct in _channel_tags():
        if len(tags) >= 15:
            break
        if ct not in tags:
            tags.append(ct)
    tags = tags[:15]
    if tags:
        hashtag_line = ", ".join(tags)
        if hashtag_line.lower() not in description.lower():
            description = f"{description}\n\n{hashtag_line}".strip()
            notes.append("ligne de 15 hashtags ajoutée à la description")

    payload = {
        "campaign_id": raw.get("campaign_id") or campaign_id,
        "angle_id": angle.get("angle_id"),
        "sub_mode": sub_mode,
        "title": title,
        "viral_paragraph": viral,
        "metadata": {
            "title": str(meta.get("title") or title),
            "description": description,
            "tags": tags,
        },
        "on_screen_text": raw.get("on_screen_text")
                          or angle.get("on_screen_text"),
        "check_in_iw_custos": None,
    }

    if sub_mode in ("meme", "meme_v2"):
        tweet_raw = raw.get("tweet") or {}
        if isinstance(tweet_raw, str):
            tweet_raw = {"text": tweet_raw}
        tweet = str(tweet_raw.get("text") or "").strip()
        tweet_lines = len(tweet.splitlines()) if tweet else 0
        if tweet_lines > 3:
            notes.append(f"tweet {tweet_lines} lignes > 3 — tronqué à 3")
            tweet = "\n".join(tweet.splitlines()[:3])
        reaction = str(raw.get("text_emotion") or "").strip()
        reaction_words = len(reaction.split()) if reaction else 0
        if reaction_words > 4:
            notes.append(f"reaction {reaction_words} mots > 4 — tronqué à 4")
            reaction = " ".join(reaction.split()[:4])
        emotion = str(raw.get("emotion")
                      or angle.get("emotion")
                      or angle.get("emotion_mode")
                      or "").strip()
        dur_raw = raw.get("duration_sec")
        try:
            dur_sec = max(5, min(30, int(dur_raw))) if dur_raw else 8
        except (TypeError, ValueError):
            dur_sec = 8
        keywords_style = _normalize_keywords_style(
            tweet_raw.get("keywords_style"), tweet)
        payload["tweet"] = {
            "text": tweet or None,
            "keywords_style": keywords_style,
        }
        payload["reaction_tweet"] = str(raw.get("reaction_tweet") or tweet or "").strip() or None
        payload["text_emotion"] = reaction or None
        payload["emotion"] = emotion or None
        payload["duration_sec"] = dur_sec

    return payload, notes


def _tweet_tokens(text: str) -> set:
    """Mots seuls du tweet, ponctuation ignorée (apostrophes, $, #, virgules…)."""
    import re
    return set(re.findall(r"[a-z0-9]+", (text or "").lower()))


def _normalize_keywords_style(kws_style, tweet_text: str = "") -> dict:
    """Normalise tweet.keywords_style au format LACRIMAE v2.5 :
    DICT {"green": [...], "red": [...]} (clés anglaises). Chaque entrée est un
    MOT SEUL présent mot à mot dans tweet.text (ponctuation ignorée) ; les
    phrases multi-mots ne matchent jamais. Une LISTE [{word, color}] (ancien
    format) → aucune couleur (dict vide) conformément à la note LACRIMAE."""
    empty = {"green": [], "red": []}
    if not isinstance(kws_style, dict):
        return empty
    tokens = _tweet_tokens(tweet_text)
    result = {"green": [], "red": []}
    for key in ("green", "red"):
        entries = kws_style.get(key)
        if not isinstance(entries, list):
            continue
        seen = set()
        for entry in entries:
            word = str(entry or "").strip()
            word_tokens = set(_tweet_tokens(word))
            if len(word_tokens) != 1:
                continue  # phrase multi-mots ou vide → jamais matchée
            token = next(iter(word_tokens))
            if token not in tokens:
                continue  # mot absent du tweet (mot à mot) → retiré
            if token in seen:
                continue
            seen.add(token)
            result[key].append(word)
    return result


def _meme_heresies(sub_mode: str) -> list[str]:
    if sub_mode not in ("meme", "meme_v2"):
        return [
            "Abonne-toi / Like et partage / Swipe up",
            "Titre > 6 mots",
            "Paragraphe > 4 lignes",
            "Mentionner que le clip est un background (l'audience ne doit pas le voir)",
            "Fabrication de faits absents de l'article",
        ]
    return [
        "Abonne-toi / Like et partage / Swipe up",
        "tweet.text > 3 lignes",
        "text_emotion > 4 mots",
        "Titre en haut > 6 mots (ou clickbait vide sans payoff)",
        "URL de meme / vidéo dans le pack (les sources restent dans le scan F00)",
        "Inventer une stat virale absente du scan F00",
        "Timecodes / segments de coupe (F01/F03 sont SKIP en mode meme)",
    ]


def _render_keywords_md(kws: dict) -> str:
    if not isinstance(kws, dict) or not (kws.get("green") or kws.get("red")):
        return ""
    lines = ["**Mots-clés colorés (LACRIMAE)** :"]
    for color in ("green", "red"):
        for word in kws.get(color) or []:
            lines.append(f"- `{word}` — {color}")
    return "\n".join(lines) + "\n"


def _render_logo_md(payload: dict) -> str:
    meta = payload.get("metadata", {})
    if payload.get("sub_mode") in ("meme", "meme_v2"):
        tweet = (payload.get("tweet") or {}).get("text")
        kws = (payload.get("tweet") or {}).get("keywords_style") or []
        return (
            f"# Pack texte LOGO MEME — {payload.get('angle_id')}\n\n"
            f"**Titre en haut (si nécessaire, ≤6 mots)** : "
            f"{payload.get('title') or '—'}\n\n"
            f"**Fake tweet (max 3 lignes)** :\n{tweet or '—'}\n"
            f"{_render_keywords_md(kws)}\n"
            f"**Texte d'émotion (max 4 mots)** : {payload.get('text_emotion') or '—'}\n"
            f"**Émotion** : {payload.get('emotion') or '—'}\n"
            f"**Durée (s)** : {payload.get('duration_sec', 8)}s\n\n"
            f"**Metadata** :\n- Title : {meta.get('title')}\n"
            f"- Description :\n{meta.get('description')}\n"
            f"- Tags : {', '.join(meta.get('tags', []))}\n"
        )
    return (
        f"# Pack texte LOGO — {payload.get('angle_id')}\n\n"
        f"**Titre viral ({LOGO_MAX_TITLE_WORDS} mots max)** :\n{payload.get('title')}\n\n"
        f"**Paragraphe viral ({LOGO_MAX_PARAGRAPH_LINES} lignes max)** :\n"
        f"{payload.get('viral_paragraph')}\n\n"
        f"**Metadata** :\n- Title : {meta.get('title')}\n"
        f"- Description :\n{meta.get('description')}\n"
        f"- Tags : {', '.join(meta.get('tags', []))}\n\n"
        f"**On-screen** : {payload.get('on_screen_text') or '—'}\n"
    )


# ----------------------------------------------------------------------
# INIT — système prompt (one-time, à ne pas refaire)
# ----------------------------------------------------------------------
def cmd_init_systemprompt(args):
    if not os.path.exists(DOCTRINE_PATH):
        print(f"[F04] Doctrine introuvable: {DOCTRINE_PATH}")
        sys.exit(1)
    if os.path.exists(SYSTEM_PROMPT_PATH) and not getattr(args, "force", False):
        content = read_text(SYSTEM_PROMPT_PATH)
        if PLACEHOLDER_MARKER not in content:
            print("[F04] copywriter_systemprompt.md déjà généré — figé. "
                  "Refaire l'init uniquement avec --force (mise à jour majeure doctrine).")
            sys.exit(1)

    doctrine = read_text(DOCTRINE_PATH)
    builder = ContextBuilder(_FORGE_ROOT)
    archivum = builder.collect_archivum("youtube", "unknown")
    copywriting_dir = os.path.join(ARCHIVUM_DIR, "copywriting")
    sub_dirs = sorted(
        name for name in os.listdir(copywriting_dir)
        if os.path.isdir(os.path.join(copywriting_dir, name))
    )

    meta_prompt = (
        "Tu es le modèle premium de F04_COPYWRITER. Tu dois générer le SYSTEM PROMPT "
        "final de la frégate copywriting, figé ensuite pour toutes les exécutions.\n\n"
        "MATIÈRE SOURCE (ne pas régurgiter, synthétiser) :\n\n"
        "1) DOCTRINE COMPLÈTE :\n"
        + doctrine
        + "\n\n2) SOUS-DOSSIERS ARCHIVUM/copywriting/ (8) :\n- "
        + "\n- ".join(sub_dirs)
        + "\n\n3) CONTEXTE ARCHIVUM (règles, angles, learnings, demons) :\n"
        + json.dumps(archivum, indent=2, ensure_ascii=False)[:60000]
        + "\n\nLe system prompt final DOIT contenir :\n"
        "- Contexte : rôle de la frégate, singularité 4 phases, premium direct\n"
        "- Doctrine : résumé des 10 sections (I-X)\n"
        "- Capacités : 3 titres + paragraphe + caption + hashtags + on-screen + CTA\n"
        "- Contraintes : format JSON strict (schéma text_payload_*.json)\n"
        "- Garde-fous : anti-bullshit, FTC, hérésies (section X)\n"
        "Réponds avec UNIQUEMENT le system prompt final en markdown, "
        "sans en-tête ni explication."
    )

    client = PremiumClient(_FORGE_ROOT)
    if not client._api_key():
        # ---- MODE BACKUP ORACLE pour l'init systemprompt -------------------
        if getattr(args, "oracle", False):
            out = os.path.join(IN_DIR, "systemprompt_oracle_prompt.json")
            save_json(out, {
                "mode": "oracle — backup sans clé premium",
                "model_id": client.config.get("model_id", "<model_premium_id>"),
                "system_prompt": "Tu es l'architecte du system prompt de la frégate copywriting.",
                "user_prompt": meta_prompt,
            })
            print(f"[F04] MODE ORACLE : prompt écrit dans {out}")
            print("[F04] L'Oracle forge le system prompt markdown → "
                  f"CONTRACTS/copywriter_systemprompt.md (en-tête inclus)")
            sys.exit(1)
        print("[F04] Clé premium absente — 2 options :")
        print("  1) Définir la clé (API Keys) : env CLIPPING_PREMIUM_API_KEY")
        print("  2) Mode backup : --init-systemprompt --oracle")
        sys.exit(1)

    client.require_config()
    result = client.chat(
        system_prompt="Tu es l'architecte du system prompt de la frégate copywriting.",
        user_prompt=meta_prompt,
    )
    if not result:
        sys.exit(1)

    header = (
        "# COPYWRITER SYSTEMPROMPT — GÉNÉRÉ PAR LE MODÈLE PREMIUM (init one-time)\n"
        f"\n> * Généré le : {now_iso()} — FIGÉ. Ne pas réécrire sans --force. *\n\n---\n\n"
    )
    with open(SYSTEM_PROMPT_PATH, "w", encoding="utf-8") as f:
        f.write(header + result.strip() + "\n")
    print(f"[F04] System prompt figé : {SYSTEM_PROMPT_PATH}")


# ----------------------------------------------------------------------
# Phase A — setup_context
# ----------------------------------------------------------------------
def cmd_setup_context(args):
    angle = find_angle(args.angle)
    specimen = find_specimen(args.angle)
    verdict = find_verdict()
    platform, market = warsmith_targets(args)

    builder = ContextBuilder(_FORGE_ROOT)
    context = builder.build(angle, specimen, verdict, platform, market)

    out = os.path.join(IN_DIR, f"copywriter_context_{args.angle}.json")
    save_json(out, context)
    size_kb = os.path.getsize(out) // 1024
    print(f"[F04] Phase A : {out} ({size_kb} KB)")
    print(f"[F04] Angle {args.angle} — {angle.get('angle_family')}/{angle.get('emotion_mode')} "
          f"— {platform} / {market}")
    print("[F04] Lancer --generate pour la Phase B (premium direct)")


# ----------------------------------------------------------------------
# Phase B — premium_generation
# ----------------------------------------------------------------------
def _load_context(angle_id: str) -> dict:
    path = os.path.join(IN_DIR, f"copywriter_context_{angle_id}.json")
    if not os.path.exists(path):
        print(f"[F04] Contexte introuvable: {path}")
        print("[F04] Lancer --setup-context d'abord (Phase A)")
        sys.exit(1)
    return load_json(path)


def cmd_generate(args):
    angle = find_angle(args.angle)
    context = _load_context(args.angle)
    platform = context.get("platform_target", "youtube")
    market = context.get("market_target", "unknown")

    system_prompt = ""
    if os.path.exists(SYSTEM_PROMPT_PATH):
        system_prompt = read_text(SYSTEM_PROMPT_PATH)
    if not system_prompt or PLACEHOLDER_MARKER in system_prompt:
        if not getattr(args, "force", False):
            print("[F04] copywriter_systemprompt.md non généré (placeholder).")
            print("[F04] Lancer --init-systemprompt (one-time) ou --generate --force.")
            sys.exit(1)
        system_prompt = (
            "Tu es F04_COPYWRITER, frégate copywriting du forge CLIPPING. "
            "Tu forges des text_payloads gagnants (3 titres + paragraphe + caption "
            "+ hashtags + on-screen + CTA). Réponds en JSON strict conforme au schéma "
            "text_payload_*.json. Interdits : 'abonne-toi', clickbait sans payoff, "
            "paragraphe > 2 lignes, reframing qui ment sur la source."
        )

    user_prompt = {
        "mission": (
            "Forge le text_payload complet pour CET angle : 3 titres calibrés "
            "(scorés platform_fit/market_fit/hook_type), un paragraphe reframing "
            "(2 lignes max), caption, hashtags 3 strates (large + moyen + niche), "
            "on-screen text (1 keyframe max), cta_text subtil. "
            "Respecte le schéma JSON strict ci-dessous."
        ),
        "campaign_id": context.get("campaign_id"),
        "angle_id": args.angle,
        "angle": context.get("angle"),
        "specimen_source": context.get("specimen"),
        "verdict": context.get("verdict"),
        "platform_target": platform,
        "market_target": market,
        "archivum": context.get("archivum"),
        "output_schema": {
            "titles": [
                {"rank": 1, "text": "...", "platform_fit": 0, "market_fit": 0,
                 "hook_type": "stat_choc|question|declaration|mystery|contradiction|cible_naming",
                 "rationale": "..."}
            ],
            "paragraph": {"text": "...", "recommendation": "use|skip",
                          "override_omniswatch": None, "final_operator": None},
            "caption": "...",
            "hashtags": ["#...", "#...", "#..."],
            "on_screen_text": "...|null",
            "cta_text": "...",
            "compliance": {"disclosure": "#ad", "ftc_required": True},
        },
        "heresies_interdites": [
            "Abonne-toi / Like et partage / Swipe up dans CTA, caption ou on-screen",
            "Clickbait sans payoff (le titre doit livrer dans la vidéo)",
            "Reframing qui ment sur le contenu source (anti-cond)",
            "Paragraphe > 2 lignes",
            "Hashtags sans strate niche",
        ],
    }

    client = PremiumClient(_FORGE_ROOT)
    if getattr(args, "dry_run", False):
        call = {
            "mode": "dry-run — aucun appel réseau",
            "model_id": client.config.get("model_id", "<model_premium_id>"),
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
        }
        out = os.path.join(IN_DIR, f"premium_call_{args.angle}.json")
        save_json(out, call)
        print(f"[F04] Phase B (dry-run) : {out}")
        print("[F04] Aucun appel premium effectué — vérifier le prompt, puis --generate")
        return

    if not client._api_key():
        # ---- MODE BACKUP ORACLE (profil whop) -------------------------------
        if getattr(args, "oracle", False):
            call = {
                "mode": "oracle — backup sans clé premium",
                "model_id": client.config.get("model_id", "<model_premium_id>"),
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
            }
            out = os.path.join(IN_DIR, f"premium_call_{args.angle}.json")
            save_json(out, call)
            raw_path = os.path.join(OUT_DIR, f"text_payload_raw_{args.angle}.json")
            if os.path.exists(raw_path):
                print(f"[F04] MODE ORACLE : raw déjà forgé ({os.path.basename(raw_path)}) "
                      f"— lancer --ordonnance")
                return
            print(f"[F04] MODE ORACLE : prompt écrit dans {out}")
            print(f"[F04] L'Oracle doit forger OUT/text_payload_raw_{args.angle}.json "
                  "(schéma output_schema), puis relancer --generate --oracle")
            sys.exit(1)
        print("[F04] Clé premium absente — 2 options :")
        print("  1) Définir la clé (API Keys) : env CLIPPING_PREMIUM_API_KEY")
        print("  2) Mode backup : --generate --oracle (l'Oracle forge le texte)")
        sys.exit(1)

    client.require_config()
    user_text = json.dumps(user_prompt, indent=2, ensure_ascii=False)
    result = client.chat(system_prompt=system_prompt, user_prompt=user_text)
    if not result:
        print("[F04] Échec de la génération premium — OUT/text_payload_raw absent")
        sys.exit(1)

    try:
        raw = json.loads(client.extract_json(result))
    except (json.JSONDecodeError, ValueError) as e:
        fallback = os.path.join(OUT_DIR, f"text_payload_raw_{args.angle}.txt")
        with open(fallback, "w", encoding="utf-8") as f:
            f.write(result)
        print(f"[F04] Sortie premium non-JSON: {e}")
        print(f"[F04] Réponse brute conservée : {fallback}")
        print("[F04] L'IRON (Phase C) ne peut pas ordonnancer du non-JSON — relancer ou corriger")
        sys.exit(1)

    raw["campaign_id"] = context.get("campaign_id")
    raw["angle_id"] = args.angle
    out = os.path.join(OUT_DIR, f"text_payload_raw_{args.angle}.json")
    save_json(out, raw)
    print(f"[F04] Phase B : {out}")
    print("[F04] Lancer --ordonnance pour la Phase C (IRON)")


# ----------------------------------------------------------------------
# Phase C — iron_ordonnancing
# ----------------------------------------------------------------------
def _load_raw(angle_id: str) -> dict:
    path = os.path.join(OUT_DIR, f"text_payload_raw_{angle_id}.json")
    if not os.path.exists(path):
        print(f"[F04] Sortie premium introuvable: {path}")
        print("[F04] Lancer --generate d'abord (Phase B)")
        sys.exit(1)
    return load_json(path)


def cmd_ordonnance(args):
    angle = find_angle(args.angle)
    raw = _load_raw(args.angle)
    context = _load_context(args.angle)
    platform = context.get("platform_target", "youtube")
    market = context.get("market_target", "unknown")

    ordonnancer = IronOrdonnancer()
    checker = ComplianceChecker()

    if getattr(args, "auto_ord", False):
        payload, notes = ordonnancer.ordonnance_auto(
            raw, angle, platform, market,
            campaign_id=context.get("campaign_id"))
        issues = checker.check(payload)
        save_json(os.path.join(OUT_DIR, f"text_payload_{args.angle}.json"), payload)
        print(f"[F04] Phase C (auto) : OUT/text_payload_{args.angle}.json")
        for note in notes:
            print(f"  - {note}")
        for issue in issues:
            print(f"  [{issue['severity']}] {issue['code']}: {issue['message']}")
        return

    prompt = ordonnancer.build_iron_prompt(raw, angle, platform, market)
    out = os.path.join(IN_DIR, f"ordonnance_prompt_{args.angle}.json")
    save_json(out, prompt)
    print(f"[F04] Phase C : {out}")
    print("[F04] Copier le prompt dans Claude sandbox -> OUT/text_payload_<angle>.json, "
          "puis --finalize")


# ----------------------------------------------------------------------
# Phase D — finalize + ledger
# ----------------------------------------------------------------------
def cmd_finalize(args):
    angle = find_angle(args.angle)
    path = os.path.join(OUT_DIR, f"text_payload_{args.angle}.json")
    if not os.path.exists(path):
        print(f"[F04] text_payload ordonnancé introuvable: {path}")
        print("[F04] Lancer --ordonnance d'abord (Phase C)")
        sys.exit(1)

    payload = load_json(path)
    checker = ComplianceChecker()
    criticals = [i for i in checker.check(payload) if i["severity"] == "critical"]
    if criticals:
        print(f"[F04] HÉRÉSIES critiques — finalize refusé pour {args.angle} :")
        for issue in criticals:
            print(f"  - {issue['code']}: {issue['message']}")
        sys.exit(1)

    angles = load_angles()
    payload["check_in_iw_custos"] = now_iso()
    save_json(path, payload)

    index = sorted(a.get("angle_id") for a in angles).index(args.angle) + 1
    renderer = MdRenderer()
    md = renderer.render(payload, index=index, total=len(angles))
    md_path = os.path.join(OUT_DIR, f"text_payload_{args.angle}.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md)
    print(f"[F04] Phase D : {md_path} (lisible opérateur)")

    all_done = all(
        os.path.exists(os.path.join(OUT_DIR, f"text_payload_{a.get('angle_id')}.json"))
        for a in angles
    )
    if all_done:
        custos = os.path.join(_FORGE_ROOT, "IW_CUSTOS.py")
        if os.path.exists(custos):
            subprocess.run(
                [sys.executable, custos, "--mode", "check-in",
                 "--frigate", "F04", "--output", md_path],
                capture_output=True, text=True, timeout=30,
            )
        print("[F04] Check-in IW_CUSTOS — fleet_status -> text_payloads_forged")
    else:
        print("[F04] Tous les angles pas encore finalisés — check-in IW_CUSTOS "
              "au finalize du dernier angle")

    print("[F04] OUT prêt pour F05_PACKAGER (production_pack) et l'Oracle OMNIS_WATCH")


# ----------------------------------------------------------------------
# LOGO v2 — Phases (profil logo, PAS de F03 : le clip vient du Warsmith)
# ----------------------------------------------------------------------
def cmd_setup_context_logo(args):
    angle = find_angle(args.angle)
    sub_mode = _detect_sub_mode(args)
    verdict = find_verdict()
    platform, market = warsmith_targets(args)
    campaign = _logo_campaign_inputs()

    if sub_mode == "meme":
        campaign["meme_source"] = _load_meme_scan()
    elif sub_mode == "meme_v2":
        source = ContextBuilder(_FORGE_ROOT)._load_meme_v2_source()
        campaign["meme_v2_source"] = source
        target = source.get("target") or {}
        platform = target.get("platform") or platform
        market = target.get("market") or market

    builder = ContextBuilder(_FORGE_ROOT)
    context = builder.build_logo(angle, sub_mode, campaign, verdict,
                                 platform, market)
    out = os.path.join(IN_DIR, f"copywriter_context_{args.angle}.json")
    save_json(out, context)
    print(f"[F04:LOGO] Phase A : {out} ({os.path.getsize(out)//1024} KB)")
    print(f"[F04:LOGO] Angle {args.angle} — sub_mode {sub_mode} — {platform} / {market}")
    print("[F04:LOGO] Lancer --generate pour la Phase B (premium direct)")


def _load_meme_scan() -> dict:
    """Charge le scan viralité F00 le plus récent (mode meme).
    Priorité au scan correspondant au mot-clé du siège (keyword.txt)."""
    f00_out = os.path.join(_FORGE_ROOT, "F00_CAPTEURS", "OUT")
    candidates = sorted(
        f for f in os.listdir(f00_out)
        if f.startswith("meme_virality_") and f.endswith(".json")
    ) if os.path.isdir(f00_out) else []
    if not candidates:
        print("[F04:LOGO] Aucun scan meme F00 — contexte meme sans stats "
              "(F00 --scan-meme requis en Gate 1)")
        return {}
    kw_path = os.path.join(_FORGE_ROOT, "ARCHIVUM", "campaign", "keyword.txt")
    if os.path.exists(kw_path):
        try:
            with open(kw_path, "r", encoding="utf-8") as f:
                wanted = f.read().strip().lower()
        except OSError:
            wanted = None
        if wanted:
            import re as _re
            safe_wanted = _re.sub(r"[^a-z0-9]+", "_", wanted).strip("_")
            match = os.path.join(f00_out, f"meme_virality_{safe_wanted}.json")
            if os.path.exists(match):
                return load_json(match)
    return load_json(os.path.join(f00_out, candidates[-1]))


def cmd_generate_logo(args):
    angle = find_angle(args.angle)
    context = _load_context(args.angle)
    sub_mode = context.get("sub_mode", "informatif")
    platform = context.get("platform_target", "youtube")
    market = context.get("market_target", "unknown")

    system_prompt = (
        "Tu es F04_COPYWRITER, frégate copywriting du forge CLIPPING — profil LOGO. "
        "Le clip source est FOURNI par le Warsmith et ne sert que d'illustration "
        "(aucun lien avec le sujet) — sauf mode meme où AUCUN clip n'est fourni "
        "(le mot-clé + les stats F00 font foi). Tu forges le pack texte d'une video "
        "virale. Réponds en JSON strict conforme à l'output_schema. Contraintes: titre "
        f"{LOGO_MAX_TITLE_WORDS} mots max, paragraphe {LOGO_MAX_PARAGRAPH_LINES} "
        "lignes max, description en 2 paragraphes (résumé + note fair use) en mode "
        "informatif/meme, jamais de 'abonne-toi'."
        " IMPORTANT: Écris TOUT (titres, paragraphe, tweet, reaction, description, "
        "tags, on-screen) en ANGLAIS, même si l'article source est dans une autre langue."
    )

    if sub_mode == "meme_v2":
        source = context.get("meme_v2_source") or {}
        mission = (
            "Mode MEME V2 : utilise exclusivement le post réel fourni par F01. "
            "Forge pour CET angle un reaction_tweet original, puissant et ciblé sur "
            "le marché US des 29-30 ans. La réaction doit transformer la situation du "
            "téléphone qui rebondit du lit au sol, sans inventer de nouveau post ni "
            "réécrire la source. Produis aussi un text_emotion contextualisé aux "
            "personnes ou au groupe évoqué, maximum 4 mots avant le deux-points, "
            "puis emotion, metadata (title, description, tags, hashtags) et duration_sec=5. "
            "Tout en anglais US. Interdits : A/B, personnage absent, Doom, Students "
            "reading this, fair-use ou promesse de monétisation, et toute formule d’un "
            "autre siège. Réponds en JSON strict."
        )
    elif sub_mode == "meme":
        keyword = (context.get("keyword")
                   or (context.get("clip_source_ref") or {}).get("keyword")
                   or "inconnu")
        mission = (
            "Mode MEME : à partir du mot-clé viral et des stats réelles du "
            "scan F00, forge pour CET angle : 1) title (le titre en haut, "
            "max 6 mots, SI nécessaire seulement — jamais de clickbait vide), "
            "2) tweet.text (le FAKE tweet du faux post, format X/Twitter, 3 lignes maximum) : "
            "écris un tweet naturel et très drôle, comme un vrai humoriste qui raconte une "
            "situation. Il faut un CONTEXTE distinct par angle (soeur, ami, colocataire, "
            "famille, rendez-vous, restaurant, voyage, commande, etc.) et un ressort comique "
            "distinct. Interdiction des marqueurs A/B, du dialogue théâtral étiqueté et des "
            "structures recyclées. Le tweet peut être un mini-récit, une observation ou une "
            "réplique rapportée. 'I have a theory' ou 'What if' peut être utilisé ponctuellement, "
            "mais jamais plus de 2 fois sur les 10 angles. Chaque angle doit raconter une scène "
            "différente autour du clash culturel du New York bagel. JAMAIS d'affirmation de faits "
            "présentée comme vraie, de politique ou de controverse. Chaque angle = "
            "tweet.keywords_style (DICT à clés anglaises green/red : "
            "green = valeur/espoir, red = danger/absurde — chaque liste contient "
            "des MOTS SEULS présents mot à mot dans tweet.text, ponctuation "
            "ignorée, jamais de phrases multi-mots), 3) text_emotion (le "
            "texte motion au milieu, en anglais, 4 mots maximum, terminé par ':' : "
            "il doit identifier la réaction collective des deux personnes du contexte "
            "du tweet. Exemples : 'My sister and me right now:', 'The two neighbors right now:', "
            "'My roommate and me right now:', 'The professor and student right now:'. "
            "Ne jamais utiliser Doom, Students reading this ou un personnage absent du tweet. "
            "Le motion text doit changer quand le contexte narratif change. OBLIGATOIRE : "
            "chaque text_emotion se termine par ':', 4) duration_sec (entier "
            "5-30, défaut 8). Tout en ANGLAIS."
            " La video est montee par OMNIS_WATCH selon la doctrine 6 couches "
            "de GUIDE_UTILISATION/04_MODE_MEME.md (setup/faux post, preuve, "
            "label A->B, reacteur pop-culture, pivot 50-55%, watermark)."
        )
    elif sub_mode == "humour":
        mission = (
            "Mode HUMOUR : corrige la blague fournie (grammaire + langue cible, "
            "sans titre inventé), puis forge une variante pour CET angle (N blagues "
            "similaires, une par angle). Chaque blague doit tenir en moins de 30 "
            "secondes de lecture. Produis aussi les métadonnées de la video."
        )
    else:
        mission = (
            "Mode INFORMATIF : résume l'article de manière virale selon le registre "
            "de viralité du copywriting. Titre viral 6 mots max + paragraphe viral "
            "4 lignes max + métadonnées (description = 1 paragraphe résumé 2 lignes "
            "+ 1 paragraphe fair use) + tags + on-screen text."
        )

    humour_spin = context.get("humour_spin")
    if sub_mode in ("humour", "meme") and humour_spin:
        mission = (
            mission
            + f"\nSPIN HUMOUR (Warsmith) : {humour_spin} — chaque angle décline "
            "cette direction humoristique (ironie, absurde, jeux de mots) SANS "
            "quitter le sujet réel. Le titre, le tweet et le texte d'émotion "
            "portent le spin, jamais de moquerie diffamatoire."
        )

    if sub_mode in ("meme", "meme_v2"):
        output_schema = {
            "title": "titre en haut (max 6 mots, SI nécessaire) ou null",
            "tweet": {
                "text": "fake tweet du faux post (max 3 lignes)",
                "keywords_style": {
                    "green": ["mot seul du tweet"],
                    "red": ["mot seul du tweet"],
                },
            },
            "reaction_tweet": "réaction originale PERTURABO, distincte de la source, maximum 3 lignes",
            "text_emotion": "texte d'émotion du milieu (max 4 mots avant ':', contextualisé)",
            "emotion": "l'émotion de l'angle (ex: poignant, drole, choc, tendu)",
            "duration_sec": 5,
            "metadata": {
                "title": "titre metadata YouTube",
                "description": "paragraphe 1 : résumé du tweet en 2-3 lignes "
                               "(le post, le chiffre choc, la réaction). "
                               "N'AJOUTE PAS de note fair use ni d'avertissement "
                               "monétisation : ils sont injectés automatiquement.",
                "tags": ["tag1", "tag2"],
            },
        }
    else:
        output_schema = {
            "title": "titre viral (6 mots max)",
            "viral_paragraph": "paragraphe viral (4 lignes max)",
            "metadata": {
                "title": "titre metadata",
                "description": "résumé 2 lignes + paragraphe fair use",
                "tags": ["tag1", "tag2"],
            },
            "on_screen_text": "texte court ou null",
        }

    user_prompt = {
        "mission": mission,
        "campaign_id": context.get("campaign_id"),
        "angle_id": args.angle,
        "sub_mode": sub_mode,
        "angle": context.get("angle"),
        "clip_source_ref": context.get("clip_source_ref"),
        "article_source": context.get("article_source"),
        "joke_source": context.get("joke_source"),
        "humour_spin": context.get("humour_spin"),
        "reference_clip_style": context.get("reference_clip_style"),
        "platform_target": platform,
        "market_target": market,
        "archivum": context.get("archivum"),
        "output_schema": output_schema,
        "heresies_interdites": _meme_heresies(sub_mode),
    }

    if sub_mode == "meme_v2":
        user_prompt["source_post"] = context.get("meme_v2_source")
        user_prompt["angle_brief"] = (context.get("angle") or {}).get("angle_brief")
        user_prompt["required_duration_sec"] = 5
        user_prompt["montage_guide_ref"] = "GUIDE_UTILISATION/04_MODE_MEME.md"
    elif sub_mode == "meme":
        user_prompt["keyword"] = context.get("keyword")
        user_prompt["meme_source"] = context.get("meme_source")
        user_prompt["montage_guide_ref"] = (
            "GUIDE_UTILISATION/04_MODE_MEME.md")

    client = PremiumClient(_FORGE_ROOT)
    if getattr(args, "dry_run", False):
        call = {
            "mode": "dry-run — aucun appel réseau",
            "model_id": client.config.get("model_id", "<model_premium_id>"),
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
        }
        out = os.path.join(IN_DIR, f"premium_call_{args.angle}.json")
        save_json(out, call)
        print(f"[F04:LOGO] Phase B (dry-run) : {out}")
        print("[F04:LOGO] Aucun appel premium — vérifier le prompt, puis --generate")
        return

    if not client._api_key():
        # ---- MODE BACKUP ORACLE : pas de clé premium → l'Oracle forge -------
        if getattr(args, "oracle", False):
            call = {
                "mode": "oracle — backup sans clé premium",
                "model_id": client.config.get("model_id", "<model_premium_id>"),
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
            }
            out = os.path.join(IN_DIR, f"premium_call_{args.angle}.json")
            save_json(out, call)
            raw_path = os.path.join(OUT_DIR, f"text_payload_raw_{args.angle}.json")
            if os.path.exists(raw_path):
                print(f"[F04:LOGO] MODE ORACLE : raw déjà forgé par l'Oracle "
                      f"({os.path.basename(raw_path)}) — lancer --ordonnance --auto-ord")
                return
            print(f"[F04:LOGO] MODE ORACLE : prompt écrit dans {out}")
            print("[F04:LOGO] L'Oracle doit forger : "
                  f"OUT/text_payload_raw_{args.angle}.json (schéma output_schema)")
            print("[F04:LOGO] Puis relancer --generate --oracle (détecte le raw) ou --ordonnance")
            sys.exit(1)
        print("[F04:LOGO] Clé premium absente — 2 options :")
        print("  1) Définir la clé (API Keys) : env CLIPPING_PREMIUM_API_KEY")
        print("  2) Mode backup : --generate --oracle (l'Oracle forge le texte)")
        sys.exit(1)

    client.require_config()
    result = client.chat(system_prompt=system_prompt,
                         user_prompt=json.dumps(user_prompt, indent=2,
                                                ensure_ascii=False))
    if not result:
        print("[F04:LOGO] Échec de la génération premium")
        sys.exit(1)
    try:
        raw = json.loads(client.extract_json(result))
    except (json.JSONDecodeError, ValueError) as e:
        print(f"[F04:LOGO] Sortie premium non-JSON: {e}")
        sys.exit(1)
    raw["campaign_id"] = context.get("campaign_id")
    raw["angle_id"] = args.angle
    save_json(os.path.join(OUT_DIR, f"text_payload_raw_{args.angle}.json"), raw)
    print(f"[F04:LOGO] Phase B : OUT/text_payload_raw_{args.angle}.json")
    print("[F04:LOGO] Lancer --ordonnance --auto-ord pour la Phase C")


def cmd_ordonnance_logo(args):
    angle = find_angle(args.angle)
    raw = _load_raw(args.angle)
    context = _load_context(args.angle)
    sub_mode = context.get("sub_mode", "informatif")
    platform = context.get("platform_target", "youtube")
    market = context.get("market_target", "unknown")

    payload, notes = _ordonnance_logo(
        raw, angle, sub_mode, platform, market,
        campaign_id=context.get("campaign_id"))
    save_json(os.path.join(OUT_DIR, f"text_payload_{args.angle}.json"), payload)
    print(f"[F04:LOGO] Phase C (auto) : OUT/text_payload_{args.angle}.json")
    for note in notes:
        print(f"  - {note}")


def cmd_finalize_logo(args):
    angle = find_angle(args.angle)
    path = os.path.join(OUT_DIR, f"text_payload_{args.angle}.json")
    if not os.path.exists(path):
        print(f"[F04:LOGO] text_payload introuvable: {path}")
        print("[F04:LOGO] Lancer --ordonnance d'abord (Phase C)")
        sys.exit(1)

    payload = load_json(path)
    title_words = len(str(payload.get("title", "")).split())
    if title_words > LOGO_MAX_TITLE_WORDS:
        print(f"[F04:LOGO] HÉRÉSIE {args.angle} : titre {title_words} mots "
              f"> {LOGO_MAX_TITLE_WORDS}")
        sys.exit(1)
    payload["check_in_iw_custos"] = now_iso()
    save_json(path, payload)

    md = _render_logo_md(payload)
    md_path = os.path.join(OUT_DIR, f"text_payload_{args.angle}.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md)
    print(f"[F04:LOGO] Phase D : {md_path} (lisible opérateur)")

    angles = load_angles()
    all_done = all(
        os.path.exists(os.path.join(OUT_DIR, f"text_payload_{a.get('angle_id')}.json"))
        for a in angles
    )
    if all_done:
        custos = os.path.join(_FORGE_ROOT, "IW_CUSTOS.py")
        if os.path.exists(custos):
            subprocess.run(
                [sys.executable, custos, "--mode", "check-in",
                 "--frigate", "F04", "--output", md_path],
                capture_output=True, text=True, timeout=30)
        print("[F04:LOGO] Check-in IW_CUSTOS — text_payloads_forged")
    print("[F04:LOGO] OUT prêt pour F05_PACKAGER (pack logo v2)")


def main():
    parser = argparse.ArgumentParser(description="F04_COPYWRITER — La Plume de la Forteresse")
    parser.add_argument("--init-systemprompt", action="store_true",
                        help="Init one-time : premium génère copywriter_systemprompt.md")
    parser.add_argument("--setup-context", action="store_true",
                        help="Phase A : rassemble l'ARCHIVUM dans IN/copywriter_context")
    parser.add_argument("--generate", action="store_true",
                        help="Phase B : génération premium directe")
    parser.add_argument("--ordonnance", action="store_true",
                        help="Phase C : prompt IRON (ou --auto-ord local)")
    parser.add_argument("--finalize", action="store_true",
                        help="Phase D : validation + .md + check-in IW_CUSTOS")
    parser.add_argument("--angle", default=None, help="angle_id (ex: A01)")
    parser.add_argument("--platform", default=None, help="Plateforme cible (override)")
    parser.add_argument("--market", default=None, help="Marché cible (override)")
    parser.add_argument("--auto-ord", action="store_true",
                        help="Phase C locale (sans IRON) : classement + compliance")
    parser.add_argument("--dry-run", action="store_true",
                        help="Phase B sans appel réseau (écrit IN/premium_call)")
    parser.add_argument("--oracle", action="store_true",
                        help="MODE BACKUP : sans clé premium, l'Oracle forge OUT/text_payload_raw_<angle>.json "
                             "à partir du prompt IN/premium_call_<angle>.json (au lieu de planter)")
    parser.add_argument("--force", action="store_true",
                        help="Init system prompt malgré un fichier déjà figé / placeholder")
    parser.add_argument("--sub-mode", default=None,
                        help="Mode LOGO: informatif | humour | meme (auto-détecté sinon)")
    args = parser.parse_args()

    try:
        if args.init_systemprompt:
            cmd_init_systemprompt(args)
        elif args.setup_context:
            if not args.angle:
                print("[F04] --angle requis pour --setup-context"); sys.exit(1)
            (cmd_setup_context_logo if is_logo() else cmd_setup_context)(args)
        elif args.generate:
            if not args.angle:
                print("[F04] --angle requis pour --generate"); sys.exit(1)
            (cmd_generate_logo if is_logo() else cmd_generate)(args)
        elif args.ordonnance:
            if not args.angle:
                print("[F04] --angle requis pour --ordonnance"); sys.exit(1)
            (cmd_ordonnance_logo if is_logo() else cmd_ordonnance)(args)
        elif args.finalize:
            if not args.angle:
                print("[F04] --angle requis pour --finalize"); sys.exit(1)
            (cmd_finalize_logo if is_logo() else cmd_finalize)(args)
        else:
            parser.print_help()
    except PremiumClientError as e:
        print(f"[F04] ERREUR premium : {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
