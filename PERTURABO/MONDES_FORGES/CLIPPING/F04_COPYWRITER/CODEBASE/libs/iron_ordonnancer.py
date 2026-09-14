"""
libs/iron_ordonnancer.py — Phase C de F04_COPYWRITER
====================================================

L'IRON (sandbox Claude) ordonnance la sortie brute du premium :

  1. Valide la cohérence (pas de contradiction, pas d'hallucination
     de hook_type)
  2. Classe les 3 titres par rank (1, 2, 3) selon
     platform_fit + market_fit (+ bonus hook_type connu)
  3. Tag le paragraph.recommendation ("use" | "skip")
  4. Vérifie FTC compliance + anti-bullshit (via compliance_checker)

Deux modes :
  - build_iron_prompt() : produit IN/ordonnance_prompt_<angle>.json
    que le Warsmith copie dans le sandbox Claude (l'IRON écrit
    OUT/text_payload_<angle>.json)
  - ordonnance_auto()   : ordonnancement local heuristique (sans IRON) —
    classement + reco paragraphe + auto-fix #ad. Le pipeline tourne
    même sans IRON ; la qualité reste inférieure à l'IRON.
"""

import json

from compliance_checker import ComplianceChecker

HOOK_TYPES = [
    "stat_choc", "question", "declaration", "mystery",
    "contradiction", "cible_naming",
]

MAX_PARAGRAPH_CHARS = 220


class IronOrdonnancer:
    # ------------------------------------------------------------------
    def build_iron_prompt(self, raw: dict, angle: dict,
                          platform: str, market: str) -> dict:
        return {
            "mission": "F04_COPYWRITER — Phase C : ordonnancement IRON du "
                       "text_payload brut généré par le modèle premium.",
            "angle_id": angle.get("angle_id"),
            "angle": {
                "angle_family": angle.get("angle_family"),
                "emotion_mode": angle.get("emotion_mode"),
                "engagement_type": angle.get("engagement_type"),
                "reframe_dim": angle.get("reframe_dim"),
                "zone": angle.get("zone"),
            },
            "platform_target": platform,
            "market_target": market,
            "raw_premium": raw,
            "taches": [
                "1. Valider la cohérence : pas de contradiction interne, "
                "pas d'hallucination de hook_type",
                "2. Classer les 3 titres par rank (1, 2, 3) selon "
                "platform_fit + market_fit + force du hook (meilleur en rank 1)",
                "3. Tagger paragraph.recommendation : 'use' si le paragraphe "
                "est pertinent vs l'angle (2 lignes max), 'skip' sinon",
                "4. Vérifier FTC : '#ad' présent dans caption",
                "5. Vérifier anti-bullshit : pas de 'abonne-toi', pas de "
                "clickbait pur sans payoff",
            ],
            "output_attendu": "OUT/text_payload_<angle_id>.json — schéma strict "
                              "(cf. F04_COPYWRITER/CODEBASE/TRACKING.md). "
                              "Conserver override_omniswatch=null et "
                              "final_operator=null (vetos downstream).",
            "heresies_interdites": [
                "Abonne-toi / Like et partage / Swipe up",
                "Paragraphe > 2 lignes",
                "hook_type hors taxonomie (stat_choc, question, declaration, "
                "mystery, contradiction, cible_naming)",
                "Rank identiques entre titres",
            ],
        }

    # ------------------------------------------------------------------
    def ordonnance_auto(self, raw: dict, angle: dict,
                        platform: str, market: str,
                        campaign_id: str = None) -> tuple[dict, list[str]]:
        notes = []

        raw_titles = raw.get("titles", []) or []
        ranked = []
        for i, t in enumerate(raw_titles):
            if not isinstance(t, dict):
                continue
            platform_fit = _to_int(t.get("platform_fit"), default=5)
            market_fit = _to_int(t.get("market_fit"), default=5)
            hook_type = t.get("hook_type")
            hook_bonus = 1 if hook_type in HOOK_TYPES else 0
            if hook_type and hook_type not in HOOK_TYPES:
                notes.append(f"hook_type hors taxonomie '{hook_type}' -> declaration")
                hook_type = "declaration"
            ranked.append({
                "text": str(t.get("text", "")).strip(),
                "platform_fit": max(0, min(10, platform_fit)),
                "market_fit": max(0, min(10, market_fit)),
                "hook_type": hook_type or "declaration",
                "rationale": str(t.get("rationale", "")).strip() or "—",
                "_score": platform_fit + market_fit + hook_bonus,
            })
        ranked.sort(key=lambda t: t["_score"], reverse=True)
        titles = []
        for rank, t in enumerate(ranked, start=1):
            entry = {k: t[k] for k in ("text", "platform_fit", "market_fit",
                                       "hook_type", "rationale")}
            entry["rank"] = rank
            titles.append(entry)
        if not titles:
            notes.append("AUCUN titre exploitable — ordonnancement impossible")
        elif len(titles) < 3:
            notes.append(f"Seulement {len(titles)} titre(s) exploitable(s) "
                         f"(la loi des 3 titres exige 3)")

        paragraph_text = str(raw.get("paragraph", {}).get("text", "") or "").strip()
        reco = "skip"
        if paragraph_text:
            lines = paragraph_text.count("\n") + 1
            if len(paragraph_text) <= MAX_PARAGRAPH_CHARS and lines <= 2:
                reco = "use"
            else:
                notes.append(f"Paragraphe > limite ({len(paragraph_text)} chars, "
                             f"{lines} lignes) -> reco skip")
        paragraph = {
            "text": paragraph_text,
            "recommendation": reco,
            "override_omniswatch": None,
            "final_operator": None,
        }

        caption = str(raw.get("caption", "") or "").strip()
        hashtags = [h.strip() for h in raw.get("hashtags", []) or []
                    if isinstance(h, str) and h.strip()]

        checker = ComplianceChecker()
        ftd_missing = checker.ftc_disclosure_missing(caption, hashtags)
        if ftd_missing:
            caption = (caption + " #ad").strip()
            hashtags.append("#ad")
            notes.append("FTC auto-fix : '#ad' ajouté à la caption")

        on_screen = raw.get("on_screen_text")
        if on_screen is not None and not str(on_screen).strip():
            on_screen = None

        payload = {
            "campaign_id": raw.get("campaign_id") or campaign_id,
            "angle_id": angle.get("angle_id"),
            "angle_family": angle.get("angle_family"),
            "emotion_mode": angle.get("emotion_mode"),
            "engagement_type": angle.get("engagement_type"),
            "platform_target": platform,
            "market_target": market,
            "titles": titles,
            "paragraph": paragraph,
            "caption": caption,
            "hashtags": hashtags,
            "on_screen_text": on_screen,
            "cta_text": str(raw.get("cta_text", "") or "").strip(),
            "compliance": {
                "disclosure": "#ad",
                "ftc_required": True,
            },
            "check_in_iw_custos": None,
        }
        return payload, notes


def _to_int(value, default: int = 5) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
