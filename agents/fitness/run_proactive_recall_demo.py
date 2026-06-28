"""Demo for Fitness proactive recall outbox."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path


AGENT_ROOT = Path(__file__).resolve().parent
TOOLS_DIR = AGENT_ROOT / "tools"
DEMO_DATA_DIR = AGENT_ROOT / "demo_data" / "proactive_recall"
DEMO_DATA_LABEL = "agents/fitness/demo_data/proactive_recall"

for path in (AGENT_ROOT, TOOLS_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import fitness_recall  # noqa: E402
import fitness_recall_outbox  # noqa: E402
import fitness_recall_worker  # noqa: E402
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
            "post_workout_meal_status": "unknown",
        },
        "nutrition": {"meals": []},
    }, user_id=user_id, date=date)


def _print_result(title: str, result: dict) -> None:
    print(f"=== {title} ===")
    print(f"enabled: {str(result['recall_enabled']).lower()}")
    print(f"opportunity: {result['opportunity']}")
    print(f"should_send: {str(result['should_send']).lower()}")
    print(f"blocked_reason: {result['blocked_reason']}")
    outbox = result.get("outbox") or {}
    print(f"outbox_status: {outbox.get('status')}")
    print(f"message_id: {outbox.get('message_id')}")
    print(f"duplicate: {str(bool(outbox.get('duplicate'))).lower()}")
    if result.get("delivery"):
        print(f"delivery_mode: {result['delivery'].get('mode')}")
        print(f"delivery_reason: {result['delivery'].get('reason')}")
    if result.get("generated_message"):
        print("message:")
        print(result["generated_message"])
    print()


def main() -> None:
    _reset_demo_state()
    print("Fitness Agent v0.5 Proactive Recall Outbox Demo")
    print(f"Demo state directory: {DEMO_DATA_LABEL}")
    print("Real state under agents/fitness/data is not read or modified.")
    print("No real WeChat/OpenClaw message is sent.\n")

    user_id = "wechat_demo_user"
    date = "2026-06-24"
    now = "2026-06-24T18:00:00"
    _seed_training_day(user_id, date)

    disabled = fitness_recall_worker.run_once(
        user_id=user_id,
        date=date,
        channel="wechat",
        delivery_mode="dry_run",
        now=now,
    )
    _print_result("Demo 1: recall disabled", disabled)

    fitness_recall.set_recall_opt_in(user_id=user_id, enabled=True)
    pending = fitness_recall_worker.run_once(
        user_id=user_id,
        date=date,
        channel="wechat",
        delivery_mode="dry_run",
        now=now,
    )
    _print_result("Demo 2: opt-in creates pending outbox", pending)

    duplicate = fitness_recall_worker.run_once(
        user_id=user_id,
        date=date,
        channel="wechat",
        delivery_mode="dry_run",
        now="2026-06-24T19:00:00",
    )
    _print_result("Demo 3: duplicate guard", duplicate)

    opt_out_date = "2026-06-25"
    _seed_training_day(user_id, opt_out_date)
    fitness_recall.set_recall_opt_in(user_id=user_id, enabled=False)
    opt_out = fitness_recall_worker.run_once(
        user_id=user_id,
        date=opt_out_date,
        channel="wechat",
        delivery_mode="dry_run",
        now="2026-06-25T18:00:00",
    )
    _print_result("Demo 4: opt-out blocks new outbox", opt_out)

    future_user = "wechat_future_openclaw_user"
    future_date = "2026-06-26"
    _seed_training_day(future_user, future_date)
    fitness_recall.set_recall_opt_in(user_id=future_user, enabled=True)
    future = fitness_recall_worker.run_once(
        user_id=future_user,
        date=future_date,
        channel="wechat",
        delivery_mode="future_openclaw",
        now="2026-06-26T18:00:00",
    )
    _print_result("Demo 5: future_openclaw unavailable", future)

    print("Outbox counts:")
    print(f"- {user_id}: {len(fitness_recall_outbox.list_outbox_items(user_id))}")
    print(f"- {future_user}: {len(fitness_recall_outbox.list_outbox_items(future_user))}")


if __name__ == "__main__":
    main()
