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

import fitness_binding_check  # noqa: E402
import fitness_state  # noqa: E402


class FitnessBindingCheckTest(unittest.TestCase):
    def test_binding_check_runs_and_reports_skill_guided_mode(self) -> None:
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            exit_code = fitness_binding_check.main()

        output = stream.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Fitness Agent Binding Check", output)
        self.assertIn("Core handler: OK", output)
        self.assertIn("Channel adapter: OK", output)
        self.assertIn("OpenClaw scaffold: OK", output)
        self.assertIn("Skill file: OK", output)
        self.assertIn("Runtime entrypoint discovered: NO", output)
        self.assertIn("Recommended binding mode: skill-guided", output)
        self.assertIn("skills/fitness-coach/SKILL.md: found", output)
        self.assertIn("agents/fitness/integrations/openclaw_adapter.py: found", output)

    def test_binding_check_does_not_write_default_user_state(self) -> None:
        old_data_dir = fitness_state.DATA_DIR
        try:
            with tempfile.TemporaryDirectory() as tmp:
                fitness_state.DATA_DIR = Path(tmp) / "data"
                with contextlib.redirect_stdout(io.StringIO()):
                    fitness_binding_check.main()
                self.assertFalse(fitness_state.get_user_data_dir("default").exists())
        finally:
            fitness_state.DATA_DIR = old_data_dir


if __name__ == "__main__":
    unittest.main()
