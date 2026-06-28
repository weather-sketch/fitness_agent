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

import fitness_recall  # noqa: E402
import fitness_state  # noqa: E402


class FitnessRecallRulesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.old_data_dir = fitness_state.DATA_DIR
        fitness_state.DATA_DIR = Path(self.tmp.name) / "data"
        self.today = "2026-06-22"
        self.now = "2026-06-22T18:00:00"

    def tearDown(self) -> None:
        fitness_state.DATA_DIR = self.old_data_dir
        self.tmp.cleanup()

    def test_default_recall_is_disabled(self) -> None:
        state = fitness_state.get_recall_state(user_id="default")

        self.assertFalse(state["enabled"])

    def test_opt_in_and_opt_out_toggle_enabled(self) -> None:
        self.assertTrue(fitness_recall.set_recall_opt_in("default", True)["enabled"])
        self.assertFalse(fitness_recall.set_recall_opt_in("default", False)["enabled"])

    def test_training_day_no_meal_log_generates_opportunity(self) -> None:
        fitness_state.update_daily_state({
            "day_type": "training_day",
            "training": {"planned": True, "time": "evening", "status": "planned"},
            "nutrition": {"meals": []},
        }, user_id="default", date=self.today)

        result = fitness_recall.detect_recall_opportunity(user_id="default", date=self.today, now=self.now)

        self.assertEqual(result["recall_type"], "training_day_no_meal_log")
        self.assertFalse(result["should_send"])
        self.assertEqual(result["blocked_reason"], "recall_disabled")
        self.assertIn("不用补全记录", result["message"])

    def test_post_workout_no_recovery_meal_generates_opportunity(self) -> None:
        fitness_state.update_daily_state({
            "training": {"status": "completed", "post_workout_meal_status": "unknown"},
            "nutrition": {"meals": []},
            "workouts": [{"status": "completed", "training_type": "glutes"}],
        }, user_id="default", date=self.today)

        result = fitness_recall.detect_recall_opportunity(user_id="default", date=self.today, now=self.now)

        self.assertEqual(result["recall_type"], "post_workout_no_recovery_meal")
        self.assertIn("练完后不用吃很多", result["message"])

    def test_lapse_recovery_copy_is_non_shaming(self) -> None:
        message = fitness_recall.generate_recall_message("lapse_recovery_followup")

        self.assertIn("不用补前面的记录", message)
        self.assertIn("节奏接回来", message)
        self.assertNotIn("你又忘了", message)
        self.assertNotIn("补齐所有记录", message)
        self.assertNotIn("惩罚", message)

    def test_travel_or_social_reset_copy_emphasizes_reset(self) -> None:
        message = fitness_recall.generate_recall_message("travel_or_social_meal_reset")

        self.assertIn("不用补旅行或聚餐的账", message)
        self.assertIn("重新接上", message)

    def test_travel_or_social_context_generates_reset_opportunity(self) -> None:
        fitness_state.update_daily_state({
            "special_context": ["social_meal"],
            "nutrition": {"meals": []},
        }, user_id="default", date=self.today)

        result = fitness_recall.detect_recall_opportunity(user_id="default", date=self.today, now=self.now)

        self.assertEqual(result["recall_type"], "travel_or_social_meal_reset")

    def test_low_data_restart_copy_is_low_pressure(self) -> None:
        message = fitness_recall.generate_recall_message("low_data_gentle_restart", silence_days=4)

        self.assertIn("不用补前面的记录", message)
        self.assertIn("从今天一餐开始", message)
        self.assertNotIn("你已经", message)

    def test_low_data_generates_gentle_restart_opportunity(self) -> None:
        result = fitness_recall.detect_recall_opportunity(user_id="default", date=self.today, now=self.now)

        self.assertEqual(result["recall_type"], "low_data_gentle_restart")
        self.assertFalse(result["should_send"])

    def test_enabled_true_should_send_when_not_in_cooldown(self) -> None:
        fitness_recall.set_recall_opt_in("default", True)
        fitness_state.update_daily_state({
            "day_type": "training_day",
            "training": {"planned": True, "time": "evening", "status": "planned"},
            "nutrition": {"meals": []},
        }, user_id="default", date=self.today)

        result = fitness_recall.detect_recall_opportunity(user_id="default", date=self.today, now=self.now)

        self.assertTrue(result["should_send"])
        self.assertEqual(result["blocked_reason"], "ready")

    def test_cooldown_blocks_send(self) -> None:
        fitness_recall.set_recall_opt_in("default", True)
        fitness_state.update_recall_state({"cooldown_until": "2026-06-23T18:00:00"}, user_id="default")
        fitness_state.update_daily_state({
            "day_type": "training_day",
            "training": {"planned": True, "time": "evening", "status": "planned"},
            "nutrition": {"meals": []},
        }, user_id="default", date=self.today)

        result = fitness_recall.detect_recall_opportunity(user_id="default", date=self.today, now=self.now)

        self.assertFalse(result["should_send"])
        self.assertEqual(result["blocked_reason"], "cooldown_active")

    def test_temp_state_does_not_pollute_real_or_demo_data(self) -> None:
        fitness_recall.set_recall_opt_in("temp_user", True)

        self.assertTrue((fitness_state.get_user_data_dir("temp_user") / "recall_state.json").exists())
        self.assertFalse((Path(self.tmp.name) / "demo_data").exists())


if __name__ == "__main__":
    unittest.main()
