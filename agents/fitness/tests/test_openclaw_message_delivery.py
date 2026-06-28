from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
for path in (ROOT, TOOLS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import fitness_delivery  # noqa: E402
import fitness_delivery_config  # noqa: E402
import fitness_state  # noqa: E402


class FitnessOpenClawMessageDeliveryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.old_data_dir = fitness_state.DATA_DIR
        fitness_state.DATA_DIR = Path(self.tmp.name) / "data"
        self.user_id = "openclaw_delivery_user"

    def tearDown(self) -> None:
        fitness_state.DATA_DIR = self.old_data_dir
        self.tmp.cleanup()

    def _item(self) -> dict:
        return {
            "user_id": self.user_id,
            "delivery_channel": "wechat",
            "delivery_mode": "openclaw_message",
            "text": "dry run test",
            "status": "pending",
        }

    def _configure(self, *, enabled: bool = True, allow_real_send: bool = False) -> None:
        fitness_delivery_config.configure_wechat_delivery(
            user_id=self.user_id,
            target="target-user@im.wechat",
            account_id="demo-account-id",
            enabled=enabled,
            allow_real_send=allow_real_send,
        )

    def test_build_openclaw_message_command_includes_required_args(self) -> None:
        command = fitness_delivery.build_openclaw_message_command(
            target="target-user@im.wechat",
            account_id="demo-account-id",
            text="hello",
            dry_run=True,
        )

        self.assertIn("--channel", command)
        self.assertIn("openclaw-weixin", command)
        self.assertIn("--target", command)
        self.assertIn("target-user@im.wechat", command)
        self.assertIn("--message", command)
        self.assertIn("hello", command)
        self.assertIn("--dry-run", command)
        self.assertIn("--json", command)
        self.assertIsInstance(command, list)

    def test_build_openclaw_message_command_preserves_mixed_case_target(self) -> None:
        mixed_case = "DemoUserAbC123@im.wechat"

        command = fitness_delivery.build_openclaw_message_command(
            target=mixed_case,
            account_id="demo-account-id",
            text="hello",
            dry_run=True,
        )

        self.assertEqual(command[command.index("--target") + 1], mixed_case)
        self.assertNotEqual(command[command.index("--target") + 1], mixed_case.lower())

    def test_send_via_openclaw_message_dry_run_defaults_true_and_no_shell(self) -> None:
        completed = subprocess.CompletedProcess(["openclaw"], 0, stdout="{}", stderr="")
        with mock.patch("fitness_delivery.subprocess.run", return_value=completed) as mocked:
            result = fitness_delivery.send_via_openclaw_message(
                target="target-user@im.wechat",
                account_id="demo-account-id",
                text="hello",
            )

        mocked.assert_called_once()
        self.assertFalse(mocked.call_args.kwargs.get("shell", False))
        self.assertTrue(result["dry_run"])
        self.assertFalse(result["delivered"])
        self.assertEqual(result["reason"], "dry_run_no_send")

    def test_real_send_requires_send_and_confirm(self) -> None:
        with mock.patch("fitness_delivery.subprocess.run") as mocked:
            result = fitness_delivery.send_via_openclaw_message(
                target="target-user@im.wechat",
                account_id="demo-account-id",
                text="hello",
                dry_run=False,
                send_enabled=True,
                confirm_send=False,
            )

        mocked.assert_not_called()
        self.assertEqual(result["reason"], "real_send_not_confirmed")

    def test_missing_config_prevents_delivery(self) -> None:
        with mock.patch("fitness_delivery.subprocess.run") as mocked:
            result = fitness_delivery.deliver_outbox_item(self._item(), mode="openclaw_message")

        mocked.assert_not_called()
        self.assertEqual(result["reason"], "config_missing")

    def test_disabled_config_prevents_delivery(self) -> None:
        self._configure(enabled=False)
        with mock.patch("fitness_delivery.subprocess.run") as mocked:
            result = fitness_delivery.deliver_outbox_item(self._item(), mode="openclaw_message")

        mocked.assert_not_called()
        self.assertEqual(result["reason"], "config_disabled")

    def test_allow_real_send_false_prevents_real_delivery(self) -> None:
        self._configure(enabled=True, allow_real_send=False)
        with mock.patch("fitness_delivery.subprocess.run") as mocked:
            result = fitness_delivery.deliver_outbox_item(
                self._item(),
                mode="openclaw_message",
                dry_run=False,
                send_enabled=True,
                confirm_send=True,
            )

        mocked.assert_not_called()
        self.assertEqual(result["reason"], "real_send_not_allowed")

    def test_target_and_account_are_masked_in_preview(self) -> None:
        self._configure()
        completed = subprocess.CompletedProcess(["openclaw"], 0, stdout="{}", stderr="")
        with mock.patch("fitness_delivery.subprocess.run", return_value=completed):
            result = fitness_delivery.deliver_outbox_item(self._item(), mode="openclaw_message")

        preview = result["command_preview"]
        self.assertIn("***@im.wechat", preview)
        self.assertNotIn("target-user@im.wechat", preview)
        self.assertNotIn("demo-account-id", preview)
        self.assertNotIn("dry run test", preview)

    def test_future_openclaw_old_mode_remains_unavailable(self) -> None:
        result = fitness_delivery.deliver_outbox_item(self._item(), mode="future_openclaw")

        self.assertFalse(result["delivered"])
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["reason"], "openclaw_send_api_not_configured")


if __name__ == "__main__":
    unittest.main()
