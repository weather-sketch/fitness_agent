"""Recall outbox state for proactive Fitness recall.

The outbox is a safe buffer before any real channel delivery. It stores what
would be sent, but this module never sends messages.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

import fitness_state


OUTBOX_FILE = "recall_outbox.json"
TERMINAL_OR_ACTIVE_STATUSES = {"pending", "sent"}
VALID_STATUSES = {"pending", "sent", "skipped", "failed"}


def _now(value: str | datetime | None = None) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value)
    return datetime.now()


def _now_str(value: str | datetime | None = None) -> str:
    return _now(value).isoformat(timespec="seconds")


def outbox_path(user_id: str) -> Any:
    return fitness_state.get_user_data_dir(user_id) / OUTBOX_FILE


def default_outbox() -> dict[str, Any]:
    return {"version": 1, "items": []}


def load_outbox(user_id: str) -> dict[str, Any]:
    path = outbox_path(user_id)
    if not path.exists():
        data = default_outbox()
        fitness_state.save_json(path, data)
        return data
    data = fitness_state.load_json(path)
    data.setdefault("version", 1)
    items = data.setdefault("items", [])
    if not isinstance(items, list):
        data["items"] = []
        fitness_state.save_json(path, data)
    return data


def save_outbox(user_id: str, outbox: dict[str, Any]) -> dict[str, Any]:
    outbox.setdefault("version", 1)
    outbox.setdefault("items", [])
    fitness_state.save_json(outbox_path(user_id), outbox)
    return outbox


def clear_outbox(user_id: str) -> dict[str, Any]:
    return save_outbox(user_id, default_outbox())


def list_outbox_items(user_id: str, status: str | None = None) -> list[dict[str, Any]]:
    items = load_outbox(user_id).get("items", []) or []
    if status is None:
        return list(items)
    return [item for item in items if item.get("status") == status]


def find_duplicate_item(
    user_id: str,
    recall_type: str,
    date: str,
    statuses: set[str] | None = None,
) -> dict[str, Any] | None:
    active_statuses = statuses or TERMINAL_OR_ACTIVE_STATUSES
    for item in list_outbox_items(user_id):
        if item.get("status") not in active_statuses:
            continue
        if item.get("recall_type") != recall_type:
            continue
        metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
        if metadata.get("date") == date:
            return item
    return None


def has_recent_active_item(user_id: str, now: str | datetime, min_interval_hours: int = 12) -> bool:
    current = _now(now)
    for item in list_outbox_items(user_id):
        if item.get("status") not in TERMINAL_OR_ACTIVE_STATUSES:
            continue
        created_at = item.get("created_at")
        if not created_at:
            continue
        try:
            created = datetime.fromisoformat(str(created_at))
        except ValueError:
            continue
        age_hours = (current - created).total_seconds() / 3600
        if 0 <= age_hours < min_interval_hours:
            return True
    return False


def build_outbox_item(
    *,
    user_id: str,
    recall_type: str,
    text: str,
    delivery_channel: str,
    delivery_mode: str,
    date: str,
    status: str = "pending",
    scheduled_for: str | None = None,
    skip_reason: str | None = None,
    metadata: dict[str, Any] | None = None,
    now: str | datetime | None = None,
) -> dict[str, Any]:
    if status not in VALID_STATUSES:
        raise ValueError(f"Unsupported outbox status: {status}")
    created_at = _now_str(now)
    return {
        "message_id": f"recall-{_now(now).strftime('%Y%m%dT%H%M%S')}-{uuid4().hex[:8]}",
        "user_id": user_id,
        "recall_type": recall_type,
        "text": text,
        "status": status,
        "delivery_channel": delivery_channel,
        "delivery_mode": delivery_mode,
        "created_at": created_at,
        "scheduled_for": scheduled_for,
        "sent_at": None,
        "skip_reason": skip_reason,
        "metadata": {
            "date": date,
            "cooldown_applied": True,
            "source": "recall_worker",
            **(metadata or {}),
        },
    }


def append_outbox_item(user_id: str, item: dict[str, Any]) -> dict[str, Any]:
    metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
    duplicate = None
    if item.get("status") in TERMINAL_OR_ACTIVE_STATUSES:
        duplicate = find_duplicate_item(
            user_id,
            str(item.get("recall_type") or ""),
            str(metadata.get("date") or ""),
        )
    if duplicate:
        return duplicate
    outbox = load_outbox(user_id)
    outbox.setdefault("items", []).append(item)
    save_outbox(user_id, outbox)
    return item


def _update_item(user_id: str, message_id: str, patch: dict[str, Any]) -> dict[str, Any]:
    outbox = load_outbox(user_id)
    for item in outbox.get("items", []) or []:
        if item.get("message_id") == message_id:
            item.update(patch)
            save_outbox(user_id, outbox)
            return item
    raise fitness_state.FitnessStateError(f"Recall outbox item not found: {message_id}")


def mark_sent(
    user_id: str,
    message_id: str,
    sent_at: str | datetime | None = None,
    delivery_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    patch = {
        "status": "sent",
        "sent_at": _now_str(sent_at),
        "skip_reason": None,
    }
    if delivery_result is not None:
        patch["delivery_result"] = delivery_result
    return _update_item(user_id, message_id, patch)


def mark_skipped(user_id: str, message_id: str, reason: str) -> dict[str, Any]:
    return _update_item(user_id, message_id, {
        "status": "skipped",
        "skip_reason": reason,
    })


def mark_failed(
    user_id: str,
    message_id: str,
    reason: str,
    delivery_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    patch = {
        "status": "failed",
        "skip_reason": reason,
    }
    if delivery_result is not None:
        patch["delivery_result"] = delivery_result
    return _update_item(user_id, message_id, patch)
