"""OpenClaw-ready integration scaffold for Fitness Agent.

This module does not import or call a real OpenClaw runtime. It converts an
OpenClaw-like event into the local channel message schema, calls the Fitness
channel adapter, and formats an OpenClaw-compatible response payload.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any


AGENT_ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = AGENT_ROOT / "tools"

for path in (AGENT_ROOT, TOOLS_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from channel_adapter import handle_channel_message  # noqa: E402


AGENT_NAME = "fitness"
SUPPORTED_TYPES = {"text", "image", "command"}


def _text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def normalize_openclaw_event(event: dict[str, Any]) -> dict[str, Any]:
    """Normalize an OpenClaw-like event into Fitness channel message schema."""
    message = event.get("message") if isinstance(event.get("message"), dict) else {}
    message_type = _text(message.get("type") or event.get("type") or "text", "text").lower()
    channel = _text(event.get("channel") or event.get("source") or "openclaw", "openclaw")
    sender_id = _text(event.get("sender_id") or event.get("sender") or "unknown_sender", "unknown_sender")
    if not sender_id.strip():
        sender_id = "unknown_sender"
    return {
        "message_id": _text(event.get("message_id") or event.get("event_id") or "openclaw-event"),
        "channel": channel,
        "sender_id": sender_id,
        "conversation_id": _text(event.get("conversation_id") or event.get("conversation") or "openclaw-conversation"),
        "type": message_type,
        "text": _text(message.get("text") or event.get("text")),
        "image_path": message.get("image_path") or event.get("image_path"),
        "timestamp": event.get("timestamp"),
        "metadata": {
            **(event.get("metadata") if isinstance(event.get("metadata"), dict) else {}),
            "source": event.get("source") or "openclaw",
            "original_event_id": event.get("event_id"),
        },
    }


def _error_response(code: str, message: str, event: dict[str, Any]) -> dict[str, Any]:
    return {
        "ok": False,
        "handled": False,
        "handoff": False,
        "agent": AGENT_NAME,
        "channel": _text(event.get("channel") or event.get("source") or "openclaw", "openclaw"),
        "conversation_id": _text(event.get("conversation_id") or event.get("conversation") or "openclaw-conversation"),
        "reply": None,
        "state_changed": False,
        "state_summary": {},
        "handoff_payload": None,
        "error": {"code": code, "message": message},
        "debug": {"event": event},
    }


def format_openclaw_response(channel_response: dict[str, Any], original_event: dict[str, Any]) -> dict[str, Any]:
    """Format a channel adapter response as an OpenClaw-compatible payload."""
    channel = channel_response.get("channel") or original_event.get("channel") or "openclaw"
    conversation_id = original_event.get("conversation_id") or original_event.get("conversation") or "openclaw-conversation"
    handled = bool(channel_response.get("handled"))
    handoff = bool(channel_response.get("handoff"))
    reply_text = channel_response.get("reply") or ""
    handoff_payload = None
    reply = None

    if handled and reply_text:
        reply = {"type": "text", "text": reply_text}
    if handoff:
        message = original_event.get("message") if isinstance(original_event.get("message"), dict) else {}
        handoff_payload = {
            "target": "main_agent",
            "reason": "non_fitness_intent",
            "original_text": message.get("text") or original_event.get("text") or "",
            "event": original_event,
        }

    return {
        "ok": True,
        "handled": handled,
        "handoff": handoff,
        "agent": AGENT_NAME,
        "channel": channel,
        "conversation_id": conversation_id,
        "reply": reply,
        "state_changed": bool(channel_response.get("state_changed")),
        "state_summary": channel_response.get("state_summary") or {},
        "handoff_payload": handoff_payload,
        "debug": {
            "channel_response": channel_response,
            "original_event": original_event,
        },
    }


def handle_openclaw_event(
    event: dict[str, Any],
    *,
    provider: str = "demo",
    dry_run: bool = False,
) -> dict[str, Any]:
    """Handle an OpenClaw-like runtime event with the Fitness channel adapter."""
    try:
        channel_message = normalize_openclaw_event(event)
    except Exception as exc:
        return _error_response("normalize_failed", f"{type(exc).__name__}: {exc}", event)

    if channel_message.get("type") not in SUPPORTED_TYPES:
        return _error_response(
            "unsupported_message_type",
            f"Unsupported message type: {channel_message.get('type')}",
            event,
        )

    try:
        channel_response = handle_channel_message(
            channel_message,
            channel=channel_message.get("channel") or "openclaw",
            date=event.get("date"),
            provider=provider,
            dry_run=dry_run,
        )
    except Exception as exc:
        return _error_response("channel_adapter_failed", f"{type(exc).__name__}: {exc}", event)

    response = format_openclaw_response(channel_response, event)
    response["debug"]["normalized_message"] = channel_message
    return response
