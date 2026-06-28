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
import fitness_state  # noqa: E402
import run_demo  # noqa: E402


class FitnessWeeklyAggregationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.old_data_dir = fitness_state.DATA_DIR
        fitness_state.DATA_DIR = Path(self.tmp.name)

    def tearDown(self) -> None:
        fitness_state.DATA_DIR = self.old_data_dir
        self.tmp.cleanup()

    def _seed_week(self, user_id: str = "default") -> None:
        fitness_state.update_daily_state({
            "training": {"type": "glutes", "status": "completed"},
            "workouts": [{"training_type": "glutes", "status": "completed"}],
            "nutrition": {
                "meals": [{"description": "breakfast"}, {"description": "dinner"}],
                "calories_remaining": 200,
                "calorie_budget_status": "on_track",
            },
        }, user_id=user_id, date="2026-06-16")
        fitness_state.update_daily_state({
            "training": {"type": "back", "status": "completed"},
            "workouts": [{"training_type": "back", "status": "completed"}],
            "nutrition": {
                "meals": [{"description": "lunch"}],
                "calories_remaining": -100,
                "calorie_budget_status": "over",
            },
            "special_context": ["social_meal", "lapse_recovery"],
            "emotion": {"lapse_risk": "high"},
        }, user_id=user_id, date="2026-06-18")

    def test_aggregate_week_counts_workouts_and_meal_days(self) -> None:
        self._seed_week()
        result = fitness_state.aggregate_week_from_daily(week_key="2026-W25")

        self.assertEqual(result["workout_completed_count"], 2)
        self.assertEqual(result["meal_logging_days"], 2)
        self.assertEqual(result["complete_logging_days"], 1)
        self.assertEqual(result["over_budget_days"], 1)
        self.assertEqual(result["training_types"], {"glutes": 1, "back": 1})
        self.assertEqual(result["days_with_logs"], ["2026-06-16", "2026-06-18"])

    def test_aggregate_week_writes_week_key_and_current_week(self) -> None:
        self._seed_week()
        result = fitness_state.aggregate_week_from_daily(week_key="2026-W25")
        week_file = fitness_state.get_user_data_dir("default") / "cycle" / "2026-W25.json"
        current_file = fitness_state.get_user_data_dir("default") / "cycle" / "current_week.json"

        self.assertTrue(week_file.exists())
        self.assertTrue(current_file.exists())
        self.assertEqual(fitness_state.load_json(week_file)["week_key"], result["week_key"])
        self.assertEqual(fitness_state.load_json(current_file)["week_key"], result["week_key"])

    def test_weekly_review_can_use_aggregated_data(self) -> None:
        self._seed_week()
        aggregate = fitness_state.aggregate_week_from_daily(week_key="2026-W25")
        review = fitness_logic.generate_weekly_review(fitness_state.get_profile(), aggregate)

        self.assertIn("完成了 2 次训练", review["reply"])
        self.assertIn("饮食记录 2 天", review["reply"])
        self.assertIn("数据还不多", review["reply"])

    def test_weekly_aggregation_is_isolated_by_user(self) -> None:
        self._seed_week(user_id="user_a")
        fitness_state.update_daily_state({
            "nutrition": {"meals": [{"description": "only user b"}]},
        }, user_id="user_b", date="2026-06-16")

        user_a = fitness_state.aggregate_week_from_daily(user_id="user_a", week_key="2026-W25")
        user_b = fitness_state.aggregate_week_from_daily(user_id="user_b", week_key="2026-W25")

        self.assertEqual(user_a["workout_completed_count"], 2)
        self.assertEqual(user_a["meal_logging_days"], 2)
        self.assertEqual(user_b["workout_completed_count"], 0)
        self.assertEqual(user_b["meal_logging_days"], 1)

    def test_demo_data_does_not_pollute_real_data_dir(self) -> None:
        real_data_dir = Path(self.tmp.name) / "real_data"
        fitness_state.DATA_DIR = real_data_dir
        before = sorted(path.relative_to(real_data_dir) for path in real_data_dir.rglob("*")) if real_data_dir.exists() else []

        try:
            run_demo._prepare_demo_data()
        finally:
            fitness_state.DATA_DIR = real_data_dir

        after = sorted(path.relative_to(real_data_dir) for path in real_data_dir.rglob("*")) if real_data_dir.exists() else []
        self.assertEqual(after, before)

    def test_demo_weekly_seed_uses_current_week_with_multiple_days(self) -> None:
        try:
            run_demo._prepare_demo_data()
            week_key = fitness_state.get_week_key()
            week_dates = set(fitness_state.get_week_date_range(week_key))
            aggregate = fitness_state.aggregate_week_from_daily(week_key=week_key)
        finally:
            fitness_state.DATA_DIR = self.old_data_dir

        self.assertEqual(aggregate["week_key"], week_key)
        self.assertEqual(set(aggregate["days_with_logs"]) - week_dates, set())
        self.assertGreaterEqual(aggregate["workout_completed_count"], 2)
        self.assertGreaterEqual(aggregate["meal_logging_days"], 4)


if __name__ == "__main__":
    unittest.main()
