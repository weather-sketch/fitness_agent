from __future__ import annotations

import copy
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
for path in (ROOT, TOOLS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import fitness_logic  # noqa: E402
import fitness_state  # noqa: E402
import routing_adapter  # noqa: E402
import run_demo  # noqa: E402
from handler import handle_fitness_message  # noqa: E402


class FitnessUserStateIsolationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.old_data_dir = fitness_state.DATA_DIR
        fitness_state.DATA_DIR = Path(self.tmp.name)
        fitness_logic.get_daily_state = fitness_state.get_daily_state
        fitness_logic.get_profile = fitness_state.get_profile
        fitness_logic.update_daily_state = fitness_state.update_daily_state
        fitness_logic.append_meal_log = fitness_state.append_meal_log
        fitness_logic.append_workout_log = fitness_state.append_workout_log

    def tearDown(self) -> None:
        fitness_state.DATA_DIR = self.old_data_dir
        self.tmp.cleanup()

    def test_user_meal_and_workout_logs_are_isolated(self) -> None:
        meal = handle_fitness_message("中午吃了一碗牛肉面", user_id="user_a", channel="local")
        workout = handle_fitness_message("今天晚上练臀，怎么吃？", user_id="user_b", channel="local")

        user_a = fitness_state.get_daily_state(user_id="user_a")
        user_b = fitness_state.get_daily_state(user_id="user_b")

        self.assertTrue(meal["handled"])
        self.assertTrue(workout["handled"])
        self.assertEqual(len(user_a["nutrition"]["meals"]), 1)
        self.assertEqual(len(user_a["workouts"]), 0)
        self.assertEqual(len(user_b["nutrition"]["meals"]), 0)
        self.assertEqual(len(user_b["workouts"]), 1)
        self.assertEqual(user_b["training"]["type"], "glutes")

    def test_same_user_daily_state_is_isolated_by_date(self) -> None:
        fitness_state.append_meal_log({"description": "day one", "logged_calories": 100}, user_id="user_a", date="2026-06-20")
        fitness_state.append_workout_log({"description": "day two", "training_type": "glutes"}, user_id="user_a", date="2026-06-21")

        day_one = fitness_state.get_daily_state(user_id="user_a", date="2026-06-20")
        day_two = fitness_state.get_daily_state(user_id="user_a", date="2026-06-21")

        self.assertEqual(len(day_one["nutrition"]["meals"]), 1)
        self.assertEqual(len(day_one["workouts"]), 0)
        self.assertEqual(len(day_two["nutrition"]["meals"]), 0)
        self.assertEqual(len(day_two["workouts"]), 1)

    def test_handled_false_does_not_create_user_state(self) -> None:
        user_dir = fitness_state.get_user_data_dir("non_fitness_user")
        result = handle_fitness_message("帮我整理明天的会议", user_id="non_fitness_user", channel="webchat")

        self.assertFalse(result["handled"])
        self.assertFalse(user_dir.exists())

    def test_routing_adapter_passes_user_id_and_channel(self) -> None:
        with mock.patch.object(routing_adapter, "handle_fitness_message", return_value={
            "handled": False,
            "intent": "unknown",
            "reply": "",
        }) as mocked:
            result = routing_adapter.route_fitness_message({
                "text": "帮我整理明天的会议",
                "user_id": "weixin_user_1",
                "channel": "weixin",
            })

        mocked.assert_called_once_with("帮我整理明天的会议", user_id="weixin_user_1", channel="weixin")
        self.assertEqual(result["user_id"], "weixin_user_1")
        self.assertEqual(result["channel"], "weixin")

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
        self.assertTrue((run_demo.DEMO_DATA_DIR / "users" / "default").exists())


if __name__ == "__main__":
    unittest.main()
