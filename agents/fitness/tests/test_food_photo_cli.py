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

import fitness_state  # noqa: E402
import fitness_vision_cli  # noqa: E402


class FitnessFoodPhotoCliTest(unittest.TestCase):
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
            sys.argv = ["fitness_vision_cli.py", *args]
            with contextlib.redirect_stdout(buffer):
                fitness_vision_cli.main()
        finally:
            sys.argv = old_argv
        return buffer.getvalue()

    def test_analyze_cli_does_not_write_state(self) -> None:
        output = self._run_cli("analyze", "--image", str(self.image))

        self.assertIn("Detected food: 牛肉面", output)
        self.assertIn("600-850 kcal", output)
        self.assertFalse(fitness_state.get_user_data_dir("default").exists())

    def test_log_cli_updates_meal_logs(self) -> None:
        output = self._run_cli("log", "--image", str(self.image), "--user", "default", "--note", "午餐")
        daily = fitness_state.get_daily_state(user_id="default")

        self.assertIn("Logged source: image", output)
        self.assertIn("Meal log field: nutrition.meals", output)
        self.assertEqual(len(daily["nutrition"]["meals"]), 1)
        self.assertEqual(daily["nutrition"]["meals"][0]["source"], "image")

    def test_log_cli_uses_explicit_date(self) -> None:
        output = self._run_cli(
            "log",
            "--image",
            str(self.image),
            "--user",
            "dated_user",
            "--note",
            "午餐",
            "--date",
            "2026-06-24",
        )
        logged_day = fitness_state.get_daily_state(user_id="dated_user", date="2026-06-24")
        next_day = fitness_state.get_user_data_dir("dated_user") / "daily" / "2026-06-25.json"

        self.assertIn("Logged date: 2026-06-24", output)
        self.assertIn("daily/2026-06-24.json", output)
        self.assertIn("Meal log field: nutrition.meals", output)
        self.assertEqual(len(logged_day["nutrition"]["meals"]), 1)
        self.assertEqual(logged_day["nutrition"]["meals"][0]["description"], "牛肉面（午餐）")
        self.assertFalse(next_day.exists())


if __name__ == "__main__":
    unittest.main()
