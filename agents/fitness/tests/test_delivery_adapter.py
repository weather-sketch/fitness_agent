from __future__ import annotations

import contextlib
import io
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
for path in (ROOT, TOOLS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import fitness_delivery  # noqa: E402


class FitnessDeliveryAdapterTest(unittest.TestCase):
    def _item(self) -> dict:
        return {
            "message_id": "recall-test",
            "user_id": "delivery_user",
            "delivery_channel": "wechat",
            "text": "今天有训练安排，不用补全记录。",
            "status": "pending",
        }

    def test_dry_run_does_not_send(self) -> None:
        result = fitness_delivery.deliver_outbox_item(self._item(), mode="dry_run")

        self.assertFalse(result["delivered"])
        self.assertEqual(result["mode"], "dry_run")
        self.assertEqual(result["status"], "pending")
        self.assertEqual(result["reason"], "dry_run_no_send")

    def test_console_prints_but_keeps_pending(self) -> None:
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            result = fitness_delivery.deliver_outbox_item(self._item(), mode="console")

        self.assertIn("Fitness Recall Console Delivery", stream.getvalue())
        self.assertFalse(result["delivered"])
        self.assertEqual(result["status"], "pending")
        self.assertEqual(result["reason"], "console_preview_no_send")

    def test_future_openclaw_returns_unavailable(self) -> None:
        result = fitness_delivery.deliver_outbox_item(self._item(), mode="future_openclaw")

        self.assertFalse(result["delivered"])
        self.assertEqual(result["mode"], "future_openclaw")
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["reason"], "openclaw_send_api_not_configured")


if __name__ == "__main__":
    unittest.main()
