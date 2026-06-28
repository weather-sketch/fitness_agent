from __future__ import annotations

import io
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
for path in (ROOT, TOOLS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import fitness_scheduler_cli  # noqa: E402
import fitness_state  # noqa: E402


class FitnessSchedulerCliTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.old_data_dir = fitness_state.DATA_DIR
        fitness_state.DATA_DIR = Path(self.tmp.name) / "data"

    def tearDown(self) -> None:
        fitness_state.DATA_DIR = self.old_data_dir
        self.tmp.cleanup()

    def _main(self, *args: str) -> tuple[int, str]:
        buffer = io.StringIO()
        with mock.patch.object(sys, "argv", ["fitness_scheduler_cli.py", *args]), redirect_stdout(buffer):
            code = fitness_scheduler_cli.main()
        return code, buffer.getvalue()

    def test_enable_real_send_requires_confirm(self) -> None:
        code, output = self._main("enable-real-send", "--user", "cli_scheduler_user")

        self.assertEqual(code, 2)
        self.assertIn("--confirm", output)

    def test_configure_and_show_runs(self) -> None:
        code, _ = self._main(
            "configure",
            "--user",
            "cli_scheduler_user",
            "--enable",
            "--hours",
            "9,18,21",
        )
        show_code, show_output = self._main("show", "--user", "cli_scheduler_user")

        self.assertEqual(code, 0)
        self.assertEqual(show_code, 0)
        self.assertIn("Fitness Scheduler Config", show_output)
        self.assertIn("preferred_hours: [9, 18, 21]", show_output)


if __name__ == "__main__":
    unittest.main()
