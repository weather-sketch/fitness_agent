"""Demo for Fitness OpenClaw message delivery adapter."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path
from unittest import mock


AGENT_ROOT = Path(__file__).resolve().parent
TOOLS_DIR = AGENT_ROOT / "tools"
DEMO_DATA_DIR = AGENT_ROOT / "demo_data" / "openclaw_delivery"
DEMO_DATA_LABEL = "agents/fitness/demo_data/openclaw_delivery"

for path in (AGENT_ROOT, TOOLS_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import fitness_delivery  # noqa: E402
import fitness_delivery_config  # noqa: E402
import fitness_recall_outbox  # noqa: E402
import fitness_state  # noqa: E402


def _reset_demo_state() -> None:
    if DEMO_DATA_DIR.exists():
        shutil.rmtree(DEMO_DATA_DIR)
    DEMO_DATA_DIR.mkdir(parents=True, exist_ok=True)
    fitness_state.DATA_DIR = DEMO_DATA_DIR


def _item(user_id: str = "wechat_demo_user") -> dict:
    return fitness_recall_outbox.build_outbox_item(
        user_id=user_id,
        recall_type="training_day_no_meal_log",
        text="今天有训练安排，不用补全记录。你只要回我一句“练前吃了”或“还没吃”。",
        delivery_channel="wechat",
        delivery_mode="openclaw_message",
        date="2026-06-24",
        now="2026-06-24T18:00:00",
    )


def _print_result(title: str, result: dict) -> None:
    print(f"=== {title} ===")
    print(f"mode: {result.get('mode')}")
    print(f"dry_run: {str(bool(result.get('dry_run'))).lower()}")
    print(f"delivered: {str(bool(result.get('delivered'))).lower()}")
    print(f"status: {result.get('status')}")
    print(f"reason: {result.get('reason')}")
    if result.get("command_preview"):
        print(f"command_preview: {result.get('command_preview')}")
    print()


def main() -> None:
    _reset_demo_state()
    print("Fitness Agent v0.5 OpenClaw Message Delivery Demo")
    print(f"Demo state directory: {DEMO_DATA_LABEL}")
    print("Real state under agents/fitness/data is not read or modified.")
    print("No real WeChat/OpenClaw message is sent in this demo.\n")

    missing = fitness_delivery.deliver_outbox_item(
        _item(),
        mode="openclaw_message",
        dry_run=True,
    )
    _print_result("Demo 1: delivery config missing", missing)

    fitness_delivery_config.configure_wechat_delivery(
        user_id="wechat_demo_user",
        target="demo-user@im.wechat",
        account_id="demo-account-id",
        enabled=True,
        allow_real_send=False,
    )
    refused = fitness_delivery.deliver_outbox_item(
        _item(),
        mode="openclaw_message",
        dry_run=False,
        send_enabled=True,
        confirm_send=True,
    )
    _print_result("Demo 2: real send disabled by config", refused)

    completed = mock.Mock(returncode=0, stdout='{"dryRun":true}', stderr="")
    with mock.patch("fitness_delivery.subprocess.run", return_value=completed):
        dry_run = fitness_delivery.deliver_outbox_item(
            _item(),
            mode="openclaw_message",
            dry_run=True,
        )
    _print_result("Demo 3: openclaw message dry-run", dry_run)

    print("=== Demo 4: future real send path ===")
    print("Real send remains manual and gated.")
    print("Required CLI flags: --send --confirm-send")
    print("Required config: enabled=true and allow_real_send=true")
    print("This demo does not send anything.")


if __name__ == "__main__":
    main()
