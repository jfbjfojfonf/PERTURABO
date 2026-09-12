"""
packager.py — F05_PACKAGER : Le Ferrier de la Porte 4 (forge CLIPPING)
======================================================================

Frégate d'assemblage final (Porte 4). Fusion purement déterministe des
artefacts F01 → F04 en N `production_pack.json` (un pack = 1 vidéo pour
1 plateforme pour 1 marché — N angles = N packs).

F05 ne fait PAS appel à l'IRON : c'est un enchaînement mécanique de
fusion de JSONs. Pas de prompt, pas de sandbox.

   --assemble : pour chaque angle, assemble le pack (9 blocs + checklist)
   --finalize : validation schéma canonique + packs_index.json +
                packager_summary.md + check-in IW_CUSTOS (F05 -> packs_assembled)

Hérésies gardées :
  - asset non-F03 dans SOURCE (strict-source, règle C1)
  - source_permission != "campaign_provided"
  - text_payload absent ou non-F04 (structure requise)
  - pack non conforme au schéma canonique CONTRACTS/production_pack_schema.json

Usage:
  python packager.py --assemble [--angles ../F02_TYRANT_CAMP/OUT/angles.json]
  python packager.py --finalize
"""

import argparse
import glob
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_F05_DIR = os.path.dirname(_SCRIPT_DIR)
_FORGE_ROOT = os.path.dirname(_F05_DIR)

sys.path.insert(0, os.path.join(_SCRIPT_DIR, "libs"))
from schema_validator import SchemaValidator
from reference_style_extractor import ReferenceStyleExtractor

# Profil actif (whop | logo) — lu depuis liber_clipping.json
sys.path.insert(0, os.path.join(_FORGE_ROOT, "SHARED"))
from profile_loader import load_profile

OUT_DIR = os.path.join(_F05_DIR, "OUT")
IN_DIR = os.path.join(_F05_DIR, "IN")
CONTRACTS_DIR = os.path.join(_FORGE_ROOT, "CONTRACTS")
ARCHIVUM_DIR = os.path.join(_FORGE_ROOT, "ARCHIVUM")
F01_OUT = os.path.join(_FORGE_ROOT, "F01_SCOUT", "OUT")
F02_OUT = os.path.join(_FORGE_ROOT, "F02_TYRANT_CAMP", "OUT")
F03_OUT = os.path.join(_FORGE_ROOT, "F03_SOURCE_HUNTER", "OUT")
F04_OUT = os.path.join(_FORGE_ROOT, "F04_COPYWRITER", "OUT")
LIBER_PATH = os.path.join(_FORGE_ROOT, "liber_clipping.json")
SCHEMA_PATH = os.path.join(CONTRACTS_DIR, "production_pack_schema.json")

ANGLES_CANDIDATES = [
    os.path.join(F02_OUT, "angles.json"),
    os.path.join(_FORGE_ROOT, "ANGLESMITH", "OUT", "angles.json"),
]

DURATION_DEFAULTS = {"youtube": (15, 45), "tiktok": (15, 30), "instagram": (15, 30)}
DURATION_RE = re.compile(r"clip_(min|max)_duration\D*(\d+)")

FORBIDDEN_DEFAULTS = ["silences > 3s", "CTA abonne-toi", "fadeouts"]

# --- Bloc LOGO v2 (profil logo) -------------------------------------------
LOGO_LOGO_PLACEMENT = (
    "Logo fourni par la campagne (image transparente). OMNIS_WATCH applique "
    "l'image transparente contenant le logo — placement campagne 1080x1920, "
    "ne pas déplacer, ne pas redimensionner, ne pas recolorer."
)
FAIR_USE_NOTE = (
    "The videos and images used in this creation serve only as illustration "
    "(fair use). They are neither claimed nor monetized beyond the permitted "
    "clip format."
)


def resolve_schema_path() -> str:
    """Schéma du pack selon le profil actif (whop par défaut)."""
    prof = load_profile()
    if prof.mode == "logo":
        return prof.resolve("pack_schema")
    return SCHEMA_PATH


def _load_latest_meme_scan() -> dict:
    """Charge le scan viralité F00 le plus récent (mode meme)."""
    f00_out = os.path.join(_FORGE_ROOT, "F00_CAPTEURS", "OUT")
    candidates = sorted(
        f for f in os.listdir(f00_out)
        if f.startswith("meme_virality_") and f.endswith(".json")
    ) if os.path.isdir(f00_out) else []
    if not candidates:
        return {}
    try:
        return load_json(os.path.join(f00_out, candidates[-1]))
    except Exception:
        return {}


def _load_campaign_keyword() -> str:
    """Le mot-clé du siège (mode meme) depuis ARCHIVUM/campaign/keyword.txt."""
    path = os.path.join(ARCHIVUM_DIR, "campaign", "keyword.txt")
    if not os.path.exists(path):
        return ""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return ""


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


def _channel_base_paragraph() -> str:
    """Paragraphe de base du compte (description_base_paragraph.md dans
    ARCHIVUM/channels/<slug>/) : avertissement non-monétisation + note fair
    use. Slug lu depuis ARCHIVUM/campaign/channel.txt. Retour '' si absent."""
    slug_path = os.path.join(ARCHIVUM_DIR, "campaign", "channel.txt")
    if not os.path.exists(slug_path):
        return ""
    try:
        with open(slug_path, "r", encoding="utf-8") as f:
            slug = f.read().strip()
    except OSError:
        return ""
    if not slug:
        return ""
    para_path = os.path.join(ARCHIVUM_DIR, "channels", slug,
                             "description_base_paragraph.md")
    if not os.path.exists(para_path):
        return ""
    try:
        with open(para_path, "r", encoding="utf-8") as f:
            content = f.read()
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


def _channel_handle() -> str:
    """Handle @ du compte (identity.json dans ARCHIVUM/channels/<slug>/).
    Slug lu depuis ARCHIVUM/campaign/channel.txt. Retour '' si absent."""
    slug_path = os.path.join(ARCHIVUM_DIR, "campaign", "channel.txt")
    if not os.path.exists(slug_path):
        return ""
    try:
        with open(slug_path, "r", encoding="utf-8") as f:
            slug = f.read().strip()
    except OSError:
        return ""
    if not slug:
        return ""
    ident_path = os.path.join(ARCHIVUM_DIR, "channels", slug, "identity.json")
    if not os.path.exists(ident_path):
        return ""
    try:
        with open(ident_path, "r", encoding="utf-8") as f:
            ident = json.load(f)
    except (OSError, ValueError):
        return ""
    return str(ident.get("handle") or "").strip()


def _load_campaign_file(name: str) -> dict:
    path = os.path.join(ARCHIVUM_DIR, "campaign", name)
    if os.path.exists(path):
        try:
            return load_json(path)
        except Exception:
            return {}
    return {}


def _clip_source_ref() -> dict:
    ref = _load_campaign_file("reference_clip.json")
    f01 = {}
    try:
        f01 = load_f01_specimen()
    except SystemExit:
        pass
    selected = f01.get("asset_selected", {}) or {}
    url = ref.get("url") or ref.get("reference") or selected.get("url") or ""
    return {
        "source_type": ref.get("source_type", "youtube"),
        "reference": url,
        "celebrity_or_subject": ref.get("celebrity_or_subject"),
        "niche": ref.get("niche"),
        "duration_sec": selected.get("duration_sec"),
        "timecodes": None,
    }


def _resolve_cuts(sub_mode: str, angle_id: str, cuts: dict) -> dict:
    entries = (cuts.get("cuts") if cuts else None) or []
    entry = next((c for c in entries if c.get("angle_id") == angle_id), None)
    if entry is None and len(entries) == 1:
        entry = entries[0]
    if entry is None:
        return {
            "start_sec": None, "end_sec": None, "duration_sec": None,
            "cut_source": ("operator" if sub_mode == "humour"
                            else "perturabo_proposed"),
            "note": ("cuts à fournir par le Warsmith (mode humour)" if sub_mode == "humour"
                      else "cuts proposés par PERTURABO — validation Warsmith requise"),
        }
    start = entry.get("start_sec")
    end = entry.get("end_sec")
    duration = entry.get("duration_sec")
    if duration is None and start is not None and end is not None:
        duration = round(float(end) - float(start), 1)
    cut_source = entry.get("cut_source") or (
        "operator" if sub_mode == "humour" else "perturabo_validated")
    return {
        "start_sec": start,
        "end_sec": end,
        "duration_sec": duration,
        "cut_source": cut_source,
        "note": entry.get("note"),
    }


def _load_meme_v2_config() -> dict:
    """Charge les inputs opérateur MEME V2 sans jamais inventer source, tag ou chaîne."""
    path = os.path.join(ARCHIVUM_DIR, "campaign", "meme_v2.json")
    if not os.path.exists(path):
        return {}
    try:
        return load_json(path)
    except (OSError, ValueError):
        return {}


def _logo_video_asset(angle: dict, payload: dict, sub_mode: str,
                      cuts: dict, video_index: int, meme: str = None,
                      meme_v2: dict = None) -> dict:
    angle_id = angle.get("angle_id")
    payload = payload or {}
    title = payload.get("title") or angle.get("title")
    viral_paragraph = (payload.get("viral_paragraph")
                       or payload.get("body") or angle.get("body") or "")
    metadata = payload.get("metadata") or {}
    if sub_mode == "meme" and not title:
        title = metadata.get("title") or (payload.get("tweet") or {}).get("text") or ""
    if not metadata:
        description = viral_paragraph or ""
        if description:
            description = f"{description}\n\n{FAIR_USE_NOTE}"
        else:
            description = FAIR_USE_NOTE
        base_para = _channel_base_paragraph()
        if base_para and "not monetized" not in description.lower() \
                and "not monetised" not in description.lower():
            description = f"{description}\n\n{base_para}".strip()
        metadata = {
            "title": title or "",
            "description": description,
            "tags": _normalize_tags(payload.get("tags")
                                    or angle.get("seo_tags") or []),
        }
    metadata["tags"] = _normalize_tags(metadata.get("tags") or [])
    if metadata["tags"]:
        hashtag_line = ", ".join(metadata["tags"])
        if hashtag_line.lower() not in metadata["description"].lower():
            metadata["description"] = f"{metadata['description']}\n\n{hashtag_line}".strip()
    asset = {
        "video_index": video_index,
        "angle_id": angle_id,
        "title": title or "",
    }
    if sub_mode in ("meme", "meme_v2"):
        # Contrat LACRIMAE : le pack meme porte les champs qu'OMNIS_WATCH
        # consomme. metadata (description) est exigé par le Warsmith pour
        # chaque vidéo : résumé du tweet + note fair use + avertissement.
        # cut/on_screen_text/logo_placement sont ignorés.
        tweet = payload.get("tweet") or {}
        asset["meme"] = meme or ""
        reaction_text = payload.get("reaction_tweet") or tweet.get("text")
        asset["tweet"] = {
            "text": reaction_text,
            "keywords_style": _keywords_v2(tweet.get("keywords_style"),
                                           reaction_text),
        }
        asset["reaction_tweet"] = reaction_text
        asset["text_emotion"] = payload.get("text_emotion")
        if sub_mode == "meme_v2":
            cfg = meme_v2 or {}
            source = cfg.get("source_post") or {}
            binding = (cfg.get("operator_bindings") or {}).get(angle_id) or {}
            asset["clip_id"] = binding.get("clip_id")
            asset["meme_tag"] = binding.get("meme_tag")
            asset["channel_id"] = binding.get("channel_id")
            asset["source_post"] = {
                "screenshot_png": source.get("screenshot_png"),
                "url": source.get("url"),
                "author": source.get("author"),
                "observed_at": source.get("observed_at"),
                "credit_display": source.get("credit_display"),
            }

        asset["emotion"] = (payload.get("emotion")
                            or angle.get("emotion")
                            or angle.get("emotion_mode"))
        asset["duration_sec"] = int(payload.get("duration_sec", 8))
        asset["watermark"] = _channel_handle() or "@memecocktail"
        asset["metadata"] = metadata
    else:
        asset["viral_paragraph"] = viral_paragraph
        asset["metadata"] = metadata
        asset["cut"] = _resolve_cuts(sub_mode, angle_id, cuts)
        asset["logo_placement"] = LOGO_LOGO_PLACEMENT
        asset["on_screen_text"] = (payload.get("on_screen_text")
                                   or angle.get("on_screen_text"))
    return asset


_ANGLE_KEEP = ["angle_id", "genre", "title", "body", "on_screen_text",
                "seo_tags", "reframe_type", "zone", "angle_family",
                "emotion_mode", "engagement_type", "reframe_dim"]
_ARTICLE_KEYS = ["reference", "subject", "celebrity_or_subject"]
_JOKE_KEYS = ["text", "meme_type", "reference"]
_STYLE_KEYS = ["source", "ratio", "blur", "editing_style", "rules", "ref"]


def _sanitize_angle(angle: dict) -> dict:
    """Ne garde que les clés déclarées dans le schéma angles[] (les angles
    ANGLESMITH réels portent des champs supplémentaires non-schéma)."""
    return {k: angle.get(k) for k in _ANGLE_KEEP if k in angle}


def _pick(data: dict, keys: list) -> dict:
    """Ne garde que les clés déclarées dans le schéma (inputs campagne
    portent des champs méta _mode/_description à ne pas embarquer)."""
    return {k: data.get(k) for k in keys if k in data}


def _keywords_v2(kws_style, tweet_text: str = "") -> dict:
    """Conforme à la note LACRIMAE (05_NOTE_PERTURABO_PACK_MEME.md section 4) :
    keywords_style = DICT {"green": [...], "red": [...]}, mots seuls présents
    mot à mot dans tweet.text. Une liste [{word,color}] (v1) -> aucune couleur."""
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
                continue
            token = next(iter(word_tokens))
            if token not in tokens or token in seen:
                continue
            seen.add(token)
            result[key].append(word)
    return result


def _tweet_tokens(text: str) -> set:
    import re
    return set(re.findall(r"[a-z0-9]+", (text or "").lower()))


def _meme_v2_export_block(config: dict) -> dict:
    """Ne transmet que la capture et la provenance utile à LACRIMAE.
    Le texte copié reste interne à F01/PERTURABO."""
    source = config.get("source_post") or {}
    return {
        "source_post": {
            "screenshot_png": source.get("screenshot_png"),
            "url": source.get("url"),
            "author": source.get("author"),
            "observed_at": source.get("observed_at"),
            "metrics": source.get("metrics"),
            "credit_display": source.get("credit_display"),
        },
        "operator_bindings": config.get("operator_bindings") or {},
    }


def _meme_for_angle(angle_id: str, meme_v2: dict = None) -> str:
    """Balise du clip : en MEME V2 elle vient du binding opérateur."""
    binding = ((meme_v2 or {}).get("operator_bindings") or {}).get(angle_id) or {}
    return str(binding.get("meme_tag") or "M1")


def assemble_logo_pack(angles: list[dict], sub_mode: str, campaign: dict,
                       verdict: dict, siege_id: str = None) -> dict:
    """Assemble le pack LOGO v2 : N videos (une par angle) + sources + style."""
    cuts = campaign.get("cuts") or {}
    article = _pick(campaign.get("article_source") or {}, _ARTICLE_KEYS)
    joke = _pick(campaign.get("joke_source") or {}, _JOKE_KEYS)
    style = _pick(campaign.get("reference_clip_style") or {}, _STYLE_KEYS)
    f01_payloads = {}
    for angle in angles:
        angle_id = angle.get("angle_id")
        p = os.path.join(F04_OUT, f"text_payload_{angle_id}.json")
        # En mode meme, F04 produit d’abord text_payload_raw_Axx.json.
        # F05 peut l’assembler directement après validation de la Gate F04.
        if not os.path.exists(p):
            raw_p = os.path.join(F04_OUT, f"text_payload_raw_{angle_id}.json")
            if os.path.exists(raw_p):
                p = raw_p
        if os.path.exists(p):
            try:
                f01_payloads[angle_id] = load_json(p)
            except Exception:
                f01_payloads[angle_id] = {}

    meme_v2_config = campaign.get("meme_v2") or {}
    videos = [
        _logo_video_asset(angle, f01_payloads.get(angle.get("angle_id")),
                          sub_mode, cuts, idx,
                          meme=_meme_for_angle(angle.get("angle_id"), meme_v2_config),
                          meme_v2=meme_v2_config)
        for idx, angle in enumerate(angles, start=1)
    ]
    campaign_id = verdict.get("campaign_id") or (angles[0].get("campaign_id") if angles else None)
    pack_id = f"LOGO-{campaign_id or 'SIEGE'}-{siege_id or 'X'}"

    pack = {
        "pack_id": pack_id,
        "siege_id": siege_id or "",
        "mode": "logo",
        "sub_mode": sub_mode,
        "clip_source_ref": _clip_source_ref(),
        "article_source": article or None if sub_mode == "informatif" else None,
        "joke_source": joke or None if sub_mode == "humour" else None,
        "reference_clip_style": style or None,
        "angles": [_sanitize_angle(a) for a in angles],
        "videos": videos,
        "checklist": {
            "factual_verified": False,
            "no_defamation": False,
            "no_fabricated_breaking": False,
            "seo_optimized": True,
        },
    }
    if sub_mode == "meme_v2":
        pack["meme_v2"] = _meme_v2_export_block(campaign.get("meme_v2") or {})
        pack["clip_source_ref"]["source_type"] = "meme_v2_social"
        pack["clip_source_ref"]["reference"] = "manual_social_source"
    if sub_mode == "meme":
        scan = campaign.get("meme_source") or _load_latest_meme_scan()
        pack["meme_source"] = {
            "keyword": (campaign.get("keyword")
                        or (scan or {}).get("keyword")
                        or angles[0].get("keyword")),
            "virality_scan": {
                "sources_scanned": (scan or {}).get("sources_scanned", []),
                "signals": (scan or {}).get("signals", {}),
                "evidence_urls": (scan or {}).get("evidence_urls", []),
                "scanned_at": (scan or {}).get("scanned_at"),
            } if scan else None,
            "montage_guide_ref": "GUIDE_UTILISATION/04_MODE_MEME.md",
        }
    return pack


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def save_json(path: str, data: dict):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ----------------------------------------------------------------------
# Résolution des entrées
# ----------------------------------------------------------------------
def find_angles_path(args) -> str:
    if getattr(args, "angles", None):
        return args.angles
    for candidate in ANGLES_CANDIDATES:
        if os.path.exists(candidate):
            return candidate
    print("[F05] angles.json introuvable (F02_TYRANT_CAMP/OUT ou ANGLESMITH/OUT)")
    sys.exit(1)


def angles_from_file(path: str) -> list[dict]:
    data = load_json(path)
    angles = data.get("angles", [])
    if not angles:
        print(f"[F05] angles.json vide: {path}")
        sys.exit(1)
    return angles


def find_verdict() -> dict:
    for path in (os.path.join(ARCHIVUM_DIR, "campaign", "verdict.json"),
                 os.path.join(F02_OUT, "campaign_verdict.json")):
        if os.path.exists(path):
            return load_json(path)
    print("[F05] campaign_verdict.json introuvable — verdict vide")
    return {}


def load_f01_specimen() -> dict:
    path = os.path.join(F01_OUT, "source_specimen.json")
    if not os.path.exists(path):
        print(f"[F05] F01 specimen introuvable: {path}")
        sys.exit(1)
    return load_json(path)


def warsmith_targets(args, verdict: dict) -> tuple[str, str]:
    platform = getattr(args, "platform", None)
    market = getattr(args, "market", None)
    if not platform or not market:
        if os.path.exists(LIBER_PATH):
            inputs = load_json(LIBER_PATH).get("inputs_warsmith", {})
            platform = platform or inputs.get("platform_target")
            market = market or inputs.get("market_target")
    platform = platform or verdict.get("platform_target") or "youtube"
    market = market or verdict.get("market_target") or "unknown"
    return platform, market


# ----------------------------------------------------------------------
# Fourchette de durée (alignée sur F03 duration_guard)
# ----------------------------------------------------------------------
def platform_bounds(platform: str) -> tuple[int, int]:
    profile = os.path.join(ARCHIVUM_DIR, "platform_generator", f"{platform}_profile.md")
    lo, hi = DURATION_DEFAULTS.get(platform, DURATION_DEFAULTS["youtube"])
    if os.path.exists(profile):
        try:
            with open(profile, "r", encoding="utf-8") as f:
                text = f.read()
            values = dict(DURATION_RE.findall(text))
            if "min" in values:
                lo = int(values["min"])
            if "max" in values:
                hi = int(values["max"])
        except (OSError, ValueError):
            pass
    return lo, hi


# ----------------------------------------------------------------------
# Blocs du pack
# ----------------------------------------------------------------------
def _source_block(specimen: dict, assets: list[dict], angle_id: str) -> dict:
    selected = specimen.get("asset_selected", {})
    url = selected.get("url")
    asset_urls = [a.get("url") for a in assets]
    if not url:
        print(f"[F05] HERESIE {angle_id}: asset_selected.url manquant")
        sys.exit(1)
    if url not in asset_urls:
        print(f"[F05] HERESIE {angle_id}: asset {url} hors des assets F01 (règle C1)")
        sys.exit(1)

    segments = []
    for seg in specimen.get("suggested_segments", []) or []:
        entry = {
            "start_sec": seg.get("start_sec"),
            "end_sec": seg.get("end_sec"),
            "rationale": seg.get("rationale", ""),
        }
        if seg.get("duration_sec") is not None:
            entry["duration_sec"] = seg.get("duration_sec")
        if seg.get("extracted_text_snippet"):
            entry["extracted_text_snippet"] = seg.get("extracted_text_snippet")
        segments.append(entry)

    source_segment = None
    if segments:
        source_segment = {
            "start_sec": segments[0]["start_sec"],
            "end_sec": segments[0]["end_sec"],
        }

    return {
        "video_url": url,
        "suggested_segments": segments,
        "source_segment_sec": source_segment,
        "source_permission": "campaign_provided",
    }


def _angle_block(angle: dict, angles: list[dict], text_payload: dict) -> dict:
    axes = ["angle_family", "emotion_mode", "engagement_type", "reframe_dim"]

    def differs(ax: str) -> bool:
        return any(angle.get(ax) != other.get(ax) for other in angles
                   if other.get("angle_id") != angle.get("angle_id"))

    differentiated_axes = [ax for ax in axes if differs(ax)]
    if len(differentiated_axes) < 2:
        differentiated_axes = axes[:2]

    hook_types = []
    for t in (text_payload.get("titles", []) or [])[:3]:
        hook = t.get("hook_type")
        if hook and hook not in hook_types:
            hook_types.append(hook)

    is_blue = angle.get("zone") == "blue_ocean"
    blue_ocean = {"is_blue_ocean": is_blue}
    if is_blue:
        blue_ocean.update({
            "blue_ocean_depth": 1,
            "territory": angle.get("territory"),
            "rationale": angle.get("territory_rationale"),
        })
    return {
        "angle_family": angle.get("angle_family"),
        "emotion_mode": angle.get("emotion_mode"),
        "engagement_type": angle.get("engagement_type"),
        "reframe_dim": angle.get("reframe_dim"),
        "hook_style_fit": hook_types,
        "loop_tech": "open_loop" if angle.get("engagement_type") == "cliffhanger"
                     else "closed_loop",
        "anti_cannibal_diff": {"differentiated_axes": differentiated_axes},
        "blue_ocean": blue_ocean,
    }


def _cut_block(specimen: dict, platform: str) -> dict:
    lo, hi = platform_bounds(platform)
    segments = specimen.get("suggested_segments", []) or []
    moments_to_chase = []
    for i, seg in enumerate(segments, start=1):
        snippet = seg.get("extracted_text_snippet") or seg.get("rationale") or ""
        moments_to_chase.append(
            f"segment {i} (t={seg.get('start_sec')}-{seg.get('end_sec')}s): {snippet}")
    if not moments_to_chase:
        moments_to_chase = ["moments à confirmer par D-F02 (pas de segments F03)"]
    return {
        "clip_max_duration": hi,
        "clip_min_duration": lo,
        "moments_to_chase": moments_to_chase,
        "moments_to_avoid": ["intro trop longue > 3s avant le hook"],
        "forbidden": list(FORBIDDEN_DEFAULTS),
    }


def _text_payload_block(payload: dict, angle_id: str) -> dict:
    required = ["titles", "paragraph", "caption", "hashtags", "on_screen_text", "cta_text"]
    for key in required:
        if key not in payload:
            print(f"[F05] HERESIE {angle_id}: text_payload sans '{key}' — "
                  f"F05 ne forge rien, il assemble (sortie F04 requise)")
            sys.exit(1)
    titles = []
    for t in (payload.get("titles") or [])[:3]:
        titles.append({
            "rank": t.get("rank"),
            "text": t.get("text"),
            "platform_fit": t.get("platform_fit"),
            "market_fit": t.get("market_fit"),
            "hook_type": t.get("hook_type"),
            "rationale": t.get("rationale", ""),
        })
    return {
        "titles": titles,
        "paragraph": payload.get("paragraph"),
        "caption": payload.get("caption"),
        "hashtags": payload.get("hashtags"),
        "on_screen_text": payload.get("on_screen_text"),
        "cta_text": payload.get("cta_text"),
    }


def _checklist(platform: str) -> dict:
    return {
        "items": [
            {"id": "post_on_platform", "label": f"Poster sur {platform}", "status": "pending"},
            {"id": "submit_whop_under_1h", "label": "Soumettre Whop dans l'heure",
             "deadline_min": 60, "status": "pending"},
            {"id": "log_link_c06", "label": "Logger le lien dans F06_TRACKER",
             "status": "pending"},
            {"id": "view_check_1h", "label": "Relever vues à 1h", "status": "pending"},
            {"id": "view_check_24h", "label": "Relever vues à 24h", "status": "pending"},
            {"id": "payout_flag_low", "label": "Flag si payout < seuil", "status": "pending"},
            {"id": "feedback_learnings", "label": "Nourrir learnings.json", "status": "pending"},
        ]
    }


def _metadata_block(payload: dict) -> dict:
    rank1 = (payload.get("titles") or [{}])[0]
    title = rank1.get("text", "")
    caption = payload.get("caption", "")
    hashtags = " ".join(payload.get("hashtags", []) or [])
    return {
        "title_pattern": title,
        "description_skeleton": f"{caption}\n\n{hashtags}".strip(),
    }


def assemble_pack(angle: dict, angles: list[dict], specimen: dict, payload: dict,
                  f01_specimen: dict, verdict: dict, platform: str, market: str,
                  pack_index: int, pack_total: int) -> dict:
    extractor = ReferenceStyleExtractor(ARCHIVUM_DIR, IN_DIR)
    style = extractor.extract()

    return {
        "identite": {
            "campaign_id": verdict.get("campaign_id") or payload.get("campaign_id"),
            "angle_id": angle.get("angle_id"),
            "pack_index": pack_index,
            "pack_total": pack_total,
        },
        "cibles": {
            "target_platform": platform,
            "target_market": market,
        },
        "source": _source_block(specimen, f01_specimen.get("assets", []),
                                angle.get("angle_id")),
        "angle": _angle_block(angle, angles, payload),
        "cut_directives": _cut_block(specimen, platform),
        "reference_style": style,
        "text_payload": _text_payload_block(payload, angle.get("angle_id")),
        "compliance": {
            "disclosure": "#ad",
            "submit_deadline_min": 60,
            "source_permission": "campaign_provided",
        },
        "metadata": _metadata_block(payload),
        "submission_checklist": _checklist(platform),
    }


# ----------------------------------------------------------------------
# Commandes
# ----------------------------------------------------------------------
def cmd_assemble_logo(args):
    """Assemblage LOGO v2 : 1 pack, N videos (une par angle)."""
    angles = angles_from_file(find_angles_path(args))
    sub_mode = (args.sub_mode or "informatif").lower()
    if sub_mode not in ("informatif", "humour", "meme", "meme_v2"):
        print(f"[F05:LOGO] sub_mode inconnu: {sub_mode} "
              f"(attendu: informatif|humour|meme|meme_v2)")
        sys.exit(1)
    verdict = find_verdict()
    campaign = {
        "article_source": _load_campaign_file("article_source.json"),
        "joke_source": _load_campaign_file("joke_source.json"),
        "cuts": _load_campaign_file("cuts.json"),
        "reference_clip_style": _load_campaign_file("reference_clip_style.json"),
        "keyword": _load_campaign_keyword(),
        "meme_source": _load_latest_meme_scan() if sub_mode == "meme" else {},
        "meme_v2": _load_meme_v2_config() if sub_mode == "meme_v2" else {},
    }
    siege_id = None
    if os.path.exists(LIBER_PATH):
        siege_id = load_json(LIBER_PATH).get("siege_id")
    pack = assemble_logo_pack(angles, sub_mode, campaign, verdict, siege_id)
    out = os.path.join(OUT_DIR, "production_pack_logo.json")
    save_json(out, pack)
    n = len(pack.get("videos", []))
    print(f"[F05:LOGO] Pack logo ({sub_mode}) : {n} videos, {len(angles)} angles "
          f"-> {os.path.basename(out)}")
    if sub_mode == "meme":
        ref = (pack.get("meme_source") or {}).get("montage_guide_ref")
        print(f"[F05:LOGO] meme: montage_guide_ref={ref} — "
              f"OMNIS_WATCH charge le guide pour le rendu")
    print("[F05] Lancer --finalize pour valider (schéma logo) + expédier")


def cmd_assemble(args):
    if load_profile().mode == "logo":
        cmd_assemble_logo(args)
        return
    angles = angles_from_file(find_angles_path(args))
    verdict = find_verdict()
    f01 = load_f01_specimen()
    platform, market = warsmith_targets(args, verdict)
    total = len(angles)

    for idx, angle in enumerate(angles, start=1):
        angle_id = angle.get("angle_id")
        specimen_path = os.path.join(F03_OUT, f"source_specimen_{angle_id}.json")
        payload_path = os.path.join(F04_OUT, f"text_payload_{angle_id}.json")
        if not os.path.exists(specimen_path):
            print(f"[F05] Specimen F03 introuvable: {specimen_path} — angle {angle_id} sauté")
            continue
        if not os.path.exists(payload_path):
            print(f"[F05] Payload F04 introuvable: {payload_path} — angle {angle_id} sauté")
            continue

        pack = assemble_pack(
            angle, angles,
            load_json(specimen_path), load_json(payload_path),
            f01, verdict, platform, market, idx, total,
        )
        out = os.path.join(OUT_DIR, f"production_pack_{angle_id}.json")
        save_json(out, pack)
        print(f"[F05] Pack {idx}/{total}: {angle_id} -> {os.path.basename(out)}")

    print("[F05] Lancer --finalize pour valider + expédier")


def _collect_packs() -> list[tuple[str, dict]]:
    paths = sorted(glob.glob(os.path.join(OUT_DIR, "production_pack_*.json")))
    if not paths:
        print("[F05] OUT/production_pack_*.json absent — lancer --assemble d'abord")
        sys.exit(1)
    return [(p, load_json(p)) for p in paths]


def cmd_finalize_logo(args):
    """Finalise le pack LOGO : validation schéma logo + index + summary + check-in."""
    packs = _collect_packs()
    validator = SchemaValidator(resolve_schema_path())
    errors = []
    sub_mode = packs[0][1].get("sub_mode", "?")
    for path, pack in packs:
        errors += validator.validate(pack, root=os.path.basename(path))
        if pack.get("mode") != "logo":
            errors.append(f"{os.path.basename(path)}: mode != logo")
        if sub_mode == "meme_v2":
            cfg = pack.get("meme_v2") or {}
            source = cfg.get("source_post") or {}
            if not source.get("screenshot_png"):
                errors.append(f"{os.path.basename(path)}: MEME V2 source_post.screenshot_png manquant")
            bindings = cfg.get("operator_bindings") or {}
            for video in pack.get("videos", []):
                aid = video.get("angle_id")
                binding = bindings.get(aid) or {}
                for key in ("clip_id", "meme_tag", "channel_id"):
                    if not binding.get(key):
                        errors.append(f"{os.path.basename(path)}: binding {aid}.{key} manquant")
                if not (video.get("source_post") or {}).get("screenshot_png"):
                    errors.append(f"{os.path.basename(path)}: videos[{aid}] capture PNG manquante")
        for i, video in enumerate(pack.get("videos", [])):
            desc = (video.get("metadata") or {}).get("description") or ""
            if not desc.strip():
                errors.append(f"{os.path.basename(path)}: videos[{i}] "
                              f"(angle {video.get('angle_id')}) sans description")
    if errors:
        print("[F05:LOGO] Packs invalides :")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)

    campaign_id = packs[0][1].get("pack_id")
    sub_mode = packs[0][1].get("sub_mode", "?")
    total_videos = sum(len(p.get("videos", [])) for _, p in packs)

    index = {
        "pack_id": campaign_id,
        "sub_mode": sub_mode,
        "video_count": total_videos,
        "generated_at": now_iso(),
        "packs": [{"file": os.path.basename(path)} for path, _ in packs],
    }
    save_json(os.path.join(OUT_DIR, "packs_index.json"), index)

    lines = [
        "# F05_PACKAGER — Synthèse des packs LOGO",
        "",
        f"- Pack : {campaign_id or 'N/A'}",
        f"- Sous-mode : {sub_mode}",
        f"- Videos : {total_videos}",
        f"- Schéma : {resolve_schema_path()}",
        "",
    ]
    if sub_mode == "meme":
        lines += [
            "| # | Angle | Meme | Titre | Durée (s) |",
            "|---|---|---|---|---|",
        ]
    else:
        lines += ["| # | Angle | Titre | Cut | Logo |", "|---|---|---|---|---|"]
    for _, pack in packs:
        for v in pack.get("videos", []):
            if sub_mode == "meme":
                lines.append(
                    f"| {v.get('video_index')} | {v.get('angle_id')} "
                    f"| {v.get('meme') or '—'} "
                    f"| {(v.get('title') or '')[:40]} "
                    f"| {v.get('duration_sec', 8)} |")
            else:
                cut = v.get("cut", {})
                lines.append(
                    f"| {v.get('video_index')} | {v.get('angle_id')} "
                    f"| {(v.get('title') or '')[:40]} "
                    f"| {cut.get('start_sec')}-{cut.get('end_sec')}s "
                    f"({cut.get('cut_source')}) | image transparente campagne |")
    lines += ["", f"**{total_videos} videos prêtes → OMNIS_WATCH**"]
    summary_path = os.path.join(OUT_DIR, "packager_summary.md")
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    custos = os.path.join(_FORGE_ROOT, "IW_CUSTOS.py")
    if os.path.exists(custos):
        subprocess.run([sys.executable, custos, "--mode", "check-in",
                        "--frigate", "F05", "--output", summary_path],
                       capture_output=True, text=True, timeout=30)
    print(f"[F05:LOGO] Finalize : {total_videos} videos validées — {summary_path}")


def cmd_finalize(args):
    if load_profile().mode == "logo":
        cmd_finalize_logo(args)
        return
    packs = _collect_packs()
    validator = SchemaValidator(SCHEMA_PATH)
    f01 = load_f01_specimen()
    asset_urls = [a.get("url") for a in f01.get("assets", [])]

    errors = []
    unobserved_style = []
    for path, pack in packs:
        errors += validator.validate(pack, root=os.path.basename(path))
        source = pack.get("source", {})
        if source.get("video_url") and source["video_url"] not in asset_urls:
            errors.append(f"{os.path.basename(path)}: HERESIE — video_url hors assets F01")
        if source.get("source_permission") != "campaign_provided":
            errors.append(f"{os.path.basename(path)}: source_permission invalide")
        if not pack.get("reference_style", {}).get("observed", False):
            unobserved_style.append(path)

    if errors:
        print("[F05] Packs invalides :")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)

    platform = packs[0][1].get("cibles", {}).get("target_platform", "?")
    market = packs[0][1].get("cibles", {}).get("target_market", "?")
    campaign_id = packs[0][1].get("identite", {}).get("campaign_id")

    index = {
        "campaign_id": campaign_id,
        "target_platform": platform,
        "target_market": market,
        "pack_count": len(packs),
        "generated_at": now_iso(),
        "packs": [
            {
                "angle_id": pack.get("identite", {}).get("angle_id"),
                "pack_index": pack.get("identite", {}).get("pack_index"),
                "pack_total": pack.get("identite", {}).get("pack_total"),
                "file": os.path.basename(path),
            }
            for path, pack in packs
        ],
    }
    save_json(os.path.join(OUT_DIR, "packs_index.json"), index)

    lines = [
        "# F05_PACKAGER — Synthèse des packs",
        "",
        f"- Campagne : {campaign_id or 'N/A'}",
        f"- Cibles : {platform} / {market}",
        f"- Packs validés : {len(packs)}/{len(packs)}",
        "",
        "| Pack | Angle | Plateforme | Marché | Style ADN | Checklist |",
        "|---|---|---|---|---|---|",
    ]
    for path, pack in packs:
        identite = pack.get("identite", {})
        style = pack.get("reference_style", {})
        style_state = "observé" if style.get("observed") else "défaut (vision IRON requise)"
        lines.append(
            f"| {identite.get('pack_index')}/{identite.get('pack_total')} "
            f"| {identite.get('angle_id')} | {platform} | {market} "
            f"| {style_state} | 7 items pending |")
    lines += [
        "",
        f"**{len(packs)} packs prêts à expédier → OMNIS_WATCH** "
        f"(mode `--pack production_pack_<angle>.json`)",
    ]
    if unobserved_style:
        lines += [
            "",
            f"⚠️ {len(unobserved_style)} pack(s) avec reference_style non observé "
            f"— prompt vision généré dans IN/reference_style_prompt.json : ",
        ]
        for path in unobserved_style:
            lines.append(f"- {os.path.basename(path)}")
    summary_path = os.path.join(OUT_DIR, "packager_summary.md")
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    custos = os.path.join(_FORGE_ROOT, "IW_CUSTOS.py")
    if os.path.exists(custos):
        subprocess.run([sys.executable, custos, "--mode", "check-in",
                        "--frigate", "F05", "--output", summary_path],
                       capture_output=True, text=True, timeout=30)
    print(f"[F05] Finalize : {len(packs)} packs validés — {summary_path}")
    print("[F05] Check-in IW_CUSTOS — fleet_status -> packs_assembled")
    if unobserved_style:
        print(f"[F05] ATTENTION: {len(unobserved_style)} pack(s) avec style ADN par défaut "
              "(vision IRON du clip de référence requise)")


def main():
    parser = argparse.ArgumentParser(description="F05_PACKAGER — Le Ferrier de la Porte 4")
    parser.add_argument("--assemble", action="store_true",
                        help="Assemble les N packs depuis F01-F04")
    parser.add_argument("--finalize", action="store_true",
                        help="Validation schéma + index + summary + check-in")
    parser.add_argument("--angles", default=None, help="Chemin vers angles.json")
    parser.add_argument("--platform", default=None, help="Plateforme cible (override)")
    parser.add_argument("--market", default=None, help="Marché cible (override)")
    parser.add_argument("--sub-mode", default=None,
                        help="Mode LOGO: informatif (article+background) | humour "
                             "(blague/meme) | meme (mot-clé viral, F01/F03 SKIP)")
    args = parser.parse_args()

    if args.assemble:
        cmd_assemble(args)
    elif args.finalize:
        cmd_finalize(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
