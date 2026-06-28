"""Local main-agent routing adapter for Fitness Agent integration tests."""

from __future__ import annotations

from typing import Any

from handler import handle_fitness_message


def _message_fields(message: str | dict[str, Any], user_id: str, channel: str) -> tuple[str, str, str]:
    if isinstance(message, dict):
        text = str(message.get("text") or message.get("user_text") or "")
        return text, str(message.get("user_id") or user_id or "default"), str(message.get("channel") or channel or "local")
    return str(message), user_id or "default", channel or "local"


def route_fitness_message(message: str | dict[str, Any], user_id: str = "default", channel: str = "local") -> dict[str, Any]:
    """Return a safe main-agent routing result for one user message.

    This adapter is intentionally small: it mirrors the desired OpenClaw binding
    without touching the runtime. User-visible output is only the handler reply.
    """
    user_text, routed_user_id, routed_channel = _message_fields(message, user_id, channel)
    try:
        result = handle_fitness_message(user_text, user_id=routed_user_id, channel=routed_channel)
    except Exception as exc:  # pragma: no cover - exact exception type depends on runtime state
        return {
            "handled": False,
            "reply": "",
            "fallback": True,
            "error": f"{type(exc).__name__}: {exc}",
            "user_id": routed_user_id,
            "channel": routed_channel,
        }

    if not result.get("handled"):
        return {
            "handled": False,
            "reply": "",
            "fallback": True,
            "intent": result.get("intent", "unknown"),
            "user_id": routed_user_id,
            "channel": routed_channel,
        }

    return {
        "handled": True,
        "reply": str(result.get("reply", "")).strip(),
        "fallback": False,
        "intent": result.get("intent"),
        "user_id": routed_user_id,
        "channel": routed_channel,
    }
