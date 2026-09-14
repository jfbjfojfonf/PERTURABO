"""
libs/md_renderer.py — Phase D de F04_COPYWRITER
===============================================

Génère OUT/text_payload_<angle_id>.md : le format lisible opérateur
que le Warsmith lit au moment de poster (pas le JSON).

Format imposé par le TRACKING.md de F04 (boîtes ═══, sections
TITRES / PARAGRAPHE / CAPTION / HASHTAGS / ON-SCREEN / CTA).
"""


class MdRenderer:
    def render(self, payload: dict, index: int = 1, total: int = 1) -> str:
        angle_family = payload.get("angle_family") or "?"
        emotion = payload.get("emotion_mode") or "?"
        engagement = payload.get("engagement_type") or "?"
        platform = payload.get("platform_target") or "?"
        market = payload.get("market_target") or "?"

        lines = [
            "═══ ANGLE %d/%d ═══" % (index, total),
            f"ANGLE : {angle_family}",
            f"ÉMOTION : {emotion}",
            f"ENGAGEMENT : {engagement}",
            f"PLATEFORME : {platform}",
            f"MARCHÉ : {market}",
            "",
            "── TITRES (3 calibrés) ──",
        ]

        titles = payload.get("titles", []) or []
        for i, t in enumerate(titles, start=1):
            lines.append(
                f"{i}. {t.get('text', '—')}\n"
                f"   [platform_fit: {t.get('platform_fit', '?')}/10, "
                f"market_fit: {t.get('market_fit', '?')}/10, "
                f"hook: {t.get('hook_type', '?')}]"
            )

        paragraph = payload.get("paragraph", {}) or {}
        lines += ["", "── PARAGRAPHE (optionnel, 2 lignes) ──"]
        paragraph_text = str(paragraph.get("text", "") or "")
        if paragraph_text:
            lines.append(paragraph_text)
            reco = paragraph.get("recommendation", "?")
            oracle = paragraph.get("override_omniswatch")
            operator = paragraph.get("final_operator")
            lines.append(
                f" reco: {reco}  |  oracle: {oracle or 'null'}  |  "
                f"operateur: {operator or 'null'}")
        else:
            lines.append("(aucun)")

        caption = str(payload.get("caption", "") or "")
        hashtags = " ".join(payload.get("hashtags", []) or [])
        lines += ["", "── CAPTION ──", caption]
        lines += ["", "── HASHTAGS ──", hashtags]

        on_screen = payload.get("on_screen_text")
        lines += ["", "── ON-SCREEN TEXT (keyframe optionnelle) ──"]
        lines.append(str(on_screen) if on_screen else "(aucun)")

        lines += ["", "── CTA ──", str(payload.get("cta_text", "") or "")]

        compliance = payload.get("compliance", {}) or {}
        lines += [
            "",
            f"── COMPLIANCE ──  disclosure: {compliance.get('disclosure', '#ad')}  "
            f"|  ftc_required: {compliance.get('ftc_required', True)}",
        ]
        return "\n".join(lines) + "\n"
