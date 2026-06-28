"""Generate local scheduler snippets for Fitness proactive recall.

This tool prints launchd plist or cron lines. It never installs cron entries.
launchd writes are dry-run by default and require --write --confirm-write.
"""

from __future__ import annotations

import argparse
import plistlib
import sys
from pathlib import Path


WORKSPACE = Path("/Users/leo/.openclaw/workspace")
PYTHON = "/usr/bin/python3"
WORKER = "agents/fitness/tools/fitness_recall_worker.py"
LOG_DIR = WORKSPACE / "agents" / "fitness" / "logs" / "scheduler"


def _parse_time(value: str) -> tuple[int, int]:
    try:
        hour_s, minute_s = value.split(":", 1)
        hour = int(hour_s)
        minute = int(minute_s)
    except (TypeError, ValueError) as exc:
        raise argparse.ArgumentTypeError("--time must use HH:MM") from exc
    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
        raise argparse.ArgumentTypeError("--time must use a valid 24-hour HH:MM")
    return hour, minute


def _scheduled_command(user_id: str, *, real_send: bool = False) -> str:
    command = f"cd {WORKSPACE} && {PYTHON} {WORKER} scheduled-run --user {user_id}"
    if real_send:
        command += " --send --confirm-send"
    return command


def build_launchd_plist(
    *,
    user_id: str,
    time_value: str,
    label: str | None = None,
    real_send: bool = False,
) -> dict:
    hour, minute = _parse_time(time_value)
    safe_user = "".join(char if char.isalnum() or char in {"-", "_", "."} else "_" for char in user_id)
    resolved_label = label or f"com.openclaw.fitness.recall.{safe_user}"
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    return {
        "Label": resolved_label,
        "ProgramArguments": [
            "/bin/sh",
            "-lc",
            _scheduled_command(user_id, real_send=real_send),
        ],
        "StartCalendarInterval": {
            "Hour": hour,
            "Minute": minute,
        },
        "StandardOutPath": str(LOG_DIR / f"{safe_user}.log"),
        "StandardErrorPath": str(LOG_DIR / f"{safe_user}.err.log"),
        "WorkingDirectory": str(WORKSPACE),
    }


def launchd_plist_text(
    *,
    user_id: str,
    time_value: str,
    label: str | None = None,
    real_send: bool = False,
) -> str:
    plist = build_launchd_plist(
        user_id=user_id,
        time_value=time_value,
        label=label,
        real_send=real_send,
    )
    return plistlib.dumps(plist, sort_keys=False).decode("utf-8")


def cron_line(*, user_id: str, time_value: str, real_send: bool = False) -> str:
    hour, minute = _parse_time(time_value)
    safe_user = "".join(char if char.isalnum() or char in {"-", "_", "."} else "_" for char in user_id)
    command = _scheduled_command(user_id, real_send=real_send)
    return (
        f"{minute} {hour} * * * {command} >> "
        f"{LOG_DIR / f'{safe_user}.log'} 2>&1"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Fitness scheduler launchd/cron snippets")
    subparsers = parser.add_subparsers(dest="command", required=True)

    print_launchd = subparsers.add_parser("print-launchd")
    print_launchd.add_argument("--user", required=True)
    print_launchd.add_argument("--time", required=True)
    print_launchd.add_argument("--label", default=None)
    print_launchd.add_argument("--dry-run", action="store_true")
    print_launchd.add_argument("--real-send", action="store_true")

    write_launchd = subparsers.add_parser("write-launchd")
    write_launchd.add_argument("--user", required=True)
    write_launchd.add_argument("--time", required=True)
    write_launchd.add_argument("--label", required=True)
    write_launchd.add_argument("--dry-run", action="store_true")
    write_launchd.add_argument("--write", action="store_true")
    write_launchd.add_argument("--confirm-write", action="store_true")
    write_launchd.add_argument("--real-send", action="store_true")

    print_cron = subparsers.add_parser("print-cron")
    print_cron.add_argument("--user", required=True)
    print_cron.add_argument("--time", required=True)
    print_cron.add_argument("--real-send", action="store_true")

    args = parser.parse_args()
    if args.command == "print-launchd":
        print(launchd_plist_text(
            user_id=args.user,
            time_value=args.time,
            label=args.label,
            real_send=args.real_send,
        ), end="")
        return 0
    if args.command == "write-launchd":
        text = launchd_plist_text(
            user_id=args.user,
            time_value=args.time,
            label=args.label,
            real_send=args.real_send,
        )
        target = Path.home() / "Library" / "LaunchAgents" / f"{args.label}.plist"
        if not (args.write and args.confirm_write):
            print("Fitness Scheduler launchd write dry-run")
            print(f"Would write: {target}")
            print("Pass --write --confirm-write to write the plist file.")
            print()
            print(text, end="")
            return 0
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        print(f"Wrote launchd plist: {target}")
        return 0
    if args.command == "print-cron":
        print(cron_line(user_id=args.user, time_value=args.time, real_send=args.real_send))
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
