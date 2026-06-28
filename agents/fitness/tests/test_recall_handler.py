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
from handler import handle_fitness_message  # noqa: E402


class FitnessRecallHandlerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.old_data_dir = fitness_state.DATA_DIR
        fitness_state.DATA_DIR = Path(self.tmp.name) / "data"

    def tearDown(self) -> None:
        fitness_state.DATA_DIR = self.old_data_dir
        self.tmp.cleanup()

    def test_explicit_opt_in_enables_recall(self) -> None:
        result = handle_fitness_message("以后可以提醒我记录训练和饮食", user_id="default")
        state = fitness_state.get_recall_state(user_id="default")

        self.assertTrue(result["handled"])
        self.assertEqual(result["intent"], "recall_opt_in")
        self.assertTrue(state["enabled"])
        self.assertIn("不会主动推送", result["reply"])
        self.assertNotIn("{", result["reply"])

    def test_explicit_opt_out_disables_recall(self) -> None:
        handle_fitness_message("以后可以提醒我记录训练和饮食", user_id="default")
        result = handle_fitness_message("别提醒我，不要打扰我", user_id="default")
        state = fitness_state.get_recall_state(user_id="default")

        self.assertTrue(result["handled"])
        self.assertEqual(result["intent"], "recall_opt_out")
        self.assertFalse(state["enabled"])
        self.assertIn("关闭", result["reply"])

    def test_recall_suggestion_does_not_enable_recall(self) -> None:
        today = "2026-06-22"
        fitness_state.update_daily_state({
            "day_type": "training_day",
            "training": {"planned": True, "time": "evening", "status": "planned"},
            "nutrition": {"meals": []},
        }, user_id="default", date=today)

        result = handle_fitness_message("你会怎么提醒我？", user_id="default")
        state = fitness_state.get_recall_state(user_id="default")

        self.assertTrue(result["handled"])
        self.assertEqual(result["intent"], "recall_suggestion")
        self.assertFalse(state["enabled"])
        self.assertNotIn("debug", result["reply"])

    def test_plain_fitness_message_does_not_enable_recall(self) -> None:
        result = handle_fitness_message("今天晚上练臀，怎么吃？", user_id="default")
        state = fitness_state.get_recall_state(user_id="default")

        self.assertTrue(result["handled"])
        self.assertFalse(state["enabled"])

    def test_non_fitness_fallback_does_not_write_recall_state(self) -> None:
        result = handle_fitness_message("帮我整理明天的会议", user_id="fallback_user")

        self.assertFalse(result["handled"])
        self.assertFalse(fitness_state.get_user_data_dir("fallback_user").exists())


if __name__ == "__main__":
    unittest.main()
