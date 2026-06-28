"""One-command portfolio demo for Fitness Agent v0.1."""

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

import fitness_logic  # noqa: E402
import fitness_state  # noqa: E402


USER_TRAINING_PLAN = "今天晚上练臀，怎么吃？"
USER_MEAL_LOG = "中午吃了一碗牛肉面。"
USER_POST_WORKOUT = "练完了，今天强度很大，练后吃什么？"
USER_LAPSE = "我今天吃爆了，不想记了。"
USER_WEEKLY_REVIEW = "这周怎么样？"


def _format_value(value: Any) -> str:
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    if isinstance(value, list):
        return "[]" if not value else "、".join(str(item) for item in value)
    if isinstance(value, dict):
        return "、".join(f"{key}:{item}" for key, item in value.items()) or "{}"
    return str(value)


def _print_block(title: str, body: str | list[str]) -> None:
    print(f"{title}:")
    if isinstance(body, list):
        for item in body:
            print(f"- {item}")
    else:
        print(body)
    print()


def _print_flow(
    number: int,
    title: str,
    user_input: str,
    detected_intent: str,
    tool_chain: list[str],
    agent_reply: str,
    key_state_changes: list[str],
    product_highlight: str,
) -> None:
    print(f"=== Demo {number}: {title} ===\n")
    _print_block("User", user_input)
    _print_block("Detected intent", detected_intent)
    _print_block("Tool chain", " -> ".join(tool_chain))
    _print_block("Agent reply", agent_reply)
    _print_block("Key state changes", key_state_changes)
    _print_block("Product highlight", product_highlight)


def _state_snapshot() -> dict[str, Any]:
    return {
        "daily": fitness_state.get_daily_state(),
        "cycle": fitness_state.get_cycle_state(),
    }


def _get_path(data: dict[str, Any], dotted_path: str) -> Any:
    current: Any = data
    for part in dotted_path.split("."):
        if isinstance(current, dict):
            current = current.get(part)
        else:
            return None
    return current


def _changes(before: dict[str, Any], after: dict[str, Any], paths: list[str]) -> list[str]:
    lines: list[str] = []
    for path in paths:
        old = _get_path(before, path)
        new = _get_path(after, path)
        if old != new:
            lines.append(f"{path}: {_format_value(old)} -> {_format_value(new)}")
        else:
            lines.append(f"{path}: {_format_value(new)}")
    return lines


def _prepare_demo_data() -> None:
    """Create deterministic isolated demo state under agents/fitness/demo_data."""
    if DEMO_DATA_DIR.exists():
        shutil.rmtree(DEMO_DATA_DIR)
    DEMO_DATA_DIR.mkdir(parents=True, exist_ok=True)
    fitness_state.DATA_DIR = DEMO_DATA_DIR

    for name in ["profile.json", "recall_state.json", "memory_candidates.json"]:
        fitness_state.save_json(
            fitness_state.get_user_data_dir("default") / name,
            copy.deepcopy(fitness_state.DEFAULTS[name]),
        )

    today = fitness_state.get_today_str()
    week_key = fitness_state.get_week_key(today)
    week_dates = fitness_state.get_week_date_range(week_key)
    seed_dates = [day for day in week_dates if day != today][:4]

    profile = fitness_state.get_profile()
    profile.update({
        "user_id": "demo_user",
        "goal": {
            "primary": "recomposition",
            "strategy": "train-aware nutrition",
            "notes": "Portfolio demo profile; not real user data.",
        },
        "metrics": {
            "height_cm": None,
            "weight_kg": None,
            "daily_calorie_target": 1600,
            "protein_target_g": 80,
        },
        "preferences": {
            "food_likes": ["酸奶", "鸡蛋", "豆腐", "鱼虾"],
            "food_dislikes": [],
            "training_focus": ["glutes", "lower_body"],
            "feedback_style": "gentle",
        },
        "updated_at": today,
    })
    fitness_state.save_json(fitness_state.get_user_data_dir("default") / "profile.json", profile)

    seed_days = {
        seed_dates[0]: {
            "day_type": "training_day",
            "training": {"planned": True, "type": "glutes", "time": "evening", "intensity": "high", "actual_intensity": "high", "status": "completed"},
            "nutrition": {
                "calorie_budget": 1600,
                "calories_consumed": 1500,
                "calories_remaining": 100,
                "calorie_budget_status": "on_track",
                "protein_target_g": 80,
                "protein_consumed_g": 78,
                "protein_gap_g": 2,
                "meals": [{"description": "早餐"}, {"description": "晚餐"}],
            },
            "workouts": [{"description": "臀腿训练", "training_type": "glutes", "status": "completed"}],
        },
        seed_dates[1]: {
            "day_type": "rest_day",
            "nutrition": {
                "calorie_budget": 1600,
                "calories_consumed": 700,
                "calories_remaining": 900,
                "calorie_budget_status": "on_track",
                "protein_target_g": 80,
                "protein_consumed_g": 30,
                "protein_gap_g": 50,
                "meals": [{"description": "午餐"}],
            },
        },
        seed_dates[2]: {
            "day_type": "training_day",
            "training": {"planned": True, "type": "back", "time": "evening", "intensity": "medium", "actual_intensity": "medium", "status": "completed"},
            "nutrition": {
                "calorie_budget": 1600,
                "calories_consumed": 1750,
                "calories_remaining": -150,
                "calorie_budget_status": "over",
                "protein_target_g": 80,
                "protein_consumed_g": 85,
                "protein_gap_g": 0,
                "meals": [{"description": "午餐"}, {"description": "晚餐"}],
            },
            "special_context": ["social_meal"],
            "workouts": [{"description": "背部训练", "training_type": "back", "status": "completed"}],
        },
        seed_dates[3]: {
            "day_type": "special_day",
            "nutrition": {
                "calorie_budget": 1600,
                "calories_consumed": 1300,
                "calories_remaining": 300,
                "calorie_budget_status": "on_track",
                "protein_target_g": 80,
                "protein_consumed_g": 60,
                "protein_gap_g": 20,
                "meals": [{"description": "恢复餐"}],
            },
            "special_context": ["lapse_recovery"],
            "emotion": {"mood": "unknown", "lapse_risk": "high"},
        },
    }
    for day, patch in seed_days.items():
        fitness_state.update_daily_state({"date": day, **patch}, date=day)

    fitness_state.update_daily_state({
        "date": today,
        "nutrition": {
            "calorie_budget": 1600,
            "calories_consumed": 0,
            "calories_remaining": 1600,
            "calorie_budget_status": "on_track",
            "protein_target_g": 80,
            "protein_consumed_g": 0,
            "protein_gap_g": 80,
            "meals": [],
        },
    }, date=today)

    fitness_state.update_cycle_state({
        "week_key": week_key,
        "week_start_date": week_dates[0],
        "week_end_date": week_dates[-1],
        "workout_completed_count": 3,
        "meal_logging_days": 4,
        "over_budget_days": 1,
        "recovery_success_count": 1,
        "special_context_count": {"聚餐": 1},
        "possible_patterns": ["下肢训练日下午更需要提前安排轻碳水"],
        "weekly_wins": ["练后有补蛋白质和水分", "吃多后没有用断食补偿"],
        "next_week_focus": "训练日下午提前安排一个轻量加餐",
    })


def _demo_training_day_plan() -> None:
    before = _state_snapshot()
    state = fitness_logic.apply_user_context(USER_TRAINING_PLAN)
    plan = fitness_logic.generate_daily_plan(fitness_state.get_profile(), state)
    fitness_state.update_daily_state({"plan_status": "generated"})
    after = _state_snapshot()

    _print_flow(
        1,
        "Training Day Nutrition Plan",
        USER_TRAINING_PLAN,
        "daily_plan / pre_workout_meal",
        ["apply_user_context", "log_workout", "classify_day_type", "generate_daily_plan", "update_daily_state"],
        plan["reply"],
        _changes(before, after, [
            "daily.day_type",
            "daily.training.type",
            "daily.training.time",
            "daily.training.status",
            "daily.plan_status",
        ]),
        "训练感知饮食规划：不是单纯控制热量，而是根据训练部位和训练时间安排练前/练后餐。",
    )


def _demo_meal_log() -> None:
    before = _state_snapshot()
    result = fitness_logic.log_meal(USER_MEAL_LOG)
    after = _state_snapshot()
    nutrition = after["daily"]["nutrition"]

    _print_flow(
        2,
        "Meal Logging And Dynamic Adjustment",
        USER_MEAL_LOG,
        result["intent"],
        ["estimate_calorie_range", "append_meal_log", "update_daily_state", "detect_lapse_risk"],
        result["reply"],
        _changes(before, after, [
            "daily.nutrition.calories_consumed",
            "daily.nutrition.calories_remaining",
            "daily.nutrition.protein_consumed_g",
            "daily.nutrition.calorie_budget_status",
        ]) + [f"daily.nutrition.meals_count: {len(nutrition.get('meals', []))}"],
        "动态调整：用粗略热量区间记录一餐，同时更新剩余热量和蛋白缺口，不要求用户提供精确克数。",
    )


def _demo_post_workout() -> None:
    before = _state_snapshot()
    workout = fitness_logic.log_workout(USER_POST_WORKOUT)
    post = fitness_logic.recommend_post_workout_meal(fitness_state.get_profile(), fitness_state.get_daily_state())
    after = _state_snapshot()

    _print_flow(
        3,
        "Post-Workout Meal Suggestion",
        USER_POST_WORKOUT,
        "post_workout_meal",
        ["log_workout", "update_daily_state", "recommend_post_workout_meal"],
        f"{workout['reply']}\n{post['reply']}",
        _changes(before, after, [
            "daily.training.status",
            "daily.training.actual_intensity",
            "daily.training.post_workout_meal_status",
            "daily.recovery.recovery_need",
        ]),
        "练后恢复优先：高强度训练后建议蛋白质 + 适量碳水，避免用少吃来抵消训练日摄入。",
    )


def _demo_lapse_recovery() -> None:
    before = _state_snapshot()
    result = fitness_logic.generate_lapse_recovery_plan(
        fitness_state.get_profile(),
        fitness_state.get_daily_state(),
        USER_LAPSE,
    )
    fitness_state.update_cycle_state({
        "over_budget_days": 1,
        "recovery_success_count": 2,
        "special_context_count": {"聚餐": 1, "恢复流程": 1},
    })
    after = _state_snapshot()

    _print_flow(
        4,
        "Lapse Recovery",
        USER_LAPSE,
        "lapse_recovery",
        ["detect_lapse_risk", "generate_lapse_recovery_plan", "update_daily_state", "update_cycle_state"],
        result["reply"],
        _changes(before, after, [
            "daily.emotion.lapse_risk",
            "daily.special_context",
            "cycle.recovery_success_count",
        ]) + ["support_mode: recovery_support"],
        "防放弃机制：把“吃爆了”从失败叙事切回恢复流程，强调下一餐接上，避免少吃补偿或额外运动补偿。",
    )


def _demo_weekly_review() -> None:
    before = _state_snapshot()
    cycle = fitness_state.aggregate_week_from_daily()
    result = fitness_logic.generate_weekly_review(fitness_state.get_profile(), cycle)
    after = _state_snapshot()

    _print_flow(
        5,
        "Lightweight Weekly Review",
        USER_WEEKLY_REVIEW,
        "weekly_review",
        ["aggregate_week_from_daily", "generate_weekly_review"],
        result["reply"],
        _changes(before, after, [
            "cycle.workout_completed_count",
            "cycle.meal_logging_days",
            "cycle.complete_logging_days",
            "cycle.over_budget_days",
            "cycle.recovery_success_count",
            "cycle.source",
            "cycle.next_week_focus",
        ]),
        "低压力复盘：同时看训练、记录、超标和恢复，不追求完美，只给下周一个可执行的小重点。",
    )


def main() -> None:
    _prepare_demo_data()
    print("Fitness Agent v0.1 One-Command Demo")
    print(f"Demo state directory: {DEMO_DATA_LABEL}")
    print("Real state under agents/fitness/data is not read or modified.\n")

    _demo_training_day_plan()
    _demo_meal_log()
    _demo_post_workout()
    _demo_lapse_recovery()
    _demo_weekly_review()


if __name__ == "__main__":
    main()
