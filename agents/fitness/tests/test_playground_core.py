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
import playground  # noqa: E402
import run_showcase_demo  # noqa: E402


class FitnessPlaygroundCoreTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.old_data_dir = fitness_state.DATA_DIR
        self.data_root = Path(self.tmp.name) / "playground"
        run_showcase_demo.reset_demo_user_state(self.data_root)

    def tearDown(self) -> None:
        fitness_state.DATA_DIR = self.old_data_dir
        self.tmp.cleanup()

    def test_menu_actions_are_callable(self) -> None:
        for choice in ["1", "2", "3", "4", "5", "6", "8", "9"]:
            with self.subTest(choice=choice):
                action = playground.run_playground_action(choice, user_id="pg", data_root=self.data_root)
                self.assertEqual(action["kind"], "flow")
                self.assertTrue(action["result"]["agent_reply"])

    def test_free_input_uses_existing_handler(self) -> None:
        action = playground.run_playground_action(
            "7",
            user_id="pg",
            free_text="今天晚上练臀，怎么吃？",
            data_root=self.data_root,
        )

        self.assertEqual(action["kind"], "free_input")
        self.assertTrue(action["result"]["handled"])
        self.assertEqual(action["result"]["intent"], "daily_plan")

    def test_non_fitness_free_input_falls_back(self) -> None:
        action = playground.run_playground_action(
            "7",
            user_id="pg",
            free_text="帮我整理明天的会议",
            data_root=self.data_root,
        )

        self.assertEqual(action["kind"], "free_input")
        self.assertFalse(action["result"]["handled"])
        self.assertEqual(action["result"]["intent"], "unknown")

    def test_invalid_and_exit_choices(self) -> None:
        invalid = playground.run_playground_action("bad", data_root=self.data_root)
        exit_action = playground.run_playground_action("0", data_root=self.data_root)

        self.assertEqual(invalid["kind"], "message")
        self.assertEqual(exit_action["kind"], "exit")

    def test_playground_uses_demo_state(self) -> None:
        playground.run_playground_action("1", user_id="pg", data_root=self.data_root)

        self.assertTrue((self.data_root / "users" / "pg_text").exists())
        self.assertEqual(fitness_state.DATA_DIR, self.data_root)


if __name__ == "__main__":
    unittest.main()
