"""Admin CLI for Fitness opt-in recall suggestions."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import fitness_recall  # noqa: E402
import fitness_state  # noqa: E402


def _print_json(payload: dict[str, Any] | list[dict[str, Any]]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Fitness Agent recall suggestion CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    status = subparsers.add_parser("status", help="Show recall state for one user")
    status.add_argument("--user", default="default")

    opt_in = subparsers.add_parser("opt-in", help="Enable opt-in recall suggestions")
    opt_in.add_argument("--user", default="default")

    opt_out = subparsers.add_parser("opt-out", help="Disable recall suggestions")
    opt_out.add_argument("--user", default="default")

    suggest = subparsers.add_parser("suggest", help="Generate a recall suggestion without sending it")
    suggest.add_argument("--user", default="default")
    suggest.add_argument("--type", default=None, choices=sorted(fitness_recall.RECALL_TYPES - {"none"}))

    args = parser.parse_args()
    try:
        if args.command == "status":
            _print_json(fitness_state.get_recall_state(user_id=args.user))
            return
        if args.command == "opt-in":
            _print_json(fitness_recall.set_recall_opt_in(user_id=args.user, enabled=True))
            return
        if args.command == "opt-out":
            _print_json(fitness_recall.set_recall_opt_in(user_id=args.user, enabled=False))
            return
        if args.command == "suggest":
            if args.type:
                state = fitness_state.get_recall_state(user_id=args.user)
                _print_json({
                    "user_id": args.user,
                    "recall_type": args.type,
                    "should_send": False,
                    "enabled": bool(state.get("enabled")),
                    "blocked_reason": "manual_preview",
                    "message": fitness_recall.generate_recall_message(
                        args.type,
                        style=state.get("preferred_recall_style") or "gentle",
                    ),
                })
            else:
                _print_json(fitness_recall.detect_recall_opportunity(user_id=args.user))
            return
    except fitness_state.FitnessStateError as exc:
        _print_json({"ok": False, "error": str(exc)})
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
