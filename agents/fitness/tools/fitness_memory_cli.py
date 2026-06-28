"""Admin CLI for Fitness memory candidate review."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import fitness_memory  # noqa: E402
import fitness_state  # noqa: E402


def _print_json(payload: dict[str, Any] | list[dict[str, Any]]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Fitness Agent memory candidate review CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="List memory candidates")
    list_parser.add_argument("--user", default="default")
    list_parser.add_argument("--status", default=None)

    active_parser = subparsers.add_parser("active", help="Show active preferences")
    active_parser.add_argument("--user", default="default")

    for command in ["approve", "reject", "archive"]:
        sub = subparsers.add_parser(command, help=f"{command} one memory candidate")
        sub.add_argument("--user", default="default")
        sub.add_argument("--candidate-id", required=True)
        sub.add_argument("--note", default=None)

    args = parser.parse_args()
    try:
        if args.command == "list":
            _print_json(fitness_memory.list_memory_candidates(user_id=args.user, status=args.status))
            return
        if args.command == "active":
            _print_json(fitness_memory.get_active_preferences(user_id=args.user))
            return
        if args.command == "approve":
            _print_json(fitness_memory.approve_memory_candidate(args.user, args.candidate_id, args.note))
            return
        if args.command == "reject":
            _print_json(fitness_memory.reject_memory_candidate(args.user, args.candidate_id, args.note))
            return
        if args.command == "archive":
            _print_json(fitness_memory.archive_memory_candidate(args.user, args.candidate_id, args.note))
            return
    except fitness_state.FitnessStateError as exc:
        _print_json({"ok": False, "error": str(exc)})
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
