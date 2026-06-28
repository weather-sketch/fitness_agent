"""Opt-in recall rules for Fitness Agent.

This module only detects recall opportunities and generates suggested copy.
It does not schedule or send messages.
"""

from __future__ import annotations

from datetime import date as date_cls, datetime, timedelta
from pathlib import Path
from typing import Any

import fitness_state


RECALL_TYPES = {
    "training_day_no_meal_log",
    "post_workout_no_recovery_meal",
    "lapse_recovery_followup",
    "travel_or_social_meal_reset",
    "weekly_review_available",
    "low_data_gentle_restart",
    "none",
}


def _now(value: str | datetime | None = None) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value)
    return datetime.now()


def _date(value: str | date_cls | None = None, now: datetime | None = None) -> str:
    if isinstance(value, date_cls):
        return value.isoformat()
    if value:
        return str(value)
    return (now or datetime.now()).date().isoformat()


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def _daily_path(user_id: str, date: str) -> Path:
    return fitness_state.get_user_data_dir(user_id) / "daily" / f"{date}.json"


def _meal_count(daily: dict[str, Any]) -> int:
    return len(daily.get("nutrition", {}).get("meals", []) or [])


def _completed_workout_count(daily: dict[str, Any]) -> int:
    workouts = daily.get("workouts", []) or []
    completed = [item for item in workouts if item.get("status") == "completed"]
    if completed:
        return len(completed)
    return 1 if daily.get("training", {}).get("status") == "completed" else 0


def _latest_logged_date(user_id: str, today: str) -> str | None:
    daily_dir = fitness_state.get_user_data_dir(user_id) / "daily"
    if not daily_dir.exists():
        return None
    latest: str | None = None
    for path in daily_dir.glob("*.json"):
        try:
            daily = fitness_state.load_json(path)
        except fitness_state.FitnessStateError:
            continue
        if _meal_count(daily) or daily.get("workouts"):
            current = path.stem
            if current <= today and (latest is None or current > latest):
                latest = current
    return latest


def _silence_days(user_id: str, today: str) -> int:
    latest = _latest_logged_date(user_id, today)
    if not latest:
        return 3
    try:
        return max(0, (date_cls.fromisoformat(today) - date_cls.fromisoformat(latest)).days)
    except ValueError:
        return 0


def _context_for(daily: dict[str, Any], silence_days: int) -> dict[str, Any]:
    training = daily.get("training", {})
    return {
        "day_type": daily.get("day_type"),
        "training_type": training.get("type"),
        "training_time": training.get("time"),
        "training_status": training.get("status"),
        "meal_count": _meal_count(daily),
        "special_context": daily.get("special_context", []) or [],
        "lapse_risk": daily.get("emotion", {}).get("lapse_risk"),
        "silence_days": silence_days,
    }


def generate_recall_message(
    recall_type: str,
    context: dict[str, Any] | None = None,
    silence_days: int = 0,
    style: str = "gentle",
) -> str:
    """Generate low-pressure recall copy for one recall type."""
    context = context or {}
    if recall_type == "training_day_no_meal_log":
        return "今天有训练安排，不用补全记录。你只要回我一句“练前吃了”或“还没吃”，我就帮你把晚上的饮食接上。"
    if recall_type == "post_workout_no_recovery_meal":
        return "练完后不用吃很多才算恢复。你只要回我一句“练后吃了什么”，我就帮你看蛋白质和碳水够不够。"
    if recall_type == "lapse_recovery_followup":
        return "不用补前面的记录，也不用靠少吃补偿。你只要回我一句“下一餐准备吃什么”，我就帮你把节奏接回来。"
    if recall_type == "travel_or_social_meal_reset":
        return "不用补旅行或聚餐的账。你只要回我一句“下一餐正常吃”，我就帮你从这一餐重新接上。"
    if recall_type == "weekly_review_available":
        return "这周已经有一些记录了。你只要回我一句“复盘”，我就帮你做一个轻量周报，只看下周一个小重点。"
    if recall_type == "low_data_gentle_restart":
        return "不用补前面的记录。你只要从今天一餐开始，回我一句吃了什么，我就帮你重新接上。"
    return ""


def _detect_type(user_id: str, date: str, now: datetime, daily: dict[str, Any], silence_days: int) -> str:
    training = daily.get("training", {})
    special_context = daily.get("special_context", []) or []
    meal_count = _meal_count(daily)

    if (
        daily.get("day_type") == "training_day"
        and training.get("planned") is True
        and training.get("status") in {"planned", "unknown", None}
        and meal_count <= 1
        and (now.hour >= 14 or training.get("time") in {"afternoon", "evening", "night"})
    ):
        return "training_day_no_meal_log"

    if (
        _completed_workout_count(daily) > 0
        and training.get("post_workout_meal_status") not in {"logged", "suggested"}
        and meal_count <= 1
    ):
        return "post_workout_no_recovery_meal"

    if (
        "lapse_recovery" in special_context
        or daily.get("emotion", {}).get("lapse_risk") == "high"
    ) and meal_count == 0:
        return "lapse_recovery_followup"

    if (
        any(item in special_context for item in ["travel", "social_meal", "alcohol"])
        and meal_count <= 1
    ):
        return "travel_or_social_meal_reset"

    current_week = fitness_state.get_user_data_dir(user_id) / "cycle" / "current_week.json"
    if current_week.exists() and now.weekday() >= 5:
        try:
            cycle = fitness_state.load_json(current_week)
            if (
                len(cycle.get("days_with_logs", []) or []) >= 3
                or int(cycle.get("meal_logging_days") or 0) >= 3
                or int(cycle.get("workout_completed_count") or 0) >= 1
            ):
                return "weekly_review_available"
        except fitness_state.FitnessStateError:
            pass

    if silence_days >= 2 and not special_context:
        return "low_data_gentle_restart"

    return "none"


def detect_recall_opportunity(
    user_id: str = "default",
    date: str | date_cls | None = None,
    now: str | datetime | None = None,
) -> dict[str, Any]:
    """Detect one recall opportunity without sending anything."""
    current_now = _now(now)
    current_date = _date(date, current_now)
    daily = fitness_state.get_daily_state(user_id=user_id, date=current_date)
    recall_state = fitness_state.get_recall_state(user_id=user_id)
    silence_days = _silence_days(user_id, current_date)
    recall_type = _detect_type(user_id, current_date, current_now, daily, silence_days)
    context = _context_for(daily, silence_days)
    enabled = bool(recall_state.get("enabled"))
    cooldown_until = _parse_datetime(recall_state.get("cooldown_until"))
    in_cooldown = bool(cooldown_until and cooldown_until > current_now)
    should_send = recall_type != "none" and enabled and not in_cooldown
    if recall_type == "none":
        reason = "no_recall_opportunity"
    elif not enabled:
        reason = "recall_disabled"
    elif in_cooldown:
        reason = "cooldown_active"
    else:
        reason = "ready"
    return {
        "user_id": user_id,
        "date": current_date,
        "recall_type": recall_type,
        "should_send": should_send,
        "enabled": enabled,
        "cooldown_until": recall_state.get("cooldown_until"),
        "blocked_reason": reason,
        "silence_days": silence_days,
        "context": context,
        "message": generate_recall_message(
            recall_type,
            context=context,
            silence_days=silence_days,
            style=recall_state.get("preferred_recall_style") or "gentle",
        ),
    }


def update_recall_state_after_recall(
    user_id: str,
    recall_type: str,
    sent: bool = False,
    now: str | datetime | None = None,
) -> dict[str, Any]:
    """Record a recall suggestion/send outcome. sent=False does not create cooldown."""
    current_now = _now(now)
    patch: dict[str, Any] = {
        "last_recall_type": recall_type,
    }
    if sent:
        patch.update({
            "last_recall_at": current_now.isoformat(timespec="seconds"),
            "recall_count_recent": int(fitness_state.get_recall_state(user_id=user_id).get("recall_count_recent") or 0) + 1,
            "cooldown_until": (current_now + timedelta(days=1)).isoformat(timespec="seconds"),
        })
    return fitness_state.update_recall_state(patch, user_id=user_id)


def set_recall_opt_in(user_id: str = "default", enabled: bool = True) -> dict[str, Any]:
    """Enable or disable recall suggestions for one user."""
    patch = {
        "enabled": bool(enabled),
        "preferred_recall_style": "gentle",
    }
    if not enabled:
        patch.update({"cooldown_until": None})
    return fitness_state.update_recall_state(patch, user_id=user_id)
