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
import fitness_scheduler_config  # noqa: E402
import fitness_state  # noqa: E402


class FitnessScheduledRecallWorkerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.old_data_dir = fitness_state.DATA_DIR
        fitness_state.DATA_DIR = Path(self.tmp.name) / "data"
        self.user_id = "scheduled_worker_user"
        self.date = "2026-06-24"
        self.now = "2026-06-24T18:00:00"

    def tearDown(self) -> None:
        fitness_state.DATA_DIR = self.old_data_dir
        self.tmp.cleanup()

    def _seed(self, user_id: str | None = None, *, recall_enabled: bool = True) -> None:
        user = user_id or self.user_id
        fitness_state.update_daily_state({
            "date": self.date,
            "day_type": "training_day",
            "training": {"planned": True, "time": "evening", "status": "planned"},
            "nutrition": {"meals": []},
        }, user_id=user, date=self.date)
        fitness_recall.set_recall_opt_in(user_id=user, enabled=recall_enabled)

    def _scheduler(self, user_id: str | None = None, *, send: bool = False) -> None:
        user = user_id or self.user_id
        fitness_scheduler_config.configure_scheduler(
            user_id=user,
            enabled=True,
            channel="wechat",
            delivery_mode="openclaw_message",
            preferred_hours=[18],
            max_runs_per_day=3,
        )
        if send:
            fitness_scheduler_config.set_real_send(user_id=user, enabled=True, confirm=True)

    def _delivery(self, user_id: str | None = None, *, enabled: bool = True, allow_real_send: bool = False) -> None:
        user = user_id or self.user_id
        fitness_delivery_config.configure_wechat_delivery(
            user_id=user,
            target="DemoUserAbC123@im.wechat",
            account_id="demo-account-id",
            enabled=enabled,
            allow_real_send=allow_real_send,
        )

    def test_scheduled_run_disabled_does_not_generate_outbox(self) -> None:
        self._seed()

        result = fitness_recall_worker.scheduled_run(user_id=self.user_id, date=self.date, dry_run=True, now=self.now)

        self.assertEqual(result["blocked_reason"], "scheduler_disabled")
        self.assertEqual(fitness_recall_outbox.list_outbox_items(self.user_id), [])

    def test_scheduled_run_enabled_dry_run_generates_pending(self) -> None:
        self._seed()
        self._scheduler()
        self._delivery()
        completed = subprocess.CompletedProcess(["openclaw"], 0, stdout="{}", stderr="")
        with mock.patch("fitness_delivery.subprocess.run", return_value=completed):
            result = fitness_recall_worker.scheduled_run(user_id=self.user_id, date=self.date, dry_run=True, now=self.now)

        self.assertEqual(result["delivery"]["reason"], "dry_run_no_send")
        self.assertEqual(fitness_recall_outbox.list_outbox_items(self.user_id)[0]["status"], "pending")

    def test_scheduled_run_recall_disabled_does_not_deliver(self) -> None:
        self._seed(recall_enabled=False)
        self._scheduler()
        self._delivery()
        with mock.patch("fitness_delivery.subprocess.run") as mocked:
            result = fitness_recall_worker.scheduled_run(user_id=self.user_id, date=self.date, dry_run=True, now=self.now)

        mocked.assert_not_called()
        self.assertEqual(result["blocked_reason"], "recall_disabled")

    def test_scheduled_run_delivery_disabled_does_not_create_outbox(self) -> None:
        self._seed()
        self._scheduler()
        self._delivery(enabled=False)

        result = fitness_recall_worker.scheduled_run(user_id=self.user_id, date=self.date, dry_run=True, now=self.now)

        self.assertEqual(result["blocked_reason"], "delivery_config_disabled")
        self.assertEqual(fitness_recall_outbox.list_outbox_items(self.user_id), [])

    def test_real_send_requires_scheduler_and_cli_confirmation(self) -> None:
        self._seed()
        self._scheduler(send=False)
        self._delivery(allow_real_send=True)
        with mock.patch("fitness_delivery.subprocess.run") as mocked:
            result = fitness_recall_worker.scheduled_run(
                user_id=self.user_id,
                date=self.date,
                dry_run=False,
                send_enabled=True,
                confirm_send=True,
                now=self.now,
            )

        mocked.assert_not_called()
        self.assertEqual(result["blocked_reason"], "scheduler_real_send_not_enabled")

    def test_scheduled_run_all_skips_default_and_continues_after_failure(self) -> None:
        self._seed("default")
        self._scheduler("default")
        self._delivery("default")
        self._seed("ok_user")
        self._scheduler("ok_user")
        self._delivery("ok_user")
        self._seed("bad_user")
        self._scheduler("bad_user")
        self._delivery("bad_user")

        def fake_scheduled_run(**kwargs):
            if kwargs["user_id"] == "bad_user":
                raise RuntimeError("boom")
            return {
                "user_id": kwargs["user_id"],
                "scheduler_enabled": True,
                "recall_enabled": True,
                "opportunity": "training_day_no_meal_log",
                "blocked_reason": "ready",
                "delivery_mode": "openclaw_message",
                "outbox": {"status": "pending"},
                "delivery": {"status": "pending", "mode": "openclaw_message"},
            }

        with mock.patch("fitness_recall_worker.scheduled_run", side_effect=fake_scheduled_run):
            result = fitness_recall_worker.scheduled_run_all(date=self.date, dry_run=True, now=self.now)

        self.assertNotIn("default", result["results"])
        self.assertIn("ok_user", result["results"])
        self.assertIn("bad_user", result["results"])
        self.assertEqual(result["summary"]["failed"], 1)


if __name__ == "__main__":
    unittest.main()
