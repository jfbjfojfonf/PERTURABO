import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "libs"))

from research_profile import build_profile  # noqa: E402


class ResearchProfileTests(unittest.TestCase):
    def test_contextual_profile(self):
        profile = build_profile(
            horizon="24h",
            platform="youtube_shorts",
            market="us_young_english",
            niche="student debt",
            niche_mode="meme",
            mode="informatif",
            freshness="brulant",
        )
        self.assertEqual(profile["horizon"], "24h")
        self.assertEqual(profile["platform"], "youtube_shorts")
        self.assertEqual(profile["niche_mode"], "meme")
        self.assertFalse(profile["legacy_compat"])
        self.assertAlmostEqual(sum(profile["weights"].values()), 1.0)

    def test_legacy_profile_is_preserved(self):
        profile = build_profile(
            horizon=None,
            platform=None,
            market=None,
            niche="Lakers basketball",
            niche_mode=None,
            mode="informatif",
            freshness="brulant",
        )
        self.assertTrue(profile["legacy_compat"])
        self.assertEqual(profile["window_hours"], 5)
        self.assertEqual(profile["platform"], "youtube_shorts")

    def test_all_horizons_are_distinct(self):
        windows = []
        for horizon in ("2h", "6h", "12h", "24h", "3d", "7d", "30d"):
            profile = build_profile(
                horizon=horizon,
                platform="youtube_shorts",
                market="us_young_english",
                niche="meme",
                niche_mode="meme",
                mode="informatif",
                freshness="brulant",
            )
            windows.append(profile["window_hours"])
        self.assertEqual(windows, [2, 6, 12, 24, 72, 168, 720])


if __name__ == "__main__":
    unittest.main()
