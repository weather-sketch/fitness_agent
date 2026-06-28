from __future__ import annotations

import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
for path in (ROOT, TOOLS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import fitness_channel_cli  # noqa: E402
import fitness_state  # noqa: E402


class FitnessChannelCliTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.old_data_dir = fitness_state.DATA_DIR
        fitness_state.DATA_DIR = Path(self.tmp.name) / "data"
        self.image = Path(self.tmp.name) / "beef_noodle_demo.jpg"
        self.image.write_text("demo image placeholder", encoding="utf-8")

    def tearDown(self) -> None:
        fitness_state.DATA_DIR = self.old_data_dir
        self.tmp.cleanup()

    def _run_cli(self, *args: str) -> str:
        old_argv = sys.argv
        buffer = io.StringIO()
        try:
            sys.argv = ["fitness_channel_cli.py", *args]
            with contextlib.redirect_stdout(buffer):
                fitness_channel_cli.main()
        finally:
            sys.argv = old_argv
        return buffer.getvalue()

    def test_text_cli_routes_fitness_message(self) -> None:
        output = self._run_cli(
            "text",
            "--text",
            "今天晚上练臀，怎么吃？",
            "--channel",
            "wechat",
            "--sender",
            "demo_user",
        )

        self.assertIn("Handled: True", output)
        self.assertIn("Handoff: False", output)
        self.assertIn("Intent: daily_plan", output)
        self.assertIn("User ID: wechat_demo_user", output)
        self.assertFalse(fitness_state.get_user_data_dir("default").exists())

    def test_image_cli_logs_meal(self) -> None:
        output = self._run_cli(
            "image",
            "--image",
            str(self.image),
            "--text",
            "午餐",
            "--channel",
            "wechat",
            "--sender",
            "demo_user",
            "--date",
            "2026-06-24",
            "--provider",
            "demo",
        )
        state = fitness_state.get_daily_state(user_id="wechat_demo_user", date="2026-06-24")

        self.assertIn("Intent: food_photo_log", output)
        self.assertIn("meal_count_after: 1", output)
        self.assertEqual(len(state["nutrition"]["meals"]), 1)

    def test_command_cli_help(self) -> None:
        output = self._run_cli(
            "command",
            "--text",
            "/fitness help",
            "--channel",
            "wechat",
            "--sender",
            "demo_user",
        )

        self.assertIn("Intent: fitness_help", output)
        self.assertIn("Fitness Agent 可以帮你处理", output)


if __name__ == "__main__":
    unittest.main()
