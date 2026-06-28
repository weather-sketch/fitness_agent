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

import fitness_logic  # noqa: E402
import fitness_memory  # noqa: E402
import fitness_state  # noqa: E402
from handler import handle_fitness_message  # noqa: E402


class FitnessPreferenceAwareRecommendationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.old_data_dir = fitness_state.DATA_DIR
        fitness_state.DATA_DIR = Path(self.tmp.name) / "data"

    def tearDown(self) -> None:
        fitness_state.DATA_DIR = self.old_data_dir
        self.tmp.cleanup()

    def _approve_yogurt_avoidance(self, user_id: str = "default") -> None:
        candidate = fitness_memory.extract_memory_candidates("以后练前别推荐酸奶，我会胃不舒服。")[0]
        fitness_state.add_memory_candidate(candidate, user_id=user_id)
        fitness_memory.approve_memory_candidate(user_id, candidate["candidate_id"])

    def _training_day_state(self) -> dict:
        return {
            "day_type": "training_day",
            "training": {"planned": True, "type": "glutes", "time": "evening", "status": "planned"},
            "nutrition": {"calories_remaining": 1600, "protein_gap_g": 80, "meals": []},
        }

    def test_daily_plan_avoids_yogurt_after_approval(self) -> None:
        self._approve_yogurt_avoidance()
        profile = fitness_state.get_profile(user_id="default")

        result = fitness_logic.generate_daily_plan(profile, self._training_day_state())

        self.assertNotIn("酸奶", result["reply"])
        self.assertIn("avoid_yogurt_pre_workout", result["active_preferences_applied"])
        self.assertIn("我会避开你不舒服的选项", result["reply"])

    def test_pre_workout_recommendation_avoids_yogurt_after_approval(self) -> None:
        self._approve_yogurt_avoidance()
        profile = fitness_state.get_profile(user_id="default")

        result = fitness_logic.recommend_pre_workout_meal(profile, self._training_day_state())

        self.assertNotIn("酸奶", result["reply"])
        self.assertIn("avoid_yogurt_pre_workout", result["active_preferences_applied"])

    def test_default_recommendation_still_mentions_yogurt(self) -> None:
        profile = fitness_state.get_profile(user_id="default")
        state = self._training_day_state()

        daily = fitness_logic.generate_daily_plan(profile, state)
        post = fitness_logic.recommend_post_workout_meal(
            profile,
            {**state, "training": {**state["training"], "actual_intensity": "high"}},
        )

        self.assertIn("酸奶", daily["reply"])
        self.assertIn("酸奶", post["reply"])

    def test_handler_debug_records_active_preference(self) -> None:
        self._approve_yogurt_avoidance(user_id="handler_user")

        result = handle_fitness_message("今天晚上练臀，怎么吃？", user_id="handler_user")

        self.assertTrue(result["handled"])
        self.assertNotIn("酸奶", result["reply"])
        self.assertIn("avoid_yogurt_pre_workout", result["debug"]["active_preferences_applied"])
        self.assertNotIn("debug", result["reply"])
        self.assertNotIn("state_changes", result["reply"])
        self.assertNotIn("{", result["reply"])


if __name__ == "__main__":
    unittest.main()
