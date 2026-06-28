from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import fitness_logic  # noqa: E402
import fitness_state  # noqa: E402


class FitnessToolsTest(unittest.TestCase):
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
                "meals": []
            }
        })

    def tearDown(self) -> None:
        fitness_state.DATA_DIR = self.old_data_dir
        self.tmp.cleanup()

    def test_json_files_can_read_write(self) -> None:
        fitness_state.update_daily_state({"day_type": "rest_day"})
        self.assertEqual(fitness_state.get_daily_state()["day_type"], "rest_day")

    def test_log_meal_increases_calories(self) -> None:
        before = fitness_state.get_daily_state()["nutrition"]["calories_consumed"]
        result = fitness_logic.log_meal("中午吃了一碗牛肉面")
        after = result["daily_state"]["nutrition"]["calories_consumed"]
        self.assertEqual(result["intent"], "log_meal")
        self.assertGreater(after, before)
        self.assertEqual(len(result["daily_state"]["nutrition"]["meals"]), 1)

    def test_training_day_generates_pre_and_post_guidance(self) -> None:
        fitness_logic.apply_user_context("今天晚上练臀，怎么吃？")
        state = fitness_state.get_daily_state()
        plan = fitness_logic.generate_daily_plan(fitness_state.get_profile(), state)
        self.assertEqual(plan["day_type"], "training_day")
        self.assertIn("轻碳水", plan["reply"])
        self.assertIn("练后", plan["reply"])

    def test_lapse_recovery_avoids_extreme_or_shaming_language(self) -> None:
        result = fitness_logic.generate_lapse_recovery_plan(
            fitness_state.get_profile(),
            fitness_state.get_daily_state(),
            "我今天吃爆了，不想记了"
        )
        reply = result["reply"]
        forbidden = ["不自律", "明天不吃", "惩罚性运动", "今天失败"]
        self.assertIn("不用补齐所有记录", reply)
        for term in forbidden:
            self.assertNotIn(term, reply)

    def test_weekly_review_outputs_positive_summary_and_one_focus(self) -> None:
        cycle = fitness_state.get_cycle_state()
        cycle.update({
            "workout_completed_count": 3,
            "meal_logging_days": 4,
            "over_budget_days": 1,
            "recovery_success_count": 1,
            "special_context_count": {"聚餐": 1},
            "weekly_wins": ["聚餐后第二天恢复记录"],
            "next_week_focus": "训练日下午提前安排轻量加餐"
        })
        review = fitness_logic.generate_weekly_review(fitness_state.get_profile(), cycle)
        self.assertIn("值得肯定", review["reply"])
        self.assertIn("下周先只抓一个小动作", review["reply"])
        self.assertEqual(review["next_week_focus"], "训练日下午提前安排轻量加餐")


if __name__ == "__main__":
    unittest.main()
