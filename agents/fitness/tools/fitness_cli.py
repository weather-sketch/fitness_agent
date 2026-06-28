"""CLI for manually running Fitness Agent v0.1 demo flows."""

from __future__ import annotations

import argparse
import json
from typing import Any

from fitness_logic import (
    apply_user_context,
    generate_daily_plan,
    generate_lapse_recovery_plan,
    generate_weekly_review,
    log_meal,
    log_workout,
    recommend_post_workout_meal,
)
from fitness_state import get_cycle_state, get_daily_state, get_profile


def _emit(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    reply = payload.get("reply")
    if reply:
        print("\n--- reply ---")
        print(reply)


def run_daily_plan(text: str) -> dict[str, Any]:
    state = apply_user_context(text)
    profile = get_profile()
    plan = generate_daily_plan(profile, state)
    return {"command": "daily-plan", "state": get_daily_state(), **plan}


def run_log_meal(text: str) -> dict[str, Any]:
    return {"command": "log-meal", **log_meal(text)}


def run_log_workout(text: str) -> dict[str, Any]:
    result = log_workout(text)
    profile = get_profile()
    post = recommend_post_workout_meal(profile, get_daily_state())
    return {"command": "log-workout", **result, "post_workout": post, "reply": f"{result['reply']}\n{post['reply']}"}


def run_lapse(text: str) -> dict[str, Any]:
    profile = get_profile()
    state = get_daily_state()
    return {"command": "lapse", **generate_lapse_recovery_plan(profile, state, text)}


def run_weekly_review() -> dict[str, Any]:
    profile = get_profile()
    cycle = get_cycle_state()
    return {"command": "weekly-review", **generate_weekly_review(profile, cycle)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Fitness Agent v0.1 CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    for command in ["daily-plan", "log-meal", "log-workout", "lapse"]:
        sub = subparsers.add_parser(command)
        sub.add_argument("text")
    subparsers.add_parser("weekly-review")

    args = parser.parse_args()

    if args.command == "daily-plan":
        _emit(run_daily_plan(args.text))
    elif args.command == "log-meal":
        _emit(run_log_meal(args.text))
    elif args.command == "log-workout":
        _emit(run_log_workout(args.text))
    elif args.command == "lapse":
        _emit(run_lapse(args.text))
    elif args.command == "weekly-review":
        _emit(run_weekly_review())


if __name__ == "__main__":
    main()
