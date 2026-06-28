"""Admin CLI for Fitness Agent state validation, backup, and restore."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import fitness_state  # noqa: E402


def _print_json(payload: dict[str, Any] | list[dict[str, Any]]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Fitness Agent admin CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate", help="Validate one user's state files")
    validate.add_argument("--user", default="default")

    backup = subparsers.add_parser("backup", help="Create one user's state backup")
    backup.add_argument("--user", default="default")
    backup.add_argument("--label", default=None)

    list_backups = subparsers.add_parser("list-backups", help="List one user's backups")
    list_backups.add_argument("--user", default="default")

    restore = subparsers.add_parser("restore", help="Restore one user's state backup")
    restore.add_argument("--user", default="default")
    restore.add_argument("--backup-id", default=None)
    restore_mode = restore.add_mutually_exclusive_group()
    restore_mode.add_argument("--dry-run", action="store_true", help="Preview restore without writing")
    restore_mode.add_argument("--apply", action="store_true", help="Apply restore")

    args = parser.parse_args()
    try:
        if args.command == "validate":
            result = fitness_state.validate_user_state(user_id=args.user)
            _print_json(result)
            raise SystemExit(0 if result["valid"] else 1)
        if args.command == "backup":
            _print_json(fitness_state.create_user_backup(user_id=args.user, label=args.label))
            return
        if args.command == "list-backups":
            _print_json(fitness_state.list_user_backups(user_id=args.user))
            return
        if args.command == "restore":
            dry_run = not args.apply
            _print_json(fitness_state.restore_user_backup(
                user_id=args.user,
                backup_id=args.backup_id,
                dry_run=dry_run,
            ))
            return
    except fitness_state.FitnessStateError as exc:
        _print_json({"ok": False, "error": str(exc)})
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
