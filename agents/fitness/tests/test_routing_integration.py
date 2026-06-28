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


class FitnessRoutingIntegrationTest(unittest.TestCase):
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

    def tearDown(self) -> None:
        fitness_state.DATA_DIR = self.old_data_dir
        self.tmp.cleanup()

    def test_fitness_text_routes_to_handler(self) -> None:
        result = routing_adapter.route_fitness_message("今天晚上练臀，怎么吃？", channel="routing_test")
        state = fitness_state.get_daily_state()

        self.assertTrue(result["handled"])
        self.assertFalse(result["fallback"])
        self.assertEqual(result["intent"], "daily_plan")
        self.assertIn("今日类型：training_day", result["reply"])
        self.assertEqual(state["day_type"], "training_day")
        self.assertEqual(state["training"]["type"], "glutes")
        self.assertEqual(len(state["workouts"]), 1)

    def test_non_fitness_text_returns_fallback_without_state_write(self) -> None:
        before = copy.deepcopy(fitness_state.get_daily_state())
        result = routing_adapter.route_fitness_message("帮我整理明天的会议", channel="routing_test")
        after = fitness_state.get_daily_state()

        self.assertFalse(result["handled"])
        self.assertTrue(result["fallback"])
        self.assertEqual(result["reply"], "")
        self.assertEqual(after, before)

    def test_handler_exception_returns_fallback(self) -> None:
        with mock.patch.object(routing_adapter, "handle_fitness_message", side_effect=RuntimeError("boom")):
            result = routing_adapter.route_fitness_message("今天晚上练臀，怎么吃？")

        self.assertFalse(result["handled"])
        self.assertTrue(result["fallback"])
        self.assertEqual(result["reply"], "")

    def test_user_reply_does_not_expose_debug_json(self) -> None:
        result = routing_adapter.route_fitness_message("今天晚上练臀，怎么吃？", channel="routing_test")
        reply = result["reply"]

        self.assertNotIn("debug", reply)
        self.assertNotIn("state_changes", reply)
        self.assertNotIn("tool_chain", reply)
        self.assertNotIn("{", reply)
        self.assertNotIn("}", reply)


if __name__ == "__main__":
    unittest.main()
