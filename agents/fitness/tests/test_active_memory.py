from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
for path in (ROOT, TOOLS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import fitness_memory  # noqa: E402
import fitness_state  # noqa: E402


class FitnessActiveMemoryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.old_data_dir = fitness_state.DATA_DIR
        fitness_state.DATA_DIR = Path(self.tmp.name) / "data"
        self.candidate = fitness_memory.extract_memory_candidates("以后练前别推荐酸奶，我会胃不舒服。")[0]
        fitness_state.add_memory_candidate(self.candidate, user_id="default")

    def tearDown(self) -> None:
        fitness_state.DATA_DIR = self.old_data_dir
        self.tmp.cleanup()

    def test_approve_candidate_updates_status_and_active_preference(self) -> None:
        reviewed = fitness_memory.approve_memory_candidate("default", self.candidate["candidate_id"])
        active = fitness_memory.get_active_preferences(user_id="default")

        self.assertEqual(reviewed["status"], "approved")
        self.assertEqual(reviewed["applied_to"], "profile.preferences.food_avoidance")
        self.assertEqual(active["food_avoidance"][0]["key"], "avoid_yogurt_pre_workout")
        self.assertEqual(active["food_avoidance"][0]["avoid_items"], ["酸奶", "yogurt"])

    def test_repeated_approve_is_idempotent(self) -> None:
        fitness_memory.approve_memory_candidate("default", self.candidate["candidate_id"])
        fitness_memory.approve_memory_candidate("default", self.candidate["candidate_id"])
        active = fitness_memory.get_active_preferences(user_id="default")

        self.assertEqual(len(active["food_avoidance"]), 1)
        self.assertEqual(len(active["safety_boundaries"]), 1)

    def test_rejected_candidate_does_not_write_active_preference(self) -> None:
        fitness_memory.reject_memory_candidate("default", self.candidate["candidate_id"])
        active = fitness_memory.get_active_preferences(user_id="default")

        self.assertEqual(active["food_avoidance"], [])

    def test_archived_candidate_does_not_write_active_preference(self) -> None:
        fitness_memory.archive_memory_candidate("default", self.candidate["candidate_id"])
        active = fitness_memory.get_active_preferences(user_id="default")

        self.assertEqual(active["food_avoidance"], [])

    def test_get_active_preferences_works_for_new_user(self) -> None:
        active = fitness_memory.get_active_preferences(user_id="new_user")

        self.assertEqual(active["food_avoidance"], [])
        self.assertEqual(active["routine"], [])

    def test_feedback_style_candidate_is_stored_but_not_forced_globally(self) -> None:
        candidate = fitness_memory.extract_memory_candidates("我更喜欢你给我一句话总结，不要长篇分析。")[0]
        fitness_state.add_memory_candidate(candidate, user_id="style_user")
        fitness_memory.approve_memory_candidate("style_user", candidate["candidate_id"])
        active = fitness_memory.get_active_preferences(user_id="style_user")

        self.assertIn("concise_summary", active["feedback_style"])

    def test_temp_state_does_not_pollute_real_or_demo_data(self) -> None:
        fitness_memory.approve_memory_candidate("default", self.candidate["candidate_id"])

        self.assertTrue((fitness_state.get_user_data_dir("default") / "profile.json").exists())
        self.assertFalse((Path(self.tmp.name) / "demo_data").exists())


if __name__ == "__main__":
    unittest.main()
