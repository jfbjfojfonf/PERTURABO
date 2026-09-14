"""
anglesmith.py — ANGLESMITH : La forge des N angles (portee par F02_TYRANT_CAMP)
==============================================================================

Porte 2. Forge N angles d'attaque repartis sur 2 zones (direct + ocean bleu,
MEME source, profondeur 1 couche max), chacun combinant 4 axes :
angle_family, emotion_mode, engagement_type, reframe_dim.

Regles verrouillees :
  - Anti-cannibale : 2 axes differenciants minimum entre chaque angle
  - Ponderation learnings : poids nul si < 50 packs executes
  - Re-ciblage ocean bleu : jamais au-dela de 1 couche (heresie)

Pattern 3 phases :
  Phase 1 (prepare) : genere IN/anglesmith_prompt.json (pour l'IRON)
  Phase 2 (IRON)    : le Warsmith copie le prompt, l'IRON forge/affine les angles
                      -> ecrit OUT/angles.json
  Phase 3 (finalize): validation anti-cannibale + check-in IW_CUSTOS ANGLESMITH

Usage:
  python anglesmith.py --prepare --n-angles 10
  python anglesmith.py --auto --n-angles 10
  python anglesmith.py --finalize
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_F02_DIR = os.path.dirname(_SCRIPT_DIR)
_FORGE_ROOT = os.path.dirname(_F02_DIR)

sys.path.insert(0, os.path.join(_SCRIPT_DIR, "libs"))
from angle_forger import AngleForger
from learnings_weight import LearningsWeight

IN_DIR = os.path.join(_F02_DIR, "IN")
OUT_DIR = os.path.join(_F02_DIR, "OUT")
CAMPAIGN_DIR = os.path.join(_FORGE_ROOT, "ARCHIVUM", "campaign")

ANGLES_PATH = os.path.join(OUT_DIR, "angles.json")


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: str, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_humour_spin() -> str | None:
    """Récupère le sens humouristique proposé par le Warsmith au --deliver-subject.
    Source de vérité : liber_clipping.json -> inputs_warsmith.spin_humour.
    """
    liber_path = os.path.join(_FORGE_ROOT, "liber_clipping.json")
    if not os.path.exists(liber_path):
        return None
    try:
        liber = load_json(liber_path)
        return liber.get("inputs_warsmith", {}).get("spin_humour") or None
    except Exception:
        return None


def load_verdict() -> dict:
    path = os.path.join(CAMPAIGN_DIR, "verdict.json")
    if not os.path.exists(path):
        print(f"[ANGLESMITH] verdict introuvable: {path}")
        print("[ANGLESMITH] Lancer F02_TYRANT_CAMP --finalize d'abord (Porte 1)")
        sys.exit(1)
    return load_json(path)


def load_meme_v2_source() -> dict:
    """Charge la source sociale archivée par F01, sans consulter F00."""
    path = os.path.join(_FORGE_ROOT, "F01_SCOUT", "OUT", "source_specimen.json")
    if not os.path.exists(path):
        print(f"[ANGLESMITH:MEME_V2] source F01 introuvable: {path}")
        sys.exit(1)
    data = load_json(path)
    source = data.get("source_post") or {}
    if not source.get("text") or not source.get("screenshot_png"):
        print("[ANGLESMITH:MEME_V2] source F01 incomplete: text/screenshot_png requis")
        sys.exit(1)
    return data


def load_meme_virality() -> dict:
    """Mode MEME : charge le scan viralité F00 (OUT/meme_virality_*.json).
    Priorité au scan correspondant au mot-clé du siège (ARCHIVUM/campaign/
    keyword.txt), sinon le plus récent."""
    f00_out = os.path.join(_FORGE_ROOT, "F00_CAPTEURS", "OUT")
    candidates = sorted(
        f for f in os.listdir(f00_out)
        if f.startswith("meme_virality_") and f.endswith(".json")
    ) if os.path.isdir(f00_out) else []
    if not candidates:
        print("[ANGLESMITH] Aucun scan meme F00 (F00_CAPTEURS/OUT/meme_virality_*.json)")
        print("[ANGLESMITH] Lancer F00_CAPTEURS --scan-meme --keyword <mot-clé> d'abord (Gate 1)")
        sys.exit(1)
    # Mot-clé du siège (source de vérité) si présent
    kw_path = os.path.join(_FORGE_ROOT, "ARCHIVUM", "campaign", "keyword.txt")
    wanted = None
    if os.path.exists(kw_path):
        try:
            with open(kw_path, "r", encoding="utf-8") as f:
                wanted = f.read().strip().lower()
        except OSError:
            wanted = None
    if wanted:
        safe_wanted = re.sub(r"[^a-z0-9]+", "_", wanted).strip("_")
        match = os.path.join(f00_out, f"meme_virality_{safe_wanted}.json")
        if os.path.exists(match):
            print(f"[ANGLESMITH] Scan meme ciblé sur le mot-clé du siège: {os.path.basename(match)}")
            return load_json(match)
    path = os.path.join(f00_out, candidates[-1])
    return load_json(path)


def _apply_weights(angles: list[dict], lw: LearningsWeight):
    for angle in angles:
        angle["weight"] = lw.weight_for_family(angle["angle_family"])
    return angles


def cmd_prepare(args):
    verdict = load_verdict()
    n = int(args.n_angles)
    spin = load_humour_spin()
    prompt = {
        "mission": "ANGLESMITH (Porte 2) — Forge les N angles d'attaque sur "
                   "le verdict de la Porte 1. Zones : direct (territoire du Demon) "
                   "+ ocean bleu (re-ciblage non sature, MEME source, 1 couche max). "
                   "Ecris OUT/angles.json.",
        "n_angles": n,
        "campaign_id": verdict.get("campaign_id"),
        "verdict": verdict,
        "regles": [
            "Chaque angle combine 4 axes : angle_family, emotion_mode, engagement_type, reframe_dim",
            "Anti-cannibale : 2 axes differenciants minimum entre chaque angle",
            "Ocean bleu : depth 1 seulement, jamais 2 couches",
            "Ponderation learnings si eligible (>= 50 packs executes)",
        ],
        "heresies_interdites": [
            "Re-ciblage au-dela de 1 couche",
            "2 angles trop proches (cannibalisme)",
            "Suggere des sources alternatives (assets = forteresse fermee)",
        ],
        "output_attendu": "OUT/angles.json (schema : README.md mecanisme des N angles)",
    }
    if spin:
        prompt["spin_humour_operateur"] = spin
        prompt["regles"] = prompt["regles"] + [
            "SENS HUMOURISTIQUE (Warsmith) : forger les angles AUTOUR de ce sens. "
            "Chaque angle doit decliner la direction humour dans un registre "
            "compatible (parodie, absurde, ironie, jeux de mots) sans quitter "
            "le sujet reel. emotion_mode doit rester credible (joie/tension "
            "humoristique), jamais de moquerie defamatoire."
        ]
    save_json(os.path.join(IN_DIR, "anglesmith_prompt.json"), prompt)
    print(f"[ANGLESMITH] Prompt IRON : {os.path.join(IN_DIR, 'anglesmith_prompt.json')}")
    if spin:
        print(f"[ANGLESMITH] Spin humour operateur injecte dans le prompt: {spin}")
    print("[ANGLESMITH] Copier le prompt dans Claude sandbox -> OUT/angles.json, puis --finalize")


def cmd_auto(args):
    sub_mode = (getattr(args, "sub_mode", None) or "").lower()
    n = int(args.n_angles)
    forger = AngleForger()

    if sub_mode == "meme_v2":
        specimen = load_meme_v2_source()
        source = specimen["source_post"]
        target = source.get("target") or {}
        keyword = source.get("source_id") or "manual_meme_v2"
        virality = {"keyword": keyword, "duration_range_sec": {"min": 5, "max": 7},
                    "metrics": source.get("metrics") or {}}
        angles = forger.forge_meme(n=n, campaign_id=keyword, keyword=keyword,
                                   virality=virality, spin_humour=None)
        angle_briefs = [
            "Instant regret: the bed promised a safe landing and the floor collected the phone.",
            "Adult damage-control panic: one harmless throw becomes an expensive repair calculation.",
            "Physics betrayal: the phone bounces once and turns confidence into a full-body flinch.",
            "US apartment reality: the sound of the phone hitting the floor wakes every roommate and neighbor.",
            "Thirty-year-old self-preservation: the owner freezes before checking whether the screen survived.",
        ]
        for index, angle in enumerate(angles):
            angle["source_post_id"] = source.get("source_id")
            angle["source_text"] = source.get("text")
            angle["market_target"] = target.get("market", "US")
            angle["age_range"] = target.get("age_range", "29-30")
            angle["platform_target"] = target.get("platform", "youtube_shorts")
            angle["angle_brief"] = angle_briefs[index] if index < len(angle_briefs) else "Source-specific reaction to the phone bounce fail."
        campaign_id = keyword
        print("[ANGLESMITH] MEME V2 : source F01 uniquement, F00 non utilisé")
    elif sub_mode == "meme":
        virality = load_meme_virality()
        spin = load_humour_spin()
        angles = forger.forge_meme(n=n, campaign_id=virality.get("keyword"),
                                   keyword=virality.get("keyword"),
                                   virality=virality,
                                   spin_humour=spin)
        campaign_id = virality.get("keyword")
        if spin:
            print(f"[ANGLESMITH] Spin humour operateur injecte dans les angles meme: {spin}")
    else:
        verdict = load_verdict()
        spin = load_humour_spin()
        angles = forger.forge(n=n, campaign_id=verdict.get("campaign_id"),
                              verdict=verdict, spin_humour=spin)
        campaign_id = verdict.get("campaign_id")

    lw = LearningsWeight(_FORGE_ROOT)
    angles = _apply_weights(angles, lw)

    out = {
        "campaign_id": campaign_id,
        "n_angles": len(angles),
        "anglesmith_status": "done",
        "weighting_eligible": lw.eligible(),
        "sub_mode": sub_mode,
        "angles": angles,
        "check_in_iw_custos": None,
    }
    save_json(ANGLES_PATH, out)
    direct = [a for a in angles if a["zone"] == "direct"]
    blue = [a for a in angles if a["zone"] == "blue_ocean"]
    print(f"[ANGLESMITH] --auto : {len(angles)} angles forges "
          f"({len(direct)} direct / {len(blue)} ocean bleu), weight_eligible={lw.eligible()}")
    if sub_mode in ("meme", "meme_v2"):
        emotions = [a.get("emotion") for a in angles]
        print(f"[ANGLESMITH] mode {sub_mode}: keyword={campaign_id} — "
              f"emotions={emotions} (anti-spam: 2 max par emotion)")


def cmd_premium(args):
    """Mode MEME premium : forge les N angles via le modèle premium (GLM 5.2).
    Charge le scan F00 (stats réelles) + spin humour du ledger, appelle le
    premium, valide le schéma (anti-spam 2 max / anti-cannibale), écrit
    OUT/angles.json. Le finalize fait la validation + check-in."""
    sub_mode = (getattr(args, "sub_mode", None) or "").lower()
    n = int(args.n_angles)
    if sub_mode != "meme":
        print("[ANGLESMITH] --premium n'est implémenté qu'en --sub-mode meme")
        sys.exit(1)

    virality = load_meme_virality()
    spin = load_humour_spin()
    keyword = virality.get("keyword", "inconnu")

    sys.path.insert(0, os.path.join(_FORGE_ROOT, "F04_COPYWRITER", "CODEBASE", "libs"))
    try:
        from premium_client import PremiumClient, PremiumClientError
    except ImportError as e:
        print(f"[ANGLESMITH] premium_client introuvable (F04): {e}")
        sys.exit(1)

    system_prompt = (
        "Tu es ANGLESMITH, la forge d'angles d'attaque du pipeline CLIPPING "
        "PERTURABO — mode MEME. À partir des stats réelles du scan F00 "
        "(vues YouTube, tendances, demande, fraîcheur) et du spin humour du "
        "Warsmith, tu forges les angles d'attaque pour des videos virales "
        "YouTube Shorts (doctrine 6 couches de GUIDE_UTILISATION/04_MODE_MEME.md). "
        "Réponds en JSON strict conforme au output_schema."
    )

    user_prompt = {
        "mission": (
            f"Forge {n} angles meme (A01..A{n:02d}) pour le mot-clé « {keyword} » "
            "en déclinant le SENS HUMOUR du Warsmith dans un registre compatible "
            "(parodie, ironie, absurde, jeux de mots) SANS quitter le sujet réel."
        ),
        "keyword": keyword,
        "spin_humour_operateur": spin or "(aucun — forger des angles meme neutres)",
        "virality_scan": virality,
        "regles": [
            "Chaque angle porte : angle_id, emotion (une émotion pop-culture), "
            "emotion_mode (= emotion), angle_family, reframe_dim, engagement_type, "
            "meme_hook (format '[sujet] at [A]: -> [sujet] at [B]:'), "
            "duration_sec_range {min:5, max:7}, zone 'direct', keyword.",
            "ANTI-SPAM : une même emotion au maximum 2 angles sur les "
            f"{n} — les autres doivent être différentes.",
            "ANTI-CANNIBALE : 2 axes differenciants minimum entre chaque angle.",
            "duration_sec_range : 5-7s (jamais au-delà).",
            "emotion réaliste et credible, jamais de moquerie diffamatoire.",
            "Tout en ANGLAIS (meme_hook inclus).",
        ],
        "heresies_interdites": [
            "2 angles trop proches (cannibalisme)",
            "Une émotion sur plus de 2 angles",
            "Inventer des stats (seules les stats du scan font foi)",
        ],
        "output_schema": {
            "angles": [
                {
                    "angle_id": "A01",
                    "emotion": "drole",
                    "emotion_mode": "drole",
                    "angle_family": "reframing",
                    "reframe_dim": "fait_vers_absurde",
                    "engagement_type": "question",
                    "meme_hook": "[sujet] at [A]: -> [sujet] at [B]:",
                    "duration_sec_range": {"min": 5, "max": 7},
                    "zone": "direct",
                    "keyword": keyword,
                }
            ]
        },
    }

    client = PremiumClient(_FORGE_ROOT)
    try:
        client.require_config()
        result = client.chat(system_prompt=system_prompt,
                             user_prompt=json.dumps(user_prompt, indent=2,
                                                    ensure_ascii=False))
    except PremiumClientError as e:
        print(f"[ANGLESMITH] Échec premium : {e}")
        sys.exit(1)

    if not result:
        print("[ANGLESMITH] Réponse premium vide")
        sys.exit(1)
    try:
        parsed = json.loads(client.extract_json(result))
    except (json.JSONDecodeError, ValueError) as e:
        print(f"[ANGLESMITH] Sortie premium non-JSON: {e}")
        print(result[:1000])
        sys.exit(1)

    angles = parsed.get("angles") or []
    if len(angles) < n:
        print(f"[ANGLESMITH] WARN: {len(angles)} angles reçus (demandé {n})")

    for i, angle in enumerate(angles):
        angle["angle_id"] = f"A{i + 1:02d}"
        angle.setdefault("emotion_mode", angle.get("emotion"))
        angle.setdefault("zone", "direct")
        angle.setdefault("keyword", keyword)
        angle.setdefault("duration_sec_range", {"min": 5, "max": 7})
        angle.setdefault("weight", 1.0)
        if spin:
            angle["humour_spin"] = spin

    out = {
        "campaign_id": keyword,
        "n_angles": len(angles),
        "anglesmith_status": "done",
        "weighting_eligible": LearningsWeight(_FORGE_ROOT).eligible(),
        "sub_mode": sub_mode,
        "forge_mode": "premium",
        "angles": angles,
        "check_in_iw_custos": None,
    }
    save_json(ANGLES_PATH, out)
    print(f"[ANGLESMITH] --premium : {len(angles)} angles meme forges via premium "
          f"({client.config.get('model_id')}) — OUT/angles.json")
    print(f"[ANGLESMITH] keyword={keyword} spin={spin is not None}")
    emotions = [a.get("emotion") for a in angles]
    print(f"[ANGLESMITH] emotions={emotions} — lancer --finalize pour valider (anti-spam)")


def cmd_finalize(args):
    if not os.path.exists(ANGLES_PATH):
        print("[ANGLESMITH] OUT/angles.json absent — lancer --prepare puis IRON, ou --auto")
        sys.exit(1)

    out = load_json(ANGLES_PATH)
    angles = out.get("angles", [])
    forger = AngleForger()

    # Heresie guard : profondeur + anti-cannibale
    for angle in angles:
        depth = angle.get("blue_ocean_depth")
        if depth is not None and depth != 1:
            print(f"[ANGLESMITH] HERESIE : depth={depth} != 1 — angle {angle.get('angle_id')} clampe")
            angle["blue_ocean_depth"] = 1

    for i in range(len(angles)):
        for j in range(i + 1, len(angles)):
            if forger._axes_different(angles[i], angles[j]) < 2:
                print(f"[ANGLESMITH] CANNIBALE: {angles[i].get('angle_id')} vs "
                      f"{angles[j].get('angle_id')} trop proches — flags")

    sub_mode = out.get("sub_mode", "")
    if sub_mode == "meme":
        counts = {}
        for angle in angles:
            emo = angle.get("emotion")
            if emo:
                counts[emo] = counts.get(emo, 0) + 1
        spam = {e: c for e, c in counts.items() if c > 2}
        if spam:
            print(f"[ANGLESMITH] HÉRÉSIE ANTI-SPAM: émotion(s) > 2 angles — {spam}")
            print("[ANGLESMITH] Corriger emotions dans OUT/angles.json avant la Porte 3")
        else:
            print("[ANGLESMITH] Anti-spam émotions OK (2 max par émotion)")

    lw = LearningsWeight(_FORGE_ROOT)
    out["angles"] = _apply_weights(angles, lw)
    out["check_in_iw_custos"] = now_iso()
    save_json(ANGLES_PATH, out)

    custos = os.path.join(_FORGE_ROOT, "IW_CUSTOS.py")
    if os.path.exists(custos):
        subprocess.run([sys.executable, custos, "--mode", "check-in",
                        "--frigate", "ANGLESMITH", "--output", ANGLES_PATH],
                       capture_output=True, text=True, timeout=30)
    print(f"[ANGLESMITH] Finalize : {len(angles)} angles valides — check-in ANGLESMITH done")
    print("[ANGLESMITH] OUT/angles.json pret pour la Porte 3 (F03 + F04)")


def main():
    parser = argparse.ArgumentParser(description="ANGLESMITH — Forge des N angles (Porte 2)")
    parser.add_argument("--prepare", action="store_true", help="Phase 1 : prompt IRON")
    parser.add_argument("--auto", action="store_true", help="Forge auto locale (sans IRON)")
    parser.add_argument("--premium", action="store_true",
                        help="Mode MEME premium : forger les angles via le modele "
                             "premium (GLM 5.2) sur le scan F00 + spin humour")
    parser.add_argument("--finalize", action="store_true", help="Phase 3 : validation + check-in")
    parser.add_argument("--n-angles", default="10", help="Nombre d'angles (defaut 10)")
    parser.add_argument("--sub-mode", default=None,
                        help="Mode MEME: forger les 5 angles sur le scan F00 "
                             "(keyword + stats), F01/F03 SKIP")
    args = parser.parse_args()

    if args.prepare:
        cmd_prepare(args)
    elif args.auto:
        cmd_auto(args)
    elif args.premium:
        cmd_premium(args)
    elif args.finalize:
        cmd_finalize(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
