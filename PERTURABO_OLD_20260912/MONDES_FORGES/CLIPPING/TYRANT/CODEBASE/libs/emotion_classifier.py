"""
libs/emotion_classifier.py — Classification émotion dominante (TYRANT prospectif)
=================================================================================

Classe l'émotion dominante d'un clip à partir de son transcript (keywords)
ou de son titre. Mapping léger sur les émotions canoniques du forge :
drame, joie, outrage, inspiration, peur, tristesse, admiration, humour.

Usage:
  from emotion_classifier import EmotionClassifier
  classifier = EmotionClassifier()
  emotion = classifier.classify(title="...", transcript_text="...")
"""

import re

_KEYWORDS = {
    "drame": ["died", "death", "dead", "tragique", "perdu", "funeral", "hospital",
              "diagnosed", "cancer", "accident", "lost his", "lost her", "breaking"],
    "joie": ["happy", "joy", "celebrat", "win", "fun", "hilarious", "joie", "fete",
             "wedding", "birthday", "proud"],
    "outrage": ["outrage", "shocking", "crazy", "insane", "scandal", "illegal",
                "toxic", "racist", "sexist", "scam", "fraud", "expose"],
    "inspiration": ["inspiring", "inspiration", "motivation", "never gave up",
                    "comeback", "success", "overcame", "dream"],
    "peur": ["scared", "fear", "terrified", "panic", "nightmare", "afraid"],
    "admiration": ["amazing", "legend", "hero", "genius", "goat", "masterpiece"],
    "humour": ["funny", "joke", "comedy", "laugh", "meme", "absurd", "parody"],
}

_EMOTIONS = list(_KEYWORDS.keys())


class EmotionClassifier:
    def __init__(self):
        self._cache = {}

    def classify(self, title: str = "", transcript_text: str = "") -> str | None:
        """Retourne l'émotion dominante (ou None si aucun signal)."""
        haystack = f"{title or ''} {transcript_text or ''}".lower()
        if not haystack.strip():
            return None
        scores = {em: 0 for em in _EMOTIONS}
        for em, kws in _KEYWORDS.items():
            for kw in kws:
                if kw in haystack:
                    scores[em] += 1
        best = max(scores, key=scores.get)
        if scores[best] == 0:
            return None
        return best
