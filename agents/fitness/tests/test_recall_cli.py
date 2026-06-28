from __future__ import annotations

import json
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
import fitness_recall_cli  # noqa: E402


class FitnessRecallCliTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.old_data_dir = fitness_state.DATA_DIR
        fitness_state.DATA_DIR = Path(self.tmp.name) / "data"

    def tearDown(self) -> None:
        fitness_state.DATA_DIR = self.old_data_dir
        self.tmp.cleanup()

    def _run_cli(self, *args: str) -> dict:
        old_argv = sys.argv
        buffer = io.StringIO()
        try:
            sys.argv = ["fitness_recall_cli.py", *args]
            with contextlib.redirect_stdout(buffer):
                fitness_recall_cli.main()
        finally:
            sys.argv = old_argv
        return json.loads(buffer.getvalue())

    def test_status_defaults_to_disabled(self) -> None:
        result = self._run_cli("status", "--user", "default")

        self.assertFalse(result["enabled"])

    def test_opt_in_and_opt_out(self) -> None:
        opted_in = self._run_cli("opt-in", "--user", "default")
        opted_out = self._run_cli("opt-out", "--user", "default")

        self.assertTrue(opted_in["enabled"])
        self.assertFalse(opted_out["enabled"])

    def test_suggest_manual_type_does_not_send(self) -> None:
        result = self._run_cli("suggest", "--user", "default", "--type", "lapse_recovery_followup")

        self.assertEqual(result["recall_type"], "lapse_recovery_followup")
        self.assertFalse(result["should_send"])
        self.assertEqual(result["blocked_reason"], "manual_preview")
        self.assertIn("不用补前面的记录", result["message"])


if __name__ == "__main__":
    unittest.main()
