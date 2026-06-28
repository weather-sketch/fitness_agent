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
import fitness_wechat_routing_check  # noqa: E402


class FitnessWeChatRoutingCheckTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.old_data_dir = fitness_state.DATA_DIR
        fitness_state.DATA_DIR = Path(self.tmp.name) / "data"

    def tearDown(self) -> None:
        fitness_state.DATA_DIR = self.old_data_dir
        self.tmp.cleanup()

    def _responses(self) -> dict[str, dict]:
        results = fitness_wechat_routing_check.run_cases()
        return {result["input"]: result["response"] for result in results}

    def test_wechat_routing_check_script_runs(self) -> None:
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            exit_code = fitness_wechat_routing_check.main()

        output = stream.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Fitness WeChat Routing Check", output)
        self.assertIn("Skill file: OK", output)
        self.assertIn("Channel adapter: OK", output)
        self.assertIn("OpenClaw scaffold: OK", output)
        self.assertIn("Recommended real WeChat test", output)

    def test_fitness_text_case_handled(self) -> None:
        response = self._responses()["今天晚上练臀，怎么吃？"]

        self.assertTrue(response["handled"])
        self.assertFalse(response["handoff"])

    def test_lapse_recovery_case_handled(self) -> None:
        response = self._responses()["我今天吃爆了，不想记了"]

        self.assertTrue(response["handled"])
        self.assertFalse(response["handoff"])

    def test_memory_preference_case_handled(self) -> None:
        response = self._responses()["以后练前别推荐酸奶，我会胃不舒服"]

        self.assertTrue(response["handled"])
        self.assertFalse(response["handoff"])

    def test_non_fitness_case_handoffs(self) -> None:
        response = self._responses()["帮我整理明天会议"]

        self.assertFalse(response["handled"])
        self.assertTrue(response["handoff"])

    def test_wechat_routing_check_does_not_write_default_user(self) -> None:
        fitness_wechat_routing_check.run_cases()

        self.assertFalse(fitness_state.get_user_data_dir("default").exists())


if __name__ == "__main__":
    unittest.main()
