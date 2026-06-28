"""User-level delivery configuration for Fitness Agent."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import fitness_state


CONFIG_FILE = "delivery_config.json"


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def delivery_config_path(user_id: str) -> Path:
    return fitness_state.get_user_data_dir(user_id) / CONFIG_FILE


def default_delivery_config() -> dict[str, Any]:
    return {"version": 1, "channels": {}}


def load_delivery_config(user_id: str) -> dict[str, Any]:
    path = delivery_config_path(user_id)
    if not path.exists():
        return default_delivery_config()
    data = fitness_state.load_json(path)
    data.setdefault("version", 1)
    channels = data.setdefault("channels", {})
    if not isinstance(channels, dict):
        data["channels"] = {}
    return data


def save_delivery_config(user_id: str, config: dict[str, Any]) -> dict[str, Any]:
    config.setdefault("version", 1)
    config.setdefault("channels", {})
    fitness_state.save_json(delivery_config_path(user_id), config)
    return config


def configure_wechat_delivery(
    *,
    user_id: str,
    target: str,
    account_id: str | None = None,
    enabled: bool = False,
    allow_real_send: bool = False,
) -> dict[str, Any]:
    config = load_delivery_config(user_id)
    channels = config.setdefault("channels", {})
    previous = channels.get("wechat") if isinstance(channels.get("wechat"), dict) else {}
    created_at = previous.get("created_at") or _now()
    channels["wechat"] = {
        "delivery_mode": "openclaw_message",
        "openclaw_channel": "openclaw-weixin",
        "target": target,
        "account_id": account_id,
        "enabled": bool(enabled),
        "allow_real_send": bool(allow_real_send),
        "created_at": created_at,
        "updated_at": _now(),
    }
    return save_delivery_config(user_id, config)


def get_channel_config(user_id: str, channel: str = "wechat") -> dict[str, Any] | None:
    config = load_delivery_config(user_id)
    channel_config = config.get("channels", {}).get(channel)
    return channel_config if isinstance(channel_config, dict) else None


def disable_channel(user_id: str, channel: str = "wechat") -> dict[str, Any]:
    config = load_delivery_config(user_id)
    channels = config.setdefault("channels", {})
    current = channels.get(channel) if isinstance(channels.get(channel), dict) else {}
    current["enabled"] = False
    current["updated_at"] = _now()
    channels[channel] = current
    return save_delivery_config(user_id, config)
