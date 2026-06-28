"""CLI for Fitness proactive recall scheduler configuration."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import fitness_scheduler_config  # noqa: E402


def _parse_hours(value: str) -> list[int]:
    hours: list[int] = []
    for raw in value.split(","):
        raw = raw.strip()
        if not raw:
            continue
        hour = int(raw)
        if hour < 0 or hour > 23:
            raise argparse.ArgumentTypeError("--hours must contain values from 0 to 23")
        hours.append(hour)
    if not hours:
        raise argparse.ArgumentTypeError("--hours must contain at least one hour")
    return hours


def _print_config(user_id: str) -> None:
    config = fitness_scheduler_config.load_scheduler_config(user_id)
    schedule = config.get("schedule") if isinstance(config.get("schedule"), dict) else {}
    safety = config.get("safety") if isinstance(config.get("safety"), dict) else {}
    print("Fitness Scheduler Config")
    print()
    print(f"User: {user_id}")
    print(f"enabled: {str(bool(config.get('enabled'))).lower()}")
    print(f"channel: {config.get('channel')}")
    print(f"delivery_mode: {config.get('delivery_mode')}")
    print(f"send_enabled: {str(bool(config.get('send_enabled'))).lower()}")
    print(f"confirm_send: {str(bool(config.get('confirm_send'))).lower()}")
    print("schedule:")
    print(f"- type: {schedule.get('type')}")
    print(f"- preferred_hours: {schedule.get('preferred_hours')}")
    print(f"- timezone: {schedule.get('timezone')}")
    print(f"- max_runs_per_day: {schedule.get('max_runs_per_day')}")
    print("safety:")
    for key in sorted(safety):
        print(f"- {key}: {str(bool(safety.get(key))).lower()}")
    print("delivery fields: stored only in delivery_config.json")


def main() -> int:
    parser = argparse.ArgumentParser(description="Fitness scheduler config CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    configure = subparsers.add_parser("configure")
    configure.add_argument("--user", required=True)
    configure.add_argument("--enable", action="store_true")
    configure.add_argument("--channel", default="wechat")
    configure.add_argument("--delivery-mode", default="openclaw_message")
    configure.add_argument("--hours", type=_parse_hours, default=[9, 18, 21])
    configure.add_argument("--timezone", default=fitness_scheduler_config.DEFAULT_TIMEZONE)
    configure.add_argument("--max-runs-per-day", type=int, default=3)

    show = subparsers.add_parser("show")
    show.add_argument("--user", required=True)

    disable = subparsers.add_parser("disable")
    disable.add_argument("--user", required=True)

    enable_real = subparsers.add_parser("enable-real-send")
    enable_real.add_argument("--user", required=True)
    enable_real.add_argument("--confirm", action="store_true")

    disable_real = subparsers.add_parser("disable-real-send")
    disable_real.add_argument("--user", required=True)

    args = parser.parse_args()
    if args.command == "configure":
        fitness_scheduler_config.configure_scheduler(
            user_id=args.user,
            enabled=args.enable,
            channel=args.channel,
            delivery_mode=args.delivery_mode,
            preferred_hours=args.hours,
            timezone=args.timezone,
            max_runs_per_day=args.max_runs_per_day,
        )
        _print_config(args.user)
        return 0
    if args.command == "show":
        _print_config(args.user)
        return 0
    if args.command == "disable":
        fitness_scheduler_config.disable_scheduler(args.user)
        _print_config(args.user)
        return 0
    if args.command == "enable-real-send":
        if not args.confirm:
            print("Refusing scheduler real send: enable-real-send requires --confirm")
            return 2
        fitness_scheduler_config.set_real_send(user_id=args.user, enabled=True, confirm=True)
        _print_config(args.user)
        return 0
    if args.command == "disable-real-send":
        fitness_scheduler_config.set_real_send(user_id=args.user, enabled=False, confirm=False)
        _print_config(args.user)
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
