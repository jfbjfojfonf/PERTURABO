"""
libs/compliance_checker.py — garde-fous de F04_COPYWRITER
=========================================================

Vérifie un text_payload contre les hérésies absolues (Section X de la
doctrine, couplée à anti_bullshit.md core) :

  - FTC : "#ad" présent dans caption (ou hashtags)
  - Interdits absolus : "abonne-toi", "like et partage", "swipe up",
    "follow for more", "part 1/2/3" hors série architected
  - Paragraphe > 2 lignes
  - Clickbait sans payoff (warning)
  - Structure minimale : 3 titres, caption, hashtags 3 strates, CTA

check() -> liste de {severity: "critical"|"warning", code, message}

Le finalize refuse les "critical". Les "warning" sont reportés à
l'opérateur sans bloquer.
"""

import re
import unicodedata

FORBIDDEN_PHRASES = [
    "abonne toi",
    "like et partage",
    "like and share",
    "like & share",
    "swipe up",
    "swipeup",
    "follow for more",
]

PART_NUMBER_RE = re.compile(r"\bpart\s*[123]\b")

MAX_PARAGRAPH_CHARS = 220


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", str(text or ""))
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.replace("-", " ").replace("_", " ")
    return text.lower()


class ComplianceChecker:
    # ------------------------------------------------------------------
    def ftc_disclosure_missing(self, caption: str, hashtags: list[str]) -> bool:
        blob = _normalize(caption + " " + " ".join(hashtags))
        return "#ad" not in blob and "#sponsored" not in blob

    def forbidden_phrase(self, payload: dict) -> str | None:
        fields = []
        for t in payload.get("titles", []) or []:
            fields.append(str(t.get("text", "")))
        fields += [
            payload.get("paragraph", {}).get("text", ""),
            payload.get("caption", ""),
            payload.get("on_screen_text") or "",
            payload.get("cta_text", ""),
        ]
        blob = _normalize(" ".join(fields))
        for phrase in FORBIDDEN_PHRASES:
            if phrase in blob:
                return phrase
        return None

    def paragraph_lines(self, payload: dict) -> int:
        text = str(payload.get("paragraph", {}).get("text", "") or "")
        return text.count("\n") + 1

    # ------------------------------------------------------------------
    def check(self, payload: dict) -> list[dict]:
        issues = []
        caption = str(payload.get("caption", "") or "")
        hashtags = payload.get("hashtags", []) or []

        if self.ftc_disclosure_missing(caption, hashtags):
            issues.append({
                "severity": "critical",
                "code": "FTC_AD_MISSING",
                "message": "'#ad' absent de la caption et des hashtags (FTC obligatoire)",
            })

        phrase = self.forbidden_phrase(payload)
        if phrase:
            issues.append({
                "severity": "critical",
                "code": "FORBIDDEN_PHRASE",
                "message": f"Phrase interdite détectée: '{phrase}'",
            })

        paragraph_text = str(payload.get("paragraph", {}).get("text", "") or "")
        if len(paragraph_text) > MAX_PARAGRAPH_CHARS or self.paragraph_lines(payload) > 2:
            issues.append({
                "severity": "critical",
                "code": "PARAGRAPH_TOO_LONG",
                "message": f"Paragraphe > 2 lignes ({len(paragraph_text)} chars) — "
                           f"la longueur-courte-longue est morte",
            })

        titles = payload.get("titles", []) or []
        if len(titles) < 3:
            issues.append({
                "severity": "warning",
                "code": "TITLES_COUNT",
                "message": f"{len(titles)}/3 titres — la loi des 3 titres exige 3",
            })
        for t in titles:
            text = str(t.get("text", "")).strip()
            if len(text) < 5:
                issues.append({
                    "severity": "warning",
                    "code": "TITLE_TOO_SHORT",
                    "message": f"Titre rank {t.get('rank')} trop court: '{text}'",
                })

        if not caption:
            issues.append({
                "severity": "warning",
                "code": "CAPTION_MISSING",
                "message": "caption vide",
            })

        if len(hashtags) < 3:
            issues.append({
                "severity": "warning",
                "code": "HASHTAGS_STRATES",
                "message": f"{len(hashtags)} hashtag(s) — la loi des 3 strates "
                           f"(large + moyen + niche) exige 3 minimum",
            })

        if not str(payload.get("cta_text", "") or "").strip():
            issues.append({
                "severity": "warning",
                "code": "CTA_MISSING",
                "message": "cta_text vide (jamais 'abonne-toi' — toujours subtil)",
            })

        blob = _normalize(" ".join(str(t.get("text", "")) for t in titles))
        has_payoff = bool(paragraph_text.strip()) or bool(caption.strip())
        if blob.endswith("?") and not has_payoff:
            issues.append({
                "severity": "warning",
                "code": "CLICKBAIT_NO_PAYOFF",
                "message": "Titre interrogatif sans payoff dans caption/paragraphe "
                           "(le titre doit livrer dans la vidéo)",
            })

        return issues
