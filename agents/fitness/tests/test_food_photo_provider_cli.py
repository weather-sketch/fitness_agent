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


class FitnessFoodPhotoProviderCliTest(unittest.TestCase):
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

    def test_analyze_demo_provider_does_not_write_state(self) -> None:
        output = self._run_cli("analyze", "--image", str(self.image), "--provider", "demo")

        self.assertIn("Provider: demo", output)
        self.assertIn("Provider status: ok", output)
        self.assertIn("Fallback used: false", output)
        self.assertIn("Detected food: 牛肉面", output)
        self.assertFalse(fitness_state.get_user_data_dir("default").exists())

    def test_analyze_manual_provider_does_not_write_state(self) -> None:
        output = self._run_cli(
            "analyze",
            "--image",
            str(self.image),
            "--provider",
            "manual",
            "--manual-food",
            "牛肉面",
            "--manual-category",
            "noodle",
            "--manual-confidence",
            "medium",
        )

        self.assertIn("Provider: manual", output)
        self.assertIn("Provider status: ok", output)
        self.assertIn("Detected food: 牛肉面", output)
        self.assertFalse(fitness_state.get_user_data_dir("default").exists())

    def test_log_manual_provider_supports_date_and_writes_meal(self) -> None:
        output = self._run_cli(
            "log",
            "--image",
            str(self.image),
            "--user",
            "provider_user",
            "--date",
            "2026-06-24",
            "--provider",
            "manual",
            "--manual-food",
            "牛肉面",
            "--manual-category",
            "noodle",
            "--manual-confidence",
            "medium",
            "--note",
            "午餐",
        )
        daily = fitness_state.get_daily_state(user_id="provider_user", date="2026-06-24")
        meals = daily["nutrition"]["meals"]

        self.assertIn("Provider: manual", output)
        self.assertIn("Provider status: ok", output)
        self.assertIn("Logged date: 2026-06-24", output)
        self.assertIn("Meal count after: 1", output)
        self.assertEqual(len(meals), 1)
        self.assertEqual(meals[0]["source"], "image")
        self.assertEqual(meals[0]["logged_calories"], 725)


if __name__ == "__main__":
    unittest.main()
