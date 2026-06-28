from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
for path in (ROOT, TOOLS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import fitness_memory  # noqa: E402
import fitness_memory_cli  # noqa: E402
import fitness_state  # noqa: E402


class FitnessMemoryCliTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.old_data_dir = fitness_state.DATA_DIR
        fitness_state.DATA_DIR = Path(self.tmp.name) / "data"

    def tearDown(self) -> None:
        fitness_state.DATA_DIR = self.old_data_dir
        self.tmp.cleanup()

    def _run_cli(self, *args: str):
        old_argv = sys.argv
        buffer = io.StringIO()
        try:
            sys.argv = ["fitness_memory_cli.py", *args]
            with contextlib.redirect_stdout(buffer):
                fitness_memory_cli.main()
        finally:
            sys.argv = old_argv
        return json.loads(buffer.getvalue())

    def test_active_command_outputs_active_preferences(self) -> None:
        result = self._run_cli("active", "--user", "default")

        self.assertEqual(result["food_avoidance"], [])

    def test_approve_command_writes_active_preference(self) -> None:
        candidate = fitness_memory.extract_memory_candidates("以后练前别推荐酸奶，我会胃不舒服。")[0]
        fitness_state.add_memory_candidate(candidate, user_id="default")

        reviewed = self._run_cli("approve", "--user", "default", "--candidate-id", candidate["candidate_id"])
        active = self._run_cli("active", "--user", "default")

        self.assertEqual(reviewed["status"], "approved")
        self.assertEqual(active["food_avoidance"][0]["key"], "avoid_yogurt_pre_workout")


if __name__ == "__main__":
    unittest.main()
