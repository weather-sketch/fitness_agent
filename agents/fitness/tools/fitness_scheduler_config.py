"""User-level scheduler configuration for Fitness proactive recall."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import fitness_state


CONFIG_FILE = "scheduler_config.json"
DEFAULT_HOURS = [9, 18, 21]
DEFAULT_TIMEZONE = "Asia/Shanghai"


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def scheduler_config_path(user_id: str) -> Path:
    return fitness_state.get_user_data_dir(user_id) / CONFIG_FILE


def default_scheduler_config(user_id: str) -> dict[str, Any]:
    return {
        "version": 1,
        "enabled": False,
        "user_id": user_id,
        "channel": "wechat",
        "delivery_mode": "openclaw_message",
        "send_enabled": False,
        "confirm_send": False,
        "schedule": {
            "type": "local_interval",
            "preferred_hours": list(DEFAULT_HOURS),
            "timezone": DEFAULT_TIMEZONE,
            "max_runs_per_day": 3,
        },
        "safety": {
            "respect_quiet_hours": True,
            "respect_cooldown": True,
            "respect_duplicate_guard": True,
            "require_recall_opt_in": True,
        },
        "created_at": None,
        "updated_at": None,
    }


def load_scheduler_config(user_id: str) -> dict[str, Any]:
    path = scheduler_config_path(user_id)
    if not path.exists():
        return default_scheduler_config(user_id)
    data = fitness_state.load_json(path)
    default = default_scheduler_config(user_id)
    data.setdefault("version", 1)
    data.setdefault("enabled", False)
    data.setdefault("user_id", user_id)
    data.setdefault("channel", default["channel"])
    data.setdefault("delivery_mode", default["delivery_mode"])
    data.setdefault("send_enabled", False)
    data.setdefault("confirm_send", False)
    schedule = data.setdefault("schedule", {})
    if not isinstance(schedule, dict):
        schedule = {}
        data["schedule"] = schedule
    for key, value in default["schedule"].items():
        schedule.setdefault(key, value)
    safety = data.setdefault("safety", {})
    if not isinstance(safety, dict):
        safety = {}
        data["safety"] = safety
    for key, value in default["safety"].items():
        safety.setdefault(key, value)
    data.setdefault("created_at", None)
    data.setdefault("updated_at", None)
    return data


def save_scheduler_config(user_id: str, config: dict[str, Any]) -> dict[str, Any]:
    config.setdefault("version", 1)
    config["user_id"] = user_id
    fitness_state.save_json(scheduler_config_path(user_id), config)
    return config


def configure_scheduler(
    *,
    user_id: str,
    enabled: bool,
    channel: str = "wechat",
    delivery_mode: str = "openclaw_message",
    preferred_hours: list[int] | None = None,
    timezone: str = DEFAULT_TIMEZONE,
    max_runs_per_day: int = 3,
) -> dict[str, Any]:
    config = load_scheduler_config(user_id)
    created_at = config.get("created_at") or _now()
    config.update({
        "enabled": bool(enabled),
        "user_id": user_id,
        "channel": channel,
        "delivery_mode": delivery_mode,
        "created_at": created_at,
        "updated_at": _now(),
    })
    config["schedule"] = {
        "type": "local_interval",
        "preferred_hours": sorted(set(int(hour) for hour in (preferred_hours or DEFAULT_HOURS))),
        "timezone": timezone,
        "max_runs_per_day": int(max_runs_per_day),
    }
    config.setdefault("safety", default_scheduler_config(user_id)["safety"])
    return save_scheduler_config(user_id, config)


def disable_scheduler(user_id: str) -> dict[str, Any]:
    config = load_scheduler_config(user_id)
    config["enabled"] = False
    config["updated_at"] = _now()
    return save_scheduler_config(user_id, config)


def set_real_send(
    *,
    user_id: str,
    enabled: bool,
    confirm: bool = False,
) -> dict[str, Any]:
    if enabled and not confirm:
        raise ValueError("enable real send requires confirm=True")
    config = load_scheduler_config(user_id)
    config["send_enabled"] = bool(enabled)
    config["confirm_send"] = bool(enabled and confirm)
    config["updated_at"] = _now()
    return save_scheduler_config(user_id, config)


def iter_scheduler_users(include_default: bool = False) -> list[str]:
    users_dir = fitness_state.DATA_DIR / fitness_state.USERS_DIR_NAME
    if not users_dir.exists():
        return []
    users: list[str] = []
    for path in sorted(users_dir.glob(f"*/{CONFIG_FILE}")):
        user_id = path.parent.name
        if user_id == fitness_state.DEFAULT_USER_ID and not include_default:
            continue
        users.append(user_id)
    return users
