from __future__ import annotations

import copy
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
import fitness_state  # noqa: E402
from handler import handle_fitness_message  # noqa: E402


class FitnessHandlerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.old_data_dir = fitness_state.DATA_DIR
        fitness_state.DATA_DIR = Path(self.tmp.name)
        fitness_logic.get_daily_state = fitness_state.get_daily_state
        fitness_logic.get_profile = fitness_state.get_profile
        fitness_logic.update_daily_state = fitness_state.update_daily_state
        fitness_logic.append_meal_log = fitness_state.append_meal_log
        fitness_logic.append_workout_log = fitness_state.append_workout_log
        for name, default in fitness_state.DEFAULTS.items():
            fitness_state.save_json(name, copy.deepcopy(default))
        profile = fitness_state.get_profile()
        profile["metrics"]["daily_calorie_target"] = 1600
        profile["metrics"]["protein_target_g"] = 80
        fitness_state.save_json("profile.json", profile)
        fitness_state.update_daily_state({
            "nutrition": {
                "calorie_budget": 1600,
                "calories_consumed": 0,
                "calories_remaining": 1600,
                "protein_target_g": 80,
                "protein_consumed_g": 0,
                "protein_gap_g": 80,
                "meals": [],
            }
        })
        fitness_state.update_cycle_state({
            "workout_completed_count": 3,
            "meal_logging_days": 4,
            "over_budget_days": 1,
            "recovery_success_count": 1,
            "special_context_count": {"聚餐": 1},
            "weekly_wins": ["聚餐后恢复记录"],
            "next_week_focus": "训练日下午提前安排轻量加餐",
        })

    def tearDown(self) -> None:
        fitness_state.DATA_DIR = self.old_data_dir
        self.tmp.cleanup()

    def test_training_day_message_is_handled(self) -> None:
        result = handle_fitness_message("今天晚上练臀，怎么吃？")
        self.assertTrue(result["handled"])
        self.assertEqual(result["intent"], "daily_plan")
        self.assertIn("轻碳水", result["reply"])
        self.assertIn("day_type", result["state_changes"])

    def test_meal_message_is_handled(self) -> None:
        result = handle_fitness_message("中午吃了一碗牛肉面")
        self.assertTrue(result["handled"])
        self.assertEqual(result["intent"], "log_meal")
        self.assertIn("600-850 kcal", result["reply"])
        self.assertIn("meal_count", result["state_changes"])

    def test_post_workout_message_is_handled(self) -> None:
        result = handle_fitness_message("练完了，今天强度很大，练后吃什么？")
        self.assertTrue(result["handled"])
        self.assertEqual(result["intent"], "post_workout_meal")
        self.assertIn("蛋白质", result["reply"])
        self.assertIn("post_workout_meal_status", result["state_changes"])

    def test_lapse_message_is_handled(self) -> None:
        result = handle_fitness_message("我今天吃爆了，不想记了")
        self.assertTrue(result["handled"])
        self.assertEqual(result["intent"], "lapse_recovery")
        self.assertIn("不用补齐所有记录", result["reply"])
        self.assertIn("lapse_risk", result["state_changes"])

    def test_weekly_review_message_is_handled(self) -> None:
        today = fitness_state.get_today_str()
        fitness_state.update_daily_state({
            "training": {"type": "glutes", "status": "completed"},
            "workouts": [{"training_type": "glutes", "status": "completed"}],
            "nutrition": {"meals": [{"description": "午餐"}, {"description": "晚餐"}]},
        }, date=today)
        result = handle_fitness_message("这周怎么样？")
        self.assertTrue(result["handled"])
        self.assertEqual(result["intent"], "weekly_review")
        self.assertIn("完成了 1 次训练", result["reply"])

    def test_non_fitness_message_hands_off(self) -> None:
        result = handle_fitness_message("帮我把明天的会议整理一下")
        self.assertFalse(result["handled"])
        self.assertEqual(result["intent"], "unknown")
        self.assertEqual(result["reply"], "")


if __name__ == "__main__":
    unittest.main()
