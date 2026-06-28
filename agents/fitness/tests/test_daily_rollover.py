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

import fitness_state  # noqa: E402


class FitnessDailyRolloverTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.old_data_dir = fitness_state.DATA_DIR
        fitness_state.DATA_DIR = Path(self.tmp.name)

    def tearDown(self) -> None:
        fitness_state.DATA_DIR = self.old_data_dir
        self.tmp.cleanup()

    def test_week_key_and_range_use_iso_week(self) -> None:
        self.assertEqual(fitness_state.get_week_key("2026-06-20"), "2026-W25")
        self.assertEqual(fitness_state.get_week_date_range("2026-W25"), [
            "2026-06-15",
            "2026-06-16",
            "2026-06-17",
            "2026-06-18",
            "2026-06-19",
            "2026-06-20",
            "2026-06-21",
        ])

    def test_daily_state_is_isolated_by_date(self) -> None:
        fitness_state.append_meal_log({"description": "day one"}, user_id="default", date="2026-06-20")
        fitness_state.append_workout_log({"description": "day two"}, user_id="default", date="2026-06-21")

        day_one = fitness_state.get_daily_state(date="2026-06-20")
        day_two = fitness_state.get_daily_state(date="2026-06-21")

        self.assertEqual(len(day_one["nutrition"]["meals"]), 1)
        self.assertEqual(len(day_one["workouts"]), 0)
        self.assertEqual(len(day_two["nutrition"]["meals"]), 0)
        self.assertEqual(len(day_two["workouts"]), 1)

    def test_ensure_daily_state_does_not_overwrite_existing_file(self) -> None:
        fitness_state.update_daily_state({"day_type": "training_day"}, date="2026-06-20")
        ensured = fitness_state.ensure_daily_state(date="2026-06-20")

        self.assertEqual(ensured["day_type"], "training_day")

    def test_rollover_daily_state_does_not_inherit_logs(self) -> None:
        fitness_state.append_meal_log({"description": "old meal"}, date="2026-06-20")
        fitness_state.append_workout_log({"description": "old workout"}, date="2026-06-20")
        rolled = fitness_state.rollover_daily_state(from_date="2026-06-20", to_date="2026-06-21")

        self.assertEqual(rolled["date"], "2026-06-21")
        self.assertEqual(rolled["nutrition"]["meals"], [])
        self.assertEqual(rolled["workouts"], [])
        self.assertEqual(rolled["previous_day_status"]["date"], "2026-06-20")

    def test_rollover_daily_state_does_not_overwrite_existing_file(self) -> None:
        fitness_state.update_daily_state({"day_type": "rest_day"}, date="2026-06-21")
        rolled = fitness_state.rollover_daily_state(from_date="2026-06-20", to_date="2026-06-21")

        self.assertEqual(rolled["day_type"], "rest_day")


if __name__ == "__main__":
    unittest.main()
