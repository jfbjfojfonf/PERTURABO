"""
libs/outlier_scorer.py — Calcul outlier_score (TYRANT prospectif)
=================================================================

Démon = clip avec outlier_score > 3x. Aucun Démon sans preuve quantitative
(hérésie). Le score est lu depuis les métadonnées yt-dlp ou le specimen
(channel_follower_count / views).

Usage:
  from outlier_scorer import OutlierScorer
  scorer = OutlierScorer(threshold=3.0)
  ok, score = scorer.is_demon(view_count, baseline)
"""


class OutlierScorer:
    def __init__(self, threshold: float = 3.0):
        self.threshold = threshold

    def score(self, view_count, baseline) -> float | None:
        try:
            v = int(view_count or 0)
            b = int(baseline or 0)
        except (TypeError, ValueError):
            return None
        if b <= 0:
            return None
        return round(v / b, 2)

    def is_demon(self, view_count, baseline) -> tuple[bool, float | None]:
        s = self.score(view_count, baseline)
        if s is None:
            return False, None
        return s > self.threshold, s
