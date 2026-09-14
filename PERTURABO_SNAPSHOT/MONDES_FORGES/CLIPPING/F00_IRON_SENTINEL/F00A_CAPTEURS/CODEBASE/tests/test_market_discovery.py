import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "libs"))

from market_discovery import allocate_angles, build_probe_queries, _deduplicate  # noqa: E402
from premium_evidence_guard import validate_premium_output  # noqa: E402


class MarketDiscoveryTests(unittest.TestCase):
    def test_probe_queries_are_only_search_probes(self):
        probes = build_probe_queries("US residents interested in Among Us")
        self.assertTrue(probes)
        self.assertTrue(all(isinstance(p, str) and p for p in probes))

    def test_duplicate_candidates_are_removed(self):
        items = [
            {"candidate_id": "a", "normalized_key": "among us impostor", "youtube_total_views": 100, "evidence_types": ["youtube"]},
            {"candidate_id": "b", "normalized_key": "among us impostor", "youtube_total_views": 10, "evidence_types": ["youtube"]},
        ]
        kept, removed = _deduplicate(items)
        self.assertEqual([x["candidate_id"] for x in kept], ["a"])
        self.assertEqual(removed[0]["duplicate_of"], "a")

    def test_angle_allocation_rejects_missing_candidates(self):
        candidates = [{"ocean": "blue"}, {"ocean": "red"}]
        allocation = allocate_angles(candidates, 4, blue=3, red=1)
        self.assertEqual(allocation["status"], "insufficient_candidates")

    def test_premium_cannot_add_unknown_url(self):
        payload = {"evidence": ["https://youtube.com/watch?v=known"]}
        output = {"sources": ["https://youtube.com/watch?v=unknown"]}
        result = validate_premium_output(output, payload)
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["anti_invention"], "fail")


    def test_non_meme_signal_is_desert(self):
        from market_discovery import _score_candidate
        candidate = {
            "keyword": "real estate market report",
            "normalized_key": "real estate market report",
            "evidence_urls": ["https://youtube.com/watch?v=x"],
            "evidence_types": ["youtube"],
            "youtube_video_count": 1,
            "youtube_top_views": 100000,
            "youtube_total_views": 100000,
            "suggestion_count": 2,
            "reddit_post_count": 0,
            "reddit_comments": 0,
            "trend_count": 0,
            "channel_count": 1,
            "channel_names": ["unrelated"],
        }
        result = _score_candidate(candidate, "3d", [], "US audience fans of @Zdak")
        self.assertEqual(result["ocean"], "desert")
        self.assertEqual(result["gates"]["meme"], "block")

    def test_signal_without_youtube_evidence_is_desert(self):
        from market_discovery import _score_candidate
        candidate = {
            "keyword": "funny meme reaction",
            "normalized_key": "funny meme reaction",
            "evidence_urls": [],
            "evidence_types": ["suggest"],
            "youtube_video_count": 0,
            "youtube_top_views": 0,
            "youtube_total_views": 0,
            "suggestion_count": 1,
            "reddit_post_count": 0,
            "reddit_comments": 0,
            "trend_count": 0,
            "channel_count": 0,
            "channel_names": [],
        }
        result = _score_candidate(candidate, "3d", [], "US audience fans of @Zdak")
        self.assertEqual(result["ocean"], "desert")
        self.assertEqual(result["gates"]["youtube_evidence"], "block")

    def test_unrelated_channel_does_not_pass_relevance(self):
        from market_discovery import _score_candidate
        candidate = {
            "keyword": "funny reaction meme",
            "normalized_key": "funny reaction meme",
            "evidence_urls": ["https://youtube.com/watch?v=x"],
            "evidence_types": ["youtube"],
            "youtube_video_count": 1,
            "youtube_top_views": 100000,
            "youtube_total_views": 100000,
            "suggestion_count": 1,
            "reddit_post_count": 0,
            "reddit_comments": 0,
            "trend_count": 0,
            "channel_count": 1,
            "channel_names": ["totally unrelated channel"],
        }
        result = _score_candidate(candidate, "3d", [], "US audience fans of @Zdak")
        self.assertEqual(result["gates"]["market_relevance"], "block")
        self.assertEqual(result["ocean"], "desert")

    def test_probe_queries_anchor_to_handle(self):
        probes = build_probe_queries("US audience fans of @Zdak")
        self.assertIn("@Zdak", probes)
        self.assertIn("Zdak meme", probes)

    def test_pack_requires_shared_territory(self):
        from market_discovery import build_packs
        a = {"candidate_id": "a", "keyword": "funny meme", "normalized_key": "funny meme", "ocean": "blue"}
        b = {"candidate_id": "b", "keyword": "gaming clips", "normalized_key": "gaming clips", "ocean": "red"}
        self.assertEqual(build_packs([a, b]), [])


if __name__ == "__main__":
    unittest.main()
