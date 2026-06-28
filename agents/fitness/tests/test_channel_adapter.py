from __future__ import annotations

import sys
import tempfile
import unittest
import contextlib
import io
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
for path in (ROOT, TOOLS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import channel_adapter  # noqa: E402
import fitness_memory  # noqa: E402
import fitness_state  # noqa: E402
import run_channel_demo  # noqa: E402
import run_showcase_demo  # noqa: E402


class FitnessChannelAdapterTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.old_data_dir = fitness_state.DATA_DIR
        fitness_state.DATA_DIR = Path(self.tmp.name) / "data"
        self.image = Path(self.tmp.name) / "beef_noodle_demo.jpg"
        self.image.write_text("demo image placeholder", encoding="utf-8")

    def tearDown(self) -> None:
        fitness_state.DATA_DIR = self.old_data_dir
        self.tmp.cleanup()

    def _message(self, message_type: str, text: str = "", sender: str = "demo_user") -> dict:
        return {
            "message_id": "msg-test",
            "channel": "wechat",
            "sender_id": sender,
            "conversation_id": "conv-test",
            "type": message_type,
            "text": text,
            "metadata": {},
        }

    def test_resolve_channel_user_id_is_stable_and_safe(self) -> None:
        self.assertEqual(
            channel_adapter.resolve_channel_user_id("wechat", "o123abc"),
            "wechat_o123abc",
        )
        self.assertEqual(
            channel_adapter.resolve_channel_user_id("we/chat", "a b:c"),
            "we_chat_a_b_c",
        )

    def test_explicit_user_id_wins(self) -> None:
        response = channel_adapter.handle_channel_message(
            self._message("text", "今天晚上练臀，怎么吃？"),
            user_id="explicit_user",
        )

        self.assertEqual(response["user_id"], "explicit_user")
        self.assertTrue(response["handled"])

    def test_text_fitness_message_is_handled(self) -> None:
        response = channel_adapter.handle_channel_message(
            self._message("text", "今天晚上练臀，怎么吃？"),
            date="2026-06-24",
        )

        self.assertTrue(response["handled"])
        self.assertFalse(response["handoff"])
        self.assertEqual(response["intent"], "daily_plan")
        self.assertIn("练前", response["reply"])
        self.assertEqual(response["user_id"], "wechat_demo_user")
        self.assertEqual(response["state_summary"]["date"], "2026-06-24")
        state = fitness_state.get_daily_state(user_id="wechat_demo_user", date="2026-06-24")
        self.assertEqual(state["day_type"], "training_day")

    def test_non_fitness_message_handoffs_without_state(self) -> None:
        response = channel_adapter.handle_channel_message(
            self._message("text", "帮我把明天的会议整理一下", sender="meeting_user"),
        )

        self.assertFalse(response["handled"])
        self.assertTrue(response["handoff"])
        self.assertEqual(response["intent"], "unknown")
        self.assertFalse(fitness_state.get_user_data_dir("wechat_meeting_user").exists())

    def test_image_message_writes_nutrition_meals(self) -> None:
        message = self._message("image", "午餐")
        message["image_path"] = str(self.image)

        response = channel_adapter.handle_channel_message(
            message,
            date="2026-06-24",
            provider="demo",
        )
        state = fitness_state.get_daily_state(user_id="wechat_demo_user", date="2026-06-24")
        meals = state["nutrition"]["meals"]

        self.assertTrue(response["handled"])
        self.assertEqual(response["intent"], "food_photo_log")
        self.assertEqual(len(meals), 1)
        self.assertEqual(meals[0]["source"], "image")
        self.assertEqual(response["state_summary"]["meal_count_after"], 1)
        self.assertEqual(response["state_summary"]["provider"], "demo")

    def test_missing_image_does_not_crash(self) -> None:
        message = self._message("image", "午餐")
        message["image_path"] = str(Path(self.tmp.name) / "missing.jpg")

        response = channel_adapter.handle_channel_message(message, date="2026-06-24")

        self.assertTrue(response["handled"])
        self.assertFalse(response["handoff"])
        self.assertEqual(response["intent"], "food_photo_log_failed")
        self.assertFalse(response["state_changed"])
        self.assertIn("没法读取", response["reply"])

    def test_fitness_help_command(self) -> None:
        response = channel_adapter.handle_channel_message(self._message("command", "/fitness help"))

        self.assertTrue(response["handled"])
        self.assertEqual(response["intent"], "fitness_help")
        self.assertIn("Fitness Agent 可以帮你处理", response["reply"])

    def test_recall_commands_update_state(self) -> None:
        on = channel_adapter.handle_channel_message(self._message("command", "/recall on"))
        status = channel_adapter.handle_channel_message(self._message("command", "/recall status"))
        off = channel_adapter.handle_channel_message(self._message("command", "/recall off"))

        self.assertEqual(on["intent"], "recall_opt_in")
        self.assertIn("已开启", status["reply"])
        self.assertEqual(status["intent"], "recall_status")
        self.assertEqual(off["intent"], "recall_opt_out")
        self.assertFalse(fitness_state.get_recall_state(user_id="wechat_demo_user")["enabled"])

    def test_memory_candidates_command_returns_summary(self) -> None:
        channel_adapter.handle_channel_message(self._message("text", "以后练前别推荐酸奶，我会胃不舒服。"))
        response = channel_adapter.handle_channel_message(self._message("command", "/memory candidates"))

        self.assertEqual(response["intent"], "memory_candidates")
        self.assertIn("avoid_yogurt_pre_workout", response["reply"])
        self.assertEqual(len(fitness_memory.list_memory_candidates(user_id="wechat_demo_user")), 1)

    def test_channel_adapter_does_not_write_default_user_by_default(self) -> None:
        channel_adapter.handle_channel_message(self._message("text", "今天晚上练臀，怎么吃？"))

        self.assertTrue(fitness_state.get_user_data_dir("wechat_demo_user").exists())
        self.assertFalse(fitness_state.get_user_data_dir("default").exists())

    def test_channel_demo_runs(self) -> None:
        old_data_dir = fitness_state.DATA_DIR
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                run_channel_demo.main()
            self.assertTrue((run_channel_demo.CHANNEL_DATA_DIR / "users" / "wechat_demo_user").exists())
        finally:
            fitness_state.DATA_DIR = old_data_dir

    def test_showcase_channel_flow_runs(self) -> None:
        data_root = Path(self.tmp.name) / "showcase"
        results = run_showcase_demo.run_showcase_flow("channel", data_root=data_root)

        self.assertEqual(results[0]["flow_id"], "channel")
        self.assertIn("fallback_handoff: true", results[0]["summary"])


if __name__ == "__main__":
    unittest.main()
