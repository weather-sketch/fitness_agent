"""Proactive recall worker simulator for Fitness Agent.

This worker writes recall outbox items only. It does not schedule background
jobs, call WeChat SDKs, or send real OpenClaw messages.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import fitness_delivery  # noqa: E402
import fitness_delivery_config  # noqa: E402
import fitness_recall  # noqa: E402
import fitness_recall_outbox  # noqa: E402
import fitness_scheduler_config  # noqa: E402
import fitness_state  # noqa: E402


QUIET_START_HOUR = 23
QUIET_END_HOUR = 8
MIN_INTERVAL_HOURS = 12


def _now(value: str | datetime | None = None) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value)
    return datetime.now()


def is_quiet_hours(now: str | datetime | None = None) -> bool:
    current = _now(now)
    return current.hour >= QUIET_START_HOUR or current.hour < QUIET_END_HOUR


def next_allowed_time(now: str | datetime | None = None) -> str:
    current = _now(now)
    if current.hour < QUIET_END_HOUR:
        allowed = current.replace(hour=QUIET_END_HOUR, minute=0, second=0, microsecond=0)
    else:
        allowed = (current + timedelta(days=1)).replace(hour=QUIET_END_HOUR, minute=0, second=0, microsecond=0)
    return allowed.isoformat(timespec="seconds")


def _base_result(
    *,
    user_id: str,
    date: str,
    channel: str,
    delivery_mode: str,
    opportunity: dict[str, Any],
) -> dict[str, Any]:
    return {
        "user_id": user_id,
        "date": date,
        "channel": channel,
        "delivery_mode": delivery_mode,
        "recall_enabled": bool(opportunity.get("enabled")),
        "opportunity": opportunity.get("recall_type"),
        "should_send": bool(opportunity.get("should_send")),
        "blocked_reason": opportunity.get("blocked_reason"),
        "generated_message": opportunity.get("message") or "",
        "outbox": None,
        "delivery": None,
    }


def _delivery_config_ready(user_id: str, channel: str, delivery_mode: str, *, real_send: bool) -> tuple[bool, str]:
    if delivery_mode != "openclaw_message":
        return True, "ready"
    channel_config = fitness_delivery_config.get_channel_config(user_id, channel)
    if not channel_config:
        return False, "delivery_config_missing"
    if not channel_config.get("enabled"):
        return False, "delivery_config_disabled"
    if not channel_config.get("target"):
        return False, "delivery_target_missing"
    if not channel_config.get("account_id"):
        return False, "delivery_account_id_missing"
    if real_send and not channel_config.get("allow_real_send"):
        return False, "delivery_real_send_not_allowed"
    return True, "ready"


def _scheduled_blocked_result(
    *,
    user_id: str,
    date: str,
    channel: str,
    delivery_mode: str,
    reason: str,
    scheduler_enabled: bool,
) -> dict[str, Any]:
    return {
        "user_id": user_id,
        "date": date,
        "channel": channel,
        "delivery_mode": delivery_mode,
        "scheduler_enabled": scheduler_enabled,
        "recall_enabled": None,
        "opportunity": None,
        "should_send": False,
        "blocked_reason": reason,
        "generated_message": "",
        "outbox": {"created": False, "duplicate": False, "status": None},
        "delivery": None,
    }


def _runs_today(user_id: str, now: datetime) -> int:
    today = now.date().isoformat()
    count = 0
    for item in fitness_recall_outbox.list_outbox_items(user_id):
        created_at = str(item.get("created_at") or "")
        metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
        if created_at.startswith(today) and metadata.get("source") in {"scheduled_recall_worker", "recall_worker"}:
            count += 1
    return count


def scheduled_run(
    *,
    user_id: str,
    date: str,
    dry_run: bool = True,
    send_enabled: bool = False,
    confirm_send: bool = False,
    now: str | datetime | None = None,
) -> dict[str, Any]:
    """Run the recall worker through scheduler config gates."""
    current_now = _now(now)
    config = fitness_scheduler_config.load_scheduler_config(user_id)
    channel = str(config.get("channel") or "wechat")
    delivery_mode = str(config.get("delivery_mode") or "openclaw_message")
    if not config.get("enabled"):
        return _scheduled_blocked_result(
            user_id=user_id,
            date=date,
            channel=channel,
            delivery_mode=delivery_mode,
            reason="scheduler_disabled",
            scheduler_enabled=False,
        )

    schedule = config.get("schedule") if isinstance(config.get("schedule"), dict) else {}
    preferred_hours = schedule.get("preferred_hours") if isinstance(schedule.get("preferred_hours"), list) else []
    if preferred_hours and current_now.hour not in {int(hour) for hour in preferred_hours}:
        return _scheduled_blocked_result(
            user_id=user_id,
            date=date,
            channel=channel,
            delivery_mode=delivery_mode,
            reason="outside_preferred_hours",
            scheduler_enabled=True,
        )

    max_runs = int(schedule.get("max_runs_per_day") or 3)
    if _runs_today(user_id, current_now) >= max_runs:
        return _scheduled_blocked_result(
            user_id=user_id,
            date=date,
            channel=channel,
            delivery_mode=delivery_mode,
            reason="max_runs_per_day_reached",
            scheduler_enabled=True,
        )

    if not dry_run and not (send_enabled and confirm_send):
        return _scheduled_blocked_result(
            user_id=user_id,
            date=date,
            channel=channel,
            delivery_mode=delivery_mode,
            reason="cli_real_send_not_confirmed",
            scheduler_enabled=True,
        )

    wants_real_send = bool(send_enabled and confirm_send and not dry_run)
    if wants_real_send and not (config.get("send_enabled") and config.get("confirm_send")):
        return _scheduled_blocked_result(
            user_id=user_id,
            date=date,
            channel=channel,
            delivery_mode=delivery_mode,
            reason="scheduler_real_send_not_enabled",
            scheduler_enabled=True,
        )

    ready, reason = _delivery_config_ready(user_id, channel, delivery_mode, real_send=wants_real_send)
    if not ready:
        return _scheduled_blocked_result(
            user_id=user_id,
            date=date,
            channel=channel,
            delivery_mode=delivery_mode,
            reason=reason,
            scheduler_enabled=True,
        )

    result = run_once(
        user_id=user_id,
        date=date,
        channel=channel,
        delivery_mode=delivery_mode,
        dry_run=dry_run,
        send_enabled=send_enabled,
        confirm_send=confirm_send,
        now=current_now,
    )
    result["scheduler_enabled"] = True
    return result


def scheduled_run_all(
    *,
    date: str,
    dry_run: bool = True,
    send_enabled: bool = False,
    confirm_send: bool = False,
    include_default: bool = False,
    now: str | datetime | None = None,
) -> dict[str, Any]:
    users = fitness_scheduler_config.iter_scheduler_users(include_default=include_default)
    results: dict[str, Any] = {}
    summary = {
        "users_checked": len(users),
        "eligible": 0,
        "sent": 0,
        "pending": 0,
        "skipped": 0,
        "failed": 0,
    }
    for user_id in users:
        try:
            result = scheduled_run(
                user_id=user_id,
                date=date,
                dry_run=dry_run,
                send_enabled=send_enabled,
                confirm_send=confirm_send,
                now=now,
            )
        except Exception as exc:  # pragma: no cover - defensive per-user isolation
            result = {
                "user_id": user_id,
                "blocked_reason": "scheduled_run_error",
                "error": str(exc),
                "outbox": {"status": None},
                "delivery": None,
            }
        results[user_id] = result
        if result.get("scheduler_enabled"):
            summary["eligible"] += 1
        outbox = result.get("outbox") if isinstance(result.get("outbox"), dict) else {}
        delivery = result.get("delivery") if isinstance(result.get("delivery"), dict) else {}
        status = outbox.get("status") or delivery.get("status")
        if status == "sent":
            summary["sent"] += 1
        elif status == "pending":
            summary["pending"] += 1
        elif status == "failed" or result.get("error"):
            summary["failed"] += 1
        else:
            summary["skipped"] += 1
    return {"summary": summary, "results": results}


def run_once(
    *,
    user_id: str,
    date: str,
    channel: str = "local",
    delivery_mode: str = "dry_run",
    dry_run: bool = True,
    send_enabled: bool = False,
    confirm_send: bool = False,
    now: str | datetime | None = None,
    min_interval_hours: int = MIN_INTERVAL_HOURS,
) -> dict[str, Any]:
    """Detect one recall opportunity and write at most one outbox item."""
    current_now = _now(now)
    opportunity = fitness_recall.detect_recall_opportunity(user_id=user_id, date=date, now=current_now)
    result = _base_result(
        user_id=user_id,
        date=date,
        channel=channel,
        delivery_mode=delivery_mode,
        opportunity=opportunity,
    )

    recall_type = str(opportunity.get("recall_type") or "none")
    if not opportunity.get("should_send"):
        result["outbox"] = {"created": False, "duplicate": False, "status": None}
        return result

    duplicate = fitness_recall_outbox.find_duplicate_item(user_id, recall_type, date)
    if duplicate:
        result["should_send"] = False
        result["blocked_reason"] = "duplicate_outbox_item"
        result["outbox"] = {
            "created": False,
            "duplicate": True,
            "status": duplicate.get("status"),
            "message_id": duplicate.get("message_id"),
        }
        return result

    if is_quiet_hours(current_now):
        item = fitness_recall_outbox.build_outbox_item(
            user_id=user_id,
            recall_type=recall_type,
            text=str(opportunity.get("message") or ""),
            delivery_channel=channel,
            delivery_mode=delivery_mode,
            date=date,
            status="skipped",
            scheduled_for=next_allowed_time(current_now),
            skip_reason="quiet_hours",
            now=current_now,
        )
        created = fitness_recall_outbox.append_outbox_item(user_id, item)
        result["should_send"] = False
        result["blocked_reason"] = "quiet_hours"
        result["outbox"] = {
            "created": True,
            "duplicate": False,
            "status": created.get("status"),
            "message_id": created.get("message_id"),
            "scheduled_for": created.get("scheduled_for"),
        }
        return result

    if fitness_recall_outbox.has_recent_active_item(user_id, current_now, min_interval_hours):
        result["should_send"] = False
        result["blocked_reason"] = "cooldown_active"
        result["outbox"] = {"created": False, "duplicate": False, "status": None}
        return result

    item = fitness_recall_outbox.build_outbox_item(
        user_id=user_id,
        recall_type=recall_type,
        text=str(opportunity.get("message") or ""),
        delivery_channel=channel,
        delivery_mode=delivery_mode,
        date=date,
        status="pending",
        now=current_now,
    )
    created = fitness_recall_outbox.append_outbox_item(user_id, item)
    delivery = fitness_delivery.deliver_outbox_item(
        created,
        mode=delivery_mode,
        dry_run=dry_run,
        send_enabled=send_enabled,
        confirm_send=confirm_send,
    )
    if delivery.get("status") == "failed":
        created = fitness_recall_outbox.mark_failed(
            user_id,
            created["message_id"],
            str(delivery.get("reason") or "delivery_failed"),
            delivery_result=delivery,
        )
    elif delivery.get("delivered") and delivery.get("status") == "sent":
        created = fitness_recall_outbox.mark_sent(
            user_id,
            created["message_id"],
            current_now,
            delivery_result=delivery,
        )
    result["outbox"] = {
        "created": True,
        "duplicate": False,
        "status": created.get("status"),
        "message_id": created.get("message_id"),
    }
    result["delivery"] = delivery
    return result


def send_pending(
    *,
    user_id: str,
    message_id: str,
    delivery_mode: str = "dry_run",
    dry_run: bool = True,
    send_enabled: bool = False,
    confirm_send: bool = False,
    now: str | datetime | None = None,
) -> dict[str, Any]:
    items = fitness_recall_outbox.list_outbox_items(user_id)
    item = next((candidate for candidate in items if candidate.get("message_id") == message_id), None)
    if not item:
        return {
            "user_id": user_id,
            "message_id": message_id,
            "delivery_mode": delivery_mode,
            "delivery": None,
            "outbox": {"status": None},
            "error": "outbox_item_not_found",
        }
    if item.get("status") != "pending":
        return {
            "user_id": user_id,
            "message_id": message_id,
            "delivery_mode": delivery_mode,
            "delivery": None,
            "outbox": {"status": item.get("status")},
            "error": "outbox_item_not_pending",
        }
    item["delivery_mode"] = delivery_mode
    delivery = fitness_delivery.deliver_outbox_item(
        item,
        mode=delivery_mode,
        dry_run=dry_run,
        send_enabled=send_enabled,
        confirm_send=confirm_send,
    )
    updated = item
    if delivery.get("status") == "failed":
        updated = fitness_recall_outbox.mark_failed(
            user_id,
            message_id,
            str(delivery.get("reason") or "delivery_failed"),
            delivery_result=delivery,
        )
    elif delivery.get("delivered") and delivery.get("status") == "sent":
        updated = fitness_recall_outbox.mark_sent(
            user_id,
            message_id,
            now,
            delivery_result=delivery,
        )
    return {
        "user_id": user_id,
        "message_id": message_id,
        "delivery_mode": delivery_mode,
        "delivery": delivery,
        "outbox": {
            "status": updated.get("status"),
            "message_id": updated.get("message_id"),
        },
        "error": None,
    }


def _print_run_once(result: dict[str, Any]) -> None:
    print("Fitness Recall Worker")
    print()
    print(f"User: {result['user_id']}")
    print(f"Date: {result['date']}")
    print(f"Channel: {result['channel']}")
    print(f"Delivery mode: {result['delivery_mode']}")
    print()
    print(f"Recall enabled: {str(result['recall_enabled']).lower()}")
    print(f"Opportunity: {result['opportunity']}")
    print(f"Should send: {str(result['should_send']).lower()}")
    print(f"Blocked reason: {result['blocked_reason']}")
    if result.get("generated_message"):
        print()
        print("Generated message:")
        print(result["generated_message"])
    print()
    print("Outbox:")
    outbox = result.get("outbox") or {}
    print(f"- status: {outbox.get('status')}")
    print(f"- message_id: {outbox.get('message_id')}")
    print(f"- duplicate: {str(bool(outbox.get('duplicate'))).lower()}")
    if outbox.get("scheduled_for"):
        print(f"- scheduled_for: {outbox.get('scheduled_for')}")
    if result.get("delivery"):
        print("Delivery:")
        print(f"- mode: {result['delivery'].get('mode')}")
        print(f"- delivered: {str(bool(result['delivery'].get('delivered'))).lower()}")
        print(f"- reason: {result['delivery'].get('reason')}")


def _print_outbox(user_id: str) -> None:
    print("Fitness Recall Outbox")
    print()
    print(f"User: {user_id}")
    items = fitness_recall_outbox.list_outbox_items(user_id)
    print(f"Items: {len(items)}")
    for item in items:
        metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
        print(f"- {item.get('message_id')} | {item.get('status')} | {item.get('recall_type')} | {metadata.get('date')}")


def _print_send_pending(result: dict[str, Any]) -> None:
    print("Fitness Recall Send Pending")
    print()
    print(f"User: {result['user_id']}")
    print(f"Message ID: {result['message_id']}")
    print(f"Delivery mode: {result['delivery_mode']}")
    if result.get("error"):
        print(f"Error: {result['error']}")
    outbox = result.get("outbox") or {}
    print(f"Outbox status: {outbox.get('status')}")
    delivery = result.get("delivery") or {}
    if delivery:
        print(f"Delivered: {str(bool(delivery.get('delivered'))).lower()}")
        print(f"Reason: {delivery.get('reason')}")
        print(f"Exit code: {delivery.get('exit_code')}")
        if delivery.get("command_preview"):
            print(f"Command preview: {delivery.get('command_preview')}")


def _print_scheduled_run(result: dict[str, Any]) -> None:
    print("Fitness Scheduled Recall Worker")
    print()
    print(f"User: {result['user_id']}")
    print(f"Date: {result['date']}")
    print(f"Scheduler enabled: {str(bool(result.get('scheduler_enabled'))).lower()}")
    print(f"Channel: {result['channel']}")
    print(f"Delivery mode: {result['delivery_mode']}")
    print(f"Recall enabled: {result.get('recall_enabled')}")
    print(f"Opportunity: {result.get('opportunity')}")
    print(f"Should send: {str(bool(result.get('should_send'))).lower()}")
    print(f"Blocked reason: {result.get('blocked_reason')}")
    outbox = result.get("outbox") or {}
    print("Outbox:")
    print(f"- status: {outbox.get('status')}")
    print(f"- message_id: {outbox.get('message_id')}")
    print(f"- duplicate: {str(bool(outbox.get('duplicate'))).lower()}")
    delivery = result.get("delivery") or {}
    if delivery:
        print("Delivery:")
        print(f"- mode: {delivery.get('mode')}")
        print(f"- delivered: {str(bool(delivery.get('delivered'))).lower()}")
        print(f"- reason: {delivery.get('reason')}")


def _print_scheduled_run_all(result: dict[str, Any]) -> None:
    summary = result.get("summary", {})
    print("Scheduled Recall Run All")
    print()
    print(f"Users checked: {summary.get('users_checked')}")
    print(f"Eligible: {summary.get('eligible')}")
    print(f"Sent: {summary.get('sent')}")
    print(f"Pending: {summary.get('pending')}")
    print(f"Skipped: {summary.get('skipped')}")
    print(f"Failed: {summary.get('failed')}")
    print()
    for user_id, user_result in (result.get("results") or {}).items():
        outbox = user_result.get("outbox") if isinstance(user_result.get("outbox"), dict) else {}
        delivery = user_result.get("delivery") if isinstance(user_result.get("delivery"), dict) else {}
        print(f"{user_id}:")
        print(f"- scheduler: {'enabled' if user_result.get('scheduler_enabled') else 'disabled'}")
        print(f"- recall: {user_result.get('recall_enabled')}")
        print(f"- opportunity: {user_result.get('opportunity')}")
        print(f"- blocked_reason: {user_result.get('blocked_reason')}")
        print(f"- delivery: {delivery.get('mode') or user_result.get('delivery_mode')}")
        print(f"- outbox: {outbox.get('status')}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Fitness recall worker simulator")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_once_parser = subparsers.add_parser("run-once", help="Detect and enqueue one recall opportunity")
    run_once_parser.add_argument("--user", required=True)
    run_once_parser.add_argument("--date", required=True)
    run_once_parser.add_argument("--channel", default="local")
    run_once_parser.add_argument("--dry-run", action="store_true")
    run_once_parser.add_argument("--delivery-mode", choices=sorted(fitness_delivery.SUPPORTED_MODES), default="console")
    run_once_parser.add_argument("--send", action="store_true")
    run_once_parser.add_argument("--confirm-send", action="store_true")
    run_once_parser.add_argument("--now", default=None)

    send_parser = subparsers.add_parser("send-pending", help="Explicitly deliver one pending outbox item")
    send_parser.add_argument("--user", required=True)
    send_parser.add_argument("--message-id", required=True)
    send_parser.add_argument("--delivery-mode", choices=sorted(fitness_delivery.SUPPORTED_MODES), default="dry_run")
    send_parser.add_argument("--dry-run", action="store_true")
    send_parser.add_argument("--send", action="store_true")
    send_parser.add_argument("--confirm-send", action="store_true")
    send_parser.add_argument("--now", default=None)

    list_parser = subparsers.add_parser("list-outbox", help="List recall outbox items")
    list_parser.add_argument("--user", required=True)

    clear_parser = subparsers.add_parser("clear-outbox", help="Clear recall outbox items")
    clear_parser.add_argument("--user", required=True)

    scheduled_parser = subparsers.add_parser("scheduled-run", help="Run recall worker through scheduler gates")
    scheduled_parser.add_argument("--user", required=True)
    scheduled_parser.add_argument("--date", default=fitness_state.get_today_str())
    scheduled_parser.add_argument("--dry-run", action="store_true")
    scheduled_parser.add_argument("--send", action="store_true")
    scheduled_parser.add_argument("--confirm-send", action="store_true")
    scheduled_parser.add_argument("--now", default=None)

    scheduled_all_parser = subparsers.add_parser("scheduled-run-all", help="Run enabled scheduler configs")
    scheduled_all_parser.add_argument("--date", default=fitness_state.get_today_str())
    scheduled_all_parser.add_argument("--dry-run", action="store_true")
    scheduled_all_parser.add_argument("--send", action="store_true")
    scheduled_all_parser.add_argument("--confirm-send", action="store_true")
    scheduled_all_parser.add_argument("--include-default", action="store_true")
    scheduled_all_parser.add_argument("--now", default=None)

    args = parser.parse_args()
    if args.command == "run-once":
        if args.send and not args.confirm_send:
            print("Refusing real send: --send requires --confirm-send")
            return 2
        delivery_mode = "dry_run" if args.dry_run and args.delivery_mode == "console" else args.delivery_mode
        dry_run = args.dry_run or not (args.send and args.confirm_send)
        result = run_once(
            user_id=args.user,
            date=args.date,
            channel=args.channel,
            delivery_mode=delivery_mode,
            dry_run=dry_run,
            send_enabled=args.send,
            confirm_send=args.confirm_send,
            now=args.now,
        )
        _print_run_once(result)
        return 0
    if args.command == "send-pending":
        if args.send and not args.confirm_send:
            print("Refusing real send: --send requires --confirm-send")
            return 2
        delivery_mode = "dry_run" if args.dry_run and args.delivery_mode == "console" else args.delivery_mode
        dry_run = args.dry_run or not (args.send and args.confirm_send)
        result = send_pending(
            user_id=args.user,
            message_id=args.message_id,
            delivery_mode=delivery_mode,
            dry_run=dry_run,
            send_enabled=args.send,
            confirm_send=args.confirm_send,
            now=args.now,
        )
        _print_send_pending(result)
        return 0
    if args.command == "list-outbox":
        _print_outbox(args.user)
        return 0
    if args.command == "clear-outbox":
        fitness_recall_outbox.clear_outbox(args.user)
        print(f"Cleared recall outbox for {args.user}")
        return 0
    if args.command == "scheduled-run":
        if args.send and not args.confirm_send:
            print("Refusing real send: --send requires --confirm-send")
            return 2
        dry_run = args.dry_run or not (args.send and args.confirm_send)
        result = scheduled_run(
            user_id=args.user,
            date=args.date,
            dry_run=dry_run,
            send_enabled=args.send,
            confirm_send=args.confirm_send,
            now=args.now,
        )
        _print_scheduled_run(result)
        return 0
    if args.command == "scheduled-run-all":
        if args.send and not args.confirm_send:
            print("Refusing real send: --send requires --confirm-send")
            return 2
        dry_run = args.dry_run or not (args.send and args.confirm_send)
        result = scheduled_run_all(
            date=args.date,
            dry_run=dry_run,
            send_enabled=args.send,
            confirm_send=args.confirm_send,
            include_default=args.include_default,
            now=args.now,
        )
        _print_scheduled_run_all(result)
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
