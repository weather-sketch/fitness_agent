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

import fitness_scheduler_install  # noqa: E402


class FitnessSchedulerInstallTest(unittest.TestCase):
    def test_launchd_plist_print_contains_worker_command(self) -> None:
        text = fitness_scheduler_install.launchd_plist_text(user_id="wechat_self_test", time_value="21:00")

        self.assertIn("fitness_recall_worker.py scheduled-run --user wechat_self_test", text)
        self.assertIn("<key>StartCalendarInterval</key>", text)

    def test_cron_line_print_contains_log_redirect(self) -> None:
        line = fitness_scheduler_install.cron_line(user_id="wechat_self_test", time_value="21:00")

        self.assertTrue(line.startswith("0 21 * * *"))
        self.assertIn("fitness_recall_worker.py scheduled-run --user wechat_self_test", line)
        self.assertIn("logs/scheduler/wechat_self_test.log", line)

    def test_write_launchd_default_is_dry_run_and_does_not_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fake_home = Path(tmp)
            buffer = io.StringIO()
            with (
                mock.patch.object(Path, "home", return_value=fake_home),
                mock.patch.object(sys, "argv", [
                    "fitness_scheduler_install.py",
                    "write-launchd",
                    "--user",
                    "wechat_self_test",
                    "--time",
                    "21:00",
                    "--label",
                    "com.openclaw.fitness.test",
                ]),
                redirect_stdout(buffer),
            ):
                code = fitness_scheduler_install.main()

            self.assertEqual(code, 0)
            self.assertIn("dry-run", buffer.getvalue())
            self.assertFalse((fake_home / "Library" / "LaunchAgents" / "com.openclaw.fitness.test.plist").exists())

    def test_write_launchd_requires_write_and_confirm_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fake_home = Path(tmp)
            buffer = io.StringIO()
            with (
                mock.patch.object(Path, "home", return_value=fake_home),
                mock.patch.object(sys, "argv", [
                    "fitness_scheduler_install.py",
                    "write-launchd",
                    "--user",
                    "wechat_self_test",
                    "--time",
                    "21:00",
                    "--label",
                    "com.openclaw.fitness.test",
                    "--write",
                    "--confirm-write",
                ]),
                redirect_stdout(buffer),
            ):
                code = fitness_scheduler_install.main()

            self.assertEqual(code, 0)
            self.assertTrue((fake_home / "Library" / "LaunchAgents" / "com.openclaw.fitness.test.plist").exists())


if __name__ == "__main__":
    unittest.main()
