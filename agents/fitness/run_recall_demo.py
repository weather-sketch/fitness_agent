"""Portfolio demo for Fitness Agent opt-in recall rules."""

from __future__ import annotations

import copy
import shutil
import sys
from pathlib import Path
from typing import Any


AGENT_ROOT = Path(__file__).resolve().parent
TOOLS_DIR = AGENT_ROOT / "tools"
DEMO_DATA_DIR = AGENT_ROOT / "demo_data"
DEMO_DATA_LABEL = "agents/fitness/demo_data"

if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import fitness_recall  # noqa: E402
import fitness_state  # noqa: E402


def _print_block(title: str, payload: str | dict[str, Any]) -> None:
    print(f"{title}:")
    if isinstance(payload, dict):
        for key, value in payload.items():
            print(f"- {key}: {value}")
    else:
        print(payload)
    print()


def _reset_demo_data() -> None:
    if DEMO_DATA_DIR.exists():
        shutil.rmtree(DEMO_DATA_DIR)
    DEMO_DATA_DIR.mkdir(parents=True, exist_ok=True)
    fitness_state.DATA_DIR = DEMO_DATA_DIR


def _ensure_demo_user(user_id: str) -> None:
    for name in ["profile.json", "recall_state.json", "memory_candidates.json"]:
        fitness_state.save_json(
            fitness_state.get_user_data_dir(user_id) / name,
            copy.deepcopy(fitness_state.DEFAULTS[name]),
        )
    fitness_state.ensure_user_state(user_id=user_id)


def _show(number: int, title: str, opportunity: dict[str, Any]) -> None:
    print(f"=== Recall Demo {number}: {title} ===\n")
    _print_block("Recall result", {
        "recall_type": opportunity["recall_type"],
        "enabled": opportunity["enabled"],
        "should_send": opportunity["should_send"],
        "blocked_reason": opportunity["blocked_reason"],
    })
    _print_block("Suggested message", opportunity["message"])


def main() -> None:
    _reset_demo_data()
    today = fitness_state.get_today_str()
    now = f"{today}T18:00:00"
    user_id = "default"
    _ensure_demo_user(user_id)

    print("Fitness Agent v0.2 Step 5 Recall Demo")
    print(f"Demo state directory: {DEMO_DATA_LABEL}")
    print("Real state under agents/fitness/data is not read or modified.\n")

    fitness_state.update_daily_state({
        "date": today,
        "day_type": "training_day",
        "training": {
            "planned": True,
            "type": "glutes",
            "time": "evening",
            "status": "planned",
            "post_workout_meal_status": "unknown",
        },
        "nutrition": {"meals": []},
    }, user_id=user_id, date=today)

    opportunity = fitness_recall.detect_recall_opportunity(user_id=user_id, date=today, now=now)
    _show(1, "Opt-in 前只生成机会，不建议发送", opportunity)

    fitness_recall.set_recall_opt_in(user_id=user_id, enabled=True)
    opportunity = fitness_recall.detect_recall_opportunity(user_id=user_id, date=today, now=now)
    _show(2, "Opt-in 后训练日低压力召回", opportunity)

    lapse_user = "lapse_demo"
    _ensure_demo_user(lapse_user)
    fitness_recall.set_recall_opt_in(user_id=lapse_user, enabled=True)
    fitness_state.update_daily_state({
        "date": today,
        "special_context": ["lapse_recovery"],
        "emotion": {"lapse_risk": "high"},
        "nutrition": {"meals": []},
    }, user_id=lapse_user, date=today)
    opportunity = fitness_recall.detect_recall_opportunity(user_id=lapse_user, date=today, now=now)
    _show(3, "超标后恢复跟进", opportunity)

    low_data_user = "low_data_demo"
    _ensure_demo_user(low_data_user)
    fitness_recall.set_recall_opt_in(user_id=low_data_user, enabled=True)
    opportunity = fitness_recall.detect_recall_opportunity(user_id=low_data_user, date=today, now=now)
    _show(4, "低数据轻量重启", opportunity)

    fitness_recall.set_recall_opt_in(user_id=user_id, enabled=False)
    opportunity = fitness_recall.detect_recall_opportunity(user_id=user_id, date=today, now=now)
    _show(5, "Opt-out 后仍可检测机会，但不建议发送", opportunity)


if __name__ == "__main__":
    main()
