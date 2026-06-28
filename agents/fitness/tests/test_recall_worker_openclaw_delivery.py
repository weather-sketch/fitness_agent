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

import fitness_delivery_config  # noqa: E402
import fitness_recall  # noqa: E402
import fitness_recall_outbox  # noqa: E402
import fitness_recall_worker  # noqa: E402
import fitness_state  # noqa: E402


class FitnessRecallWorkerOpenClawDeliveryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.old_data_dir = fitness_state.DATA_DIR
        fitness_state.DATA_DIR = Path(self.tmp.name) / "data"
        self.user_id = "worker_openclaw_user"
        self.date = "2026-06-24"
        self.now = "2026-06-24T18:00:00"

    def tearDown(self) -> None:
        fitness_state.DATA_DIR = self.old_data_dir
        self.tmp.cleanup()

    def _seed(self) -> None:
        fitness_state.update_daily_state({
            "date": self.date,
            "day_type": "training_day",
            "training": {"planned": True, "time": "evening", "status": "planned"},
            "nutrition": {"meals": []},
        }, user_id=self.user_id, date=self.date)

    def _configure(self, *, allow_real_send: bool = False) -> None:
        fitness_delivery_config.configure_wechat_delivery(
            user_id=self.user_id,
            target="target-user@im.wechat",
            account_id="demo-account-id",
            enabled=True,
            allow_real_send=allow_real_send,
        )

    def test_recall_disabled_prevents_openclaw_delivery(self) -> None:
        self._seed()
        with mock.patch("fitness_delivery.subprocess.run") as mocked:
            result = fitness_recall_worker.run_once(
                user_id=self.user_id,
                date=self.date,
                channel="wechat",
                delivery_mode="openclaw_message",
                dry_run=True,
                now=self.now,
            )

        mocked.assert_not_called()
        self.assertEqual(result["blocked_reason"], "recall_disabled")

    def test_openclaw_dry_run_does_not_mark_sent(self) -> None:
        self._seed()
        self._configure()
        fitness_recall.set_recall_opt_in(self.user_id, True)
        completed = subprocess.CompletedProcess(["openclaw"], 0, stdout="{}", stderr="")
        with mock.patch("fitness_delivery.subprocess.run", return_value=completed):
            result = fitness_recall_worker.run_once(
                user_id=self.user_id,
                date=self.date,
                channel="wechat",
                delivery_mode="openclaw_message",
                dry_run=True,
                now=self.now,
            )
        items = fitness_recall_outbox.list_outbox_items(self.user_id)

        self.assertEqual(result["delivery"]["reason"], "dry_run_no_send")
        self.assertEqual(items[0]["status"], "pending")

    def test_successful_mocked_real_send_marks_sent(self) -> None:
        self._seed()
        self._configure(allow_real_send=True)
        fitness_recall.set_recall_opt_in(self.user_id, True)
        completed = subprocess.CompletedProcess(["openclaw"], 0, stdout='{"ok":true}', stderr="")
        with mock.patch("fitness_delivery.subprocess.run", return_value=completed):
            result = fitness_recall_worker.run_once(
                user_id=self.user_id,
                date=self.date,
                channel="wechat",
                delivery_mode="openclaw_message",
                dry_run=False,
                send_enabled=True,
                confirm_send=True,
                now=self.now,
            )
        items = fitness_recall_outbox.list_outbox_items(self.user_id)

        self.assertTrue(result["delivery"]["delivered"])
        self.assertEqual(items[0]["status"], "sent")
        self.assertEqual(items[0]["delivery_result"]["reason"], "openclaw_message_sent")

    def test_failed_mocked_real_send_marks_failed(self) -> None:
        self._seed()
        self._configure(allow_real_send=True)
        fitness_recall.set_recall_opt_in(self.user_id, True)
        completed = subprocess.CompletedProcess(["openclaw"], 1, stdout="", stderr="boom")
        with mock.patch("fitness_delivery.subprocess.run", return_value=completed):
            result = fitness_recall_worker.run_once(
                user_id=self.user_id,
                date=self.date,
                channel="wechat",
                delivery_mode="openclaw_message",
                dry_run=False,
                send_enabled=True,
                confirm_send=True,
                now=self.now,
            )
        items = fitness_recall_outbox.list_outbox_items(self.user_id)

        self.assertEqual(result["delivery"]["reason"], "openclaw_message_failed")
        self.assertEqual(items[0]["status"], "failed")

    def test_duplicate_guard_prevents_repeated_delivery(self) -> None:
        self._seed()
        self._configure()
        fitness_recall.set_recall_opt_in(self.user_id, True)
        completed = subprocess.CompletedProcess(["openclaw"], 0, stdout="{}", stderr="")
        with mock.patch("fitness_delivery.subprocess.run", return_value=completed):
            fitness_recall_worker.run_once(
                user_id=self.user_id,
                date=self.date,
                channel="wechat",
                delivery_mode="openclaw_message",
                dry_run=True,
                now=self.now,
            )
        with mock.patch("fitness_delivery.subprocess.run") as mocked:
            result = fitness_recall_worker.run_once(
                user_id=self.user_id,
                date=self.date,
                channel="wechat",
                delivery_mode="openclaw_message",
                dry_run=True,
                now="2026-06-24T19:00:00",
            )

        mocked.assert_not_called()
        self.assertEqual(result["blocked_reason"], "duplicate_outbox_item")


if __name__ == "__main__":
    unittest.main()
