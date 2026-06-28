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

import fitness_memory  # noqa: E402
import fitness_state  # noqa: E402
import openclaw_adapter  # noqa: E402
import run_openclaw_integration_demo  # noqa: E402
import run_showcase_demo  # noqa: E402


class FitnessOpenClawAdapterTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.old_data_dir = fitness_state.DATA_DIR
        fitness_state.DATA_DIR = Path(self.tmp.name) / "data"
        self.image = Path(self.tmp.name) / "beef_noodle_demo.jpg"
        self.image.write_text("demo image placeholder", encoding="utf-8")

    def tearDown(self) -> None:
        fitness_state.DATA_DIR = self.old_data_dir
        self.tmp.cleanup()

    def _event(self, message_type: str, text: str = "今天晚上练臀，怎么吃？", sender: str = "demo_user") -> dict:
        return {
            "event_id": "evt-test",
            "source": "openclaw",
            "channel": "wechat",
            "sender_id": sender,
            "conversation_id": "conv-test",
            "message": {"type": message_type, "text": text},
            "timestamp": "2026-06-24T20:00:00",
            "metadata": {},
        }

    def test_normalize_text_event(self) -> None:
        normalized = openclaw_adapter.normalize_openclaw_event(self._event("text"))

        self.assertEqual(normalized["message_id"], "evt-test")
        self.assertEqual(normalized["channel"], "wechat")
        self.assertEqual(normalized["sender_id"], "demo_user")
        self.assertEqual(normalized["type"], "text")
        self.assertEqual(normalized["text"], "今天晚上练臀，怎么吃？")

    def test_normalize_image_event(self) -> None:
        event = self._event("image", "午餐")
        event["message"]["image_path"] = str(self.image)
        normalized = openclaw_adapter.normalize_openclaw_event(event)

        self.assertEqual(normalized["type"], "image")
        self.assertEqual(normalized["image_path"], str(self.image))

    def test_missing_optional_fields_do_not_crash(self) -> None:
        normalized = openclaw_adapter.normalize_openclaw_event({"message": {"type": "text", "text": "hi"}})

        self.assertEqual(normalized["sender_id"], "unknown_sender")
        self.assertEqual(normalized["conversation_id"], "openclaw-conversation")

    def test_unsupported_message_type_returns_error(self) -> None:
        response = openclaw_adapter.handle_openclaw_event(self._event("audio", "voice"))

        self.assertFalse(response["ok"])
        self.assertEqual(response["error"]["code"], "unsupported_message_type")

    def test_text_fitness_event_handled(self) -> None:
        event = self._event("text")
        event["date"] = "2026-06-24"
        response = openclaw_adapter.handle_openclaw_event(event)

        self.assertTrue(response["ok"])
        self.assertTrue(response["handled"])
        self.assertFalse(response["handoff"])
        self.assertEqual(response["agent"], "fitness")
        self.assertIn("reply", response)
        self.assertIn("练前", response["reply"]["text"])
        self.assertEqual(response["state_summary"]["date"], "2026-06-24")
        state = fitness_state.get_daily_state(user_id="wechat_demo_user", date="2026-06-24")
        self.assertEqual(state["day_type"], "training_day")

    def test_image_event_writes_nutrition_meals(self) -> None:
        event = self._event("image", "午餐")
        event["message"]["image_path"] = str(self.image)
        event["date"] = "2026-06-24"
        response = openclaw_adapter.handle_openclaw_event(event, provider="demo")
        state = fitness_state.get_daily_state(user_id="wechat_demo_user", date="2026-06-24")

        self.assertTrue(response["handled"])
        self.assertEqual(len(state["nutrition"]["meals"]), 1)
        self.assertEqual(response["state_summary"]["meal_count_after"], 1)

    def test_command_help_returns_reply(self) -> None:
        response = openclaw_adapter.handle_openclaw_event(self._event("command", "/fitness help"))

        self.assertTrue(response["handled"])
        self.assertIn("Fitness Agent 可以帮你处理", response["reply"]["text"])

    def test_recall_on_command_enables_recall(self) -> None:
        response = openclaw_adapter.handle_openclaw_event(self._event("command", "/recall on"))

        self.assertTrue(response["state_changed"])
        self.assertTrue(fitness_state.get_recall_state(user_id="wechat_demo_user")["enabled"])

    def test_memory_preference_event_creates_candidate(self) -> None:
        response = openclaw_adapter.handle_openclaw_event(self._event("text", "以后练前别推荐酸奶，我会胃不舒服。"))
        candidates = fitness_memory.list_memory_candidates(user_id="wechat_demo_user")

        self.assertTrue(response["handled"])
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["key"], "avoid_yogurt_pre_workout")

    def test_non_fitness_event_handoffs_to_main_agent(self) -> None:
        response = openclaw_adapter.handle_openclaw_event(self._event("text", "帮我把明天的会议整理一下", sender="meeting_user"))

        self.assertTrue(response["ok"])
        self.assertFalse(response["handled"])
        self.assertTrue(response["handoff"])
        self.assertIsNone(response["reply"])
        self.assertEqual(response["handoff_payload"]["target"], "main_agent")
        self.assertFalse(fitness_state.get_user_data_dir("wechat_meeting_user").exists())

    def test_output_schema_contains_required_fields(self) -> None:
        response = openclaw_adapter.handle_openclaw_event(self._event("text"))

        for key in ["ok", "handled", "handoff", "agent", "reply", "state_summary", "debug"]:
            self.assertIn(key, response)

    def test_default_does_not_write_default_user(self) -> None:
        openclaw_adapter.handle_openclaw_event(self._event("text"))

        self.assertTrue(fitness_state.get_user_data_dir("wechat_demo_user").exists())
        self.assertFalse(fitness_state.get_user_data_dir("default").exists())

    def test_openclaw_demo_runs(self) -> None:
        old_data_dir = fitness_state.DATA_DIR
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                run_openclaw_integration_demo.main()
            self.assertTrue((run_openclaw_integration_demo.OPENCLAW_DATA_DIR / "users" / "wechat_demo_user").exists())
        finally:
            fitness_state.DATA_DIR = old_data_dir

    def test_showcase_openclaw_flow_runs(self) -> None:
        data_root = Path(self.tmp.name) / "showcase"
        results = run_showcase_demo.run_showcase_flow("openclaw", data_root=data_root)

        self.assertEqual(results[0]["flow_id"], "openclaw")
        self.assertIn("handoff_target: main_agent", results[0]["summary"])


if __name__ == "__main__":
    unittest.main()
