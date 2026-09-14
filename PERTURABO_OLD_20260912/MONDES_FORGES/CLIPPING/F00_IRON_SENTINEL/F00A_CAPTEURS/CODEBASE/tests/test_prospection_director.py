import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "libs"))

from prospection_director import (  # noqa: E402
    build_deterministic_questions,
    build_session,
    validate_question_plan,
)


class ProspectionDirectorTests(unittest.TestCase):
    def test_deterministic_plan_has_objectives_and_allowed_sources(self):
        questions = build_deterministic_questions("US Among Us players", "youtube_shorts", "30d")
        self.assertGreaterEqual(len(questions), 3)
        checked = validate_question_plan({"questions": questions})
        self.assertEqual(checked["status"], "pass")
        self.assertTrue(all(q["objective"] and q["queries"] for q in questions))

    def test_unknown_source_is_blocked(self):
        result = validate_question_plan({"questions": [{
            "question_id": "Q-X", "objective": "x", "question": "x",
            "queries": ["x"], "sources_allowed": ["unknown"],
            "expected_evidence": []
        }]})
        self.assertEqual(result["status"], "blocked")

    def test_session_has_zero_invention_and_three_turn_limit(self):
        session = build_session("US Among Us players", "youtube_shorts", "30d")
        self.assertEqual(session["validation"]["invented"], 0)
        self.assertEqual(session["limits"]["max_turns"], 3)
        self.assertEqual(session["director"]["premium_status"], "not_called")


if __name__ == "__main__":
    unittest.main()
