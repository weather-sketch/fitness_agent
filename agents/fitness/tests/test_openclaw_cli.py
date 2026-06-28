from __future__ import annotations

import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
INTEGRATIONS = ROOT / "integrations"
for path in (ROOT, TOOLS, INTEGRATIONS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import fitness_openclaw_cli  # noqa: E402
import fitness_state  # noqa: E402


class FitnessOpenClawCliTest(unittest.TestCase):
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
            sys.argv = ["fitness_openclaw_cli.py", *args]
            with contextlib.redirect_stdout(buffer):
                fitness_openclaw_cli.main()
        finally:
            sys.argv = old_argv
        return buffer.getvalue()

    def test_text_cli_runs(self) -> None:
        output = self._run_cli(
            "text",
            "--text",
            "今天晚上练臀，怎么吃？",
            "--channel",
            "wechat",
            "--sender",
            "demo_user",
            "--conversation",
            "conv_demo",
            "--date",
            "2026-06-24",
        )
        state = fitness_state.get_daily_state(user_id="wechat_demo_user", date="2026-06-24")

        self.assertIn("OpenClaw event:", output)
        self.assertIn("- handled: true", output)
        self.assertIn("- date: 2026-06-24", output)
        self.assertIn("Reply:", output)
        self.assertEqual(state["day_type"], "training_day")
        self.assertFalse(fitness_state.get_user_data_dir("default").exists())

    def test_image_cli_runs(self) -> None:
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
            "--conversation",
            "conv_demo",
            "--date",
            "2026-06-24",
            "--provider",
            "demo",
        )
        state = fitness_state.get_daily_state(user_id="wechat_demo_user", date="2026-06-24")

        self.assertIn("- handled: true", output)
        self.assertIn("meal_count_after: 1", output)
        self.assertEqual(len(state["nutrition"]["meals"]), 1)

    def test_command_cli_runs(self) -> None:
        output = self._run_cli(
            "command",
            "--text",
            "/fitness help",
            "--channel",
            "wechat",
            "--sender",
            "demo_user",
            "--conversation",
            "conv_demo",
        )

        self.assertIn("- handled: true", output)
        self.assertIn("Fitness Agent 可以帮你处理", output)


if __name__ == "__main__":
    unittest.main()
