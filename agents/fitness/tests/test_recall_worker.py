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

import fitness_recall  # noqa: E402
import fitness_recall_outbox  # noqa: E402
import fitness_recall_worker  # noqa: E402
import fitness_state  # noqa: E402


class FitnessRecallWorkerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.old_data_dir = fitness_state.DATA_DIR
        fitness_state.DATA_DIR = Path(self.tmp.name) / "data"
        self.user_id = "worker_user"
        self.date = "2026-06-24"
        self.now = "2026-06-24T18:00:00"

    def tearDown(self) -> None:
        fitness_state.DATA_DIR = self.old_data_dir
        self.tmp.cleanup()

    def _seed_training_day(self, date: str | None = None) -> None:
        current_date = date or self.date
        fitness_state.update_daily_state({
            "date": current_date,
            "day_type": "training_day",
            "training": {"planned": True, "time": "evening", "status": "planned"},
            "nutrition": {"meals": []},
        }, user_id=self.user_id, date=current_date)

    def test_recall_disabled_does_not_generate_outbox(self) -> None:
        self._seed_training_day()
        result = fitness_recall_worker.run_once(
            user_id=self.user_id,
            date=self.date,
            channel="wechat",
            delivery_mode="dry_run",
            now=self.now,
        )

        self.assertFalse(result["recall_enabled"])
        self.assertEqual(result["blocked_reason"], "recall_disabled")
        self.assertEqual(result["outbox"]["created"], False)
        self.assertFalse(fitness_recall_outbox.outbox_path(self.user_id).exists())

    def test_opt_in_generates_pending_outbox_item(self) -> None:
        self._seed_training_day()
        fitness_recall.set_recall_opt_in(self.user_id, True)
        result = fitness_recall_worker.run_once(
            user_id=self.user_id,
            date=self.date,
            channel="wechat",
            delivery_mode="dry_run",
            now=self.now,
        )
        items = fitness_recall_outbox.list_outbox_items(self.user_id)

        self.assertTrue(result["recall_enabled"])
        self.assertTrue(result["should_send"])
        self.assertEqual(result["outbox"]["status"], "pending")
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["status"], "pending")
        self.assertEqual(result["delivery"]["reason"], "dry_run_no_send")

    def test_duplicate_guard_prevents_second_pending_item(self) -> None:
        self._seed_training_day()
        fitness_recall.set_recall_opt_in(self.user_id, True)
        first = fitness_recall_worker.run_once(
            user_id=self.user_id,
            date=self.date,
            channel="wechat",
            delivery_mode="dry_run",
            now=self.now,
        )
        second = fitness_recall_worker.run_once(
            user_id=self.user_id,
            date=self.date,
            channel="wechat",
            delivery_mode="dry_run",
            now="2026-06-24T19:00:00",
        )

        self.assertEqual(second["blocked_reason"], "duplicate_outbox_item")
        self.assertTrue(second["outbox"]["duplicate"])
        self.assertEqual(first["outbox"]["message_id"], second["outbox"]["message_id"])
        self.assertEqual(len(fitness_recall_outbox.list_outbox_items(self.user_id)), 1)

    def test_opt_out_does_not_generate_new_outbox_item(self) -> None:
        self._seed_training_day()
        fitness_recall.set_recall_opt_in(self.user_id, True)
        fitness_recall_worker.run_once(
            user_id=self.user_id,
            date=self.date,
            channel="wechat",
            delivery_mode="dry_run",
            now=self.now,
        )
        fitness_recall.set_recall_opt_in(self.user_id, False)
        next_date = "2026-06-25"
        self._seed_training_day(next_date)
        result = fitness_recall_worker.run_once(
            user_id=self.user_id,
            date=next_date,
            channel="wechat",
            delivery_mode="dry_run",
            now="2026-06-25T18:00:00",
        )

        self.assertEqual(result["blocked_reason"], "recall_disabled")
        self.assertEqual(len(fitness_recall_outbox.list_outbox_items(self.user_id)), 1)

    def test_quiet_hours_creates_skipped_item_with_next_allowed_time(self) -> None:
        self._seed_training_day()
        fitness_recall.set_recall_opt_in(self.user_id, True)
        result = fitness_recall_worker.run_once(
            user_id=self.user_id,
            date=self.date,
            channel="wechat",
            delivery_mode="dry_run",
            now="2026-06-24T23:30:00",
        )
        items = fitness_recall_outbox.list_outbox_items(self.user_id)

        self.assertEqual(result["blocked_reason"], "quiet_hours")
        self.assertEqual(result["outbox"]["status"], "skipped")
        self.assertEqual(result["outbox"]["scheduled_for"], "2026-06-25T08:00:00")
        self.assertEqual(items[0]["skip_reason"], "quiet_hours")

    def test_generated_message_is_non_shaming(self) -> None:
        self._seed_training_day()
        fitness_recall.set_recall_opt_in(self.user_id, True)
        result = fitness_recall_worker.run_once(
            user_id=self.user_id,
            date=self.date,
            channel="wechat",
            delivery_mode="dry_run",
            now=self.now,
        )

        message = result["generated_message"]
        self.assertIn("不用补全记录", message)
        self.assertNotIn("你又失败了", message)
        self.assertNotIn("惩罚", message)
        self.assertNotIn("必须", message)

    def test_worker_does_not_write_default_user(self) -> None:
        self._seed_training_day()
        fitness_recall.set_recall_opt_in(self.user_id, True)
        fitness_recall_worker.run_once(
            user_id=self.user_id,
            date=self.date,
            channel="wechat",
            delivery_mode="dry_run",
            now=self.now,
        )

        self.assertFalse(fitness_state.get_user_data_dir("default").exists())


if __name__ == "__main__":
    unittest.main()
