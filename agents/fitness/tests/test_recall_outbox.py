from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
for path in (ROOT, TOOLS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import fitness_recall_outbox  # noqa: E402
import fitness_state  # noqa: E402


class FitnessRecallOutboxTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.old_data_dir = fitness_state.DATA_DIR
        fitness_state.DATA_DIR = Path(self.tmp.name) / "data"
        self.user_id = "outbox_user"

    def tearDown(self) -> None:
        fitness_state.DATA_DIR = self.old_data_dir
        self.tmp.cleanup()

    def _item(self, date: str = "2026-06-24") -> dict:
        return fitness_recall_outbox.build_outbox_item(
            user_id=self.user_id,
            recall_type="training_day_no_meal_log",
            text="今天有训练安排，不用补全记录。",
            delivery_channel="wechat",
            delivery_mode="dry_run",
            date=date,
            now=f"{date}T18:00:00",
        )

    def test_outbox_initializes_when_missing(self) -> None:
        outbox = fitness_recall_outbox.load_outbox(self.user_id)

        self.assertEqual(outbox, {"version": 1, "items": []})
        self.assertTrue(fitness_recall_outbox.outbox_path(self.user_id).exists())

    def test_append_pending_item(self) -> None:
        item = fitness_recall_outbox.append_outbox_item(self.user_id, self._item())
        items = fitness_recall_outbox.list_outbox_items(self.user_id)

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["message_id"], item["message_id"])
        self.assertEqual(items[0]["status"], "pending")

    def test_duplicate_guard_returns_existing_pending_item(self) -> None:
        first = fitness_recall_outbox.append_outbox_item(self.user_id, self._item())
        second = fitness_recall_outbox.append_outbox_item(self.user_id, self._item())

        self.assertEqual(first["message_id"], second["message_id"])
        self.assertEqual(len(fitness_recall_outbox.list_outbox_items(self.user_id)), 1)

    def test_mark_sent_skipped_failed(self) -> None:
        sent_item = fitness_recall_outbox.append_outbox_item(self.user_id, self._item("2026-06-24"))
        skipped_item = fitness_recall_outbox.append_outbox_item(self.user_id, self._item("2026-06-25"))
        failed_item = fitness_recall_outbox.append_outbox_item(self.user_id, self._item("2026-06-26"))

        sent = fitness_recall_outbox.mark_sent(self.user_id, sent_item["message_id"], "2026-06-24T18:10:00")
        skipped = fitness_recall_outbox.mark_skipped(self.user_id, skipped_item["message_id"], "quiet_hours")
        failed = fitness_recall_outbox.mark_failed(self.user_id, failed_item["message_id"], "openclaw_send_api_not_configured")

        self.assertEqual(sent["status"], "sent")
        self.assertEqual(sent["sent_at"], "2026-06-24T18:10:00")
        self.assertEqual(skipped["status"], "skipped")
        self.assertEqual(skipped["skip_reason"], "quiet_hours")
        self.assertEqual(failed["status"], "failed")
        self.assertEqual(failed["skip_reason"], "openclaw_send_api_not_configured")

    def test_outbox_does_not_write_default_user(self) -> None:
        fitness_recall_outbox.load_outbox(self.user_id)

        self.assertFalse(fitness_state.get_user_data_dir("default").exists())


if __name__ == "__main__":
    unittest.main()
