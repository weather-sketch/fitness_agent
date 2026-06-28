"""Demo for scheduled proactive recall worker.

No real OpenClaw or WeChat message is sent. Subprocess delivery is mocked.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path
from unittest import mock


AGENT_ROOT = Path(__file__).resolve().parent
TOOLS_DIR = AGENT_ROOT / "tools"
DEMO_DATA_DIR = AGENT_ROOT / "demo_data" / "scheduled_recall"
DEMO_DATA_LABEL = "agents/fitness/demo_data/scheduled_recall"

for path in (AGENT_ROOT, TOOLS_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import fitness_delivery  # noqa: E402
import fitness_delivery_config  # noqa: E402
import fitness_recall  # noqa: E402
import fitness_recall_outbox  # noqa: E402
import fitness_recall_worker  # noqa: E402
import fitness_scheduler_config  # noqa: E402
import fitness_state  # noqa: E402


def _reset_demo_state() -> None:
    if DEMO_DATA_DIR.exists():
        shutil.rmtree(DEMO_DATA_DIR)
    DEMO_DATA_DIR.mkdir(parents=True, exist_ok=True)
    fitness_state.DATA_DIR = DEMO_DATA_DIR


def _seed_training_day(user_id: str, date: str) -> None:
    fitness_state.update_daily_state({
        "date": date,
        "day_type": "training_day",
        "training": {
            "planned": True,
            "type": "glutes",
            "time": "evening",
            "status": "planned",
        },
        "nutrition": {"meals": []},
    }, user_id=user_id, date=date)
    fitness_recall.set_recall_opt_in(user_id=user_id, enabled=True)


def _configure_scheduler(user_id: str) -> None:
    fitness_scheduler_config.configure_scheduler(
        user_id=user_id,
        enabled=True,
        channel="wechat",
        delivery_mode="openclaw_message",
        preferred_hours=[18],
        timezone="Asia/Shanghai",
        max_runs_per_day=3,
    )


def _configure_delivery(user_id: str, *, enabled: bool = True, allow_real_send: bool = False) -> None:
    fitness_delivery_config.configure_wechat_delivery(
        user_id=user_id,
        target="DemoUserAbC123@im.wechat",
        account_id="demo-account-id",
        enabled=enabled,
        allow_real_send=allow_real_send,
    )


def _print_result(title: str, result: dict) -> None:
    print(f"=== {title} ===")
    print(f"scheduler_enabled: {str(bool(result.get('scheduler_enabled'))).lower()}")
    print(f"opportunity: {result.get('opportunity')}")
    print(f"should_send: {str(bool(result.get('should_send'))).lower()}")
    print(f"blocked_reason: {result.get('blocked_reason')}")
    outbox = result.get("outbox") or {}
    print(f"outbox_status: {outbox.get('status')}")
    print(f"duplicate: {str(bool(outbox.get('duplicate'))).lower()}")
    delivery = result.get("delivery") or {}
    if delivery:
        print(f"delivery_mode: {delivery.get('mode')}")
        print(f"delivery_reason: {delivery.get('reason')}")
        if delivery.get("command_preview"):
            print(f"command_preview: {delivery.get('command_preview')}")
    print()


def main() -> None:
    _reset_demo_state()
    print("Fitness Agent v0.5 Scheduled Proactive Recall Demo")
    print(f"Demo state directory: {DEMO_DATA_LABEL}")
    print("Real state under agents/fitness/data is not read or modified.")
    print("No real OpenClaw/WeChat message is sent.\n")

    date = "2026-06-24"
    now = "2026-06-24T18:00:00"

    disabled_user = "sched_disabled_user"
    _seed_training_day(disabled_user, date)
    disabled = fitness_recall_worker.scheduled_run(user_id=disabled_user, date=date, dry_run=True, now=now)
    _print_result("Demo 1: scheduler disabled", disabled)

    dry_user = "sched_dry_run_user"
    _seed_training_day(dry_user, date)
    _configure_scheduler(dry_user)
    _configure_delivery(dry_user)
    completed = subprocess.CompletedProcess(["openclaw"], 0, stdout='{"dryRun":true}', stderr="")
    with mock.patch("fitness_delivery.subprocess.run", return_value=completed):
        dry = fitness_recall_worker.scheduled_run(user_id=dry_user, date=date, dry_run=True, now=now)
    _print_result("Demo 2: scheduler enabled dry-run creates pending outbox", dry)

    delivery_disabled_user = "sched_delivery_disabled_user"
    _seed_training_day(delivery_disabled_user, date)
    _configure_scheduler(delivery_disabled_user)
    _configure_delivery(delivery_disabled_user, enabled=False)
    delivery_disabled = fitness_recall_worker.scheduled_run(
        user_id=delivery_disabled_user,
        date=date,
        dry_run=True,
        now=now,
    )
    _print_result("Demo 3: delivery disabled blocks scheduled run", delivery_disabled)

    real_gate_user = "sched_real_gate_user"
    _seed_training_day(real_gate_user, date)
    _configure_scheduler(real_gate_user)
    fitness_scheduler_config.set_real_send(user_id=real_gate_user, enabled=True, confirm=True)
    _configure_delivery(real_gate_user, enabled=True, allow_real_send=True)
    real_gate = fitness_recall_worker.scheduled_run(
        user_id=real_gate_user,
        date=date,
        dry_run=False,
        send_enabled=False,
        confirm_send=False,
        now=now,
    )
    _print_result("Demo 4: real-send config enabled but CLI did not confirm", real_gate)

    with mock.patch("fitness_delivery.subprocess.run", return_value=completed):
        duplicate = fitness_recall_worker.scheduled_run(user_id=dry_user, date=date, dry_run=True, now="2026-06-24T18:30:00")
    _print_result("Demo 5: duplicate guard prevents second pending item", duplicate)

    command = fitness_delivery.build_openclaw_message_command(
        target="DemoUserAbC123@im.wechat",
        account_id="demo-account-id",
        text="exact-case preservation demo",
        dry_run=True,
    )
    print("=== Demo 6: exact-case target preservation ===")
    print("Actual command target is preserved exactly in subprocess args.")
    print(f"actual_target: {command[command.index('--target') + 1]}")
    print(f"masked_preview: {fitness_delivery._command_preview(command)}")
    print("Do not lowercase @im.wechat targets.")


if __name__ == "__main__":
    main()
