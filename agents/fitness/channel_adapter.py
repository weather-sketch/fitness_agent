"""Channel adapter contract for Fitness Agent.

This module normalizes local/OpenClaw/IM-like messages and routes them to the
Fitness Agent without depending on any real channel SDK.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any


AGENT_ROOT = Path(__file__).resolve().parent
TOOLS_DIR = AGENT_ROOT / "tools"

for path in (AGENT_ROOT, TOOLS_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from handler import handle_fitness_message  # noqa: E402
import fitness_memory  # noqa: E402
import fitness_recall  # noqa: E402
import fitness_state  # noqa: E402
import fitness_vision  # noqa: E402


SUPPORTED_MESSAGE_TYPES = {"text", "image", "command"}


def _safe_segment(value: str | None, fallback: str = "user") -> str:
    raw = str(value or fallback).strip() or fallback
    safe = "".join(char if char.isalnum() or char in {"-", "_"} else "_" for char in raw)
    return safe.strip("_") or fallback


def resolve_channel_user_id(
    channel: str,
    sender_id: str | None,
    default_user_id: str | None = None,
) -> str:
    """Resolve a stable Fitness user id from channel and sender information."""
    if default_user_id:
        return _safe_segment(default_user_id, fallback="default")
    safe_channel = _safe_segment(channel or "local", fallback="local")
    safe_sender = _safe_segment(sender_id or "anonymous", fallback="anonymous")
    return f"{safe_channel}_{safe_sender}"


def _message_channel(message: dict[str, Any], channel: str) -> str:
    return str(message.get("channel") or channel or "local")


def _message_type(message: dict[str, Any]) -> str:
    return str(message.get("type") or "text").lower()


def _state_summary(user_id: str, date: str | None = None) -> dict[str, Any]:
    if not fitness_state.get_user_data_dir(user_id).exists():
        return {}
    daily = fitness_state.get_daily_state(user_id=user_id, date=date)
    nutrition = daily.get("nutrition", {})
    return {
        "date": daily.get("date"),
        "day_type": daily.get("day_type"),
        "training_type": daily.get("training", {}).get("type"),
        "meal_count": len(nutrition.get("meals", []) or []),
        "calories_consumed": nutrition.get("calories_consumed"),
        "calories_remaining": nutrition.get("calories_remaining"),
        "memory_candidate_count": len(fitness_memory.list_memory_candidates(user_id=user_id)),
        "recall_enabled": bool(fitness_state.get_recall_state(user_id=user_id).get("enabled")),
    }


def _response(
    *,
    handled: bool,
    handoff: bool,
    channel: str,
    user_id: str,
    message_type: str,
    intent: str,
    reply: str,
    state_changed: bool = False,
    state_summary: dict[str, Any] | None = None,
    tool_chain: list[str] | None = None,
    debug: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "handled": handled,
        "handoff": handoff,
        "channel": channel,
        "user_id": user_id,
        "message_type": message_type,
        "intent": intent,
        "reply": reply.strip(),
        "state_changed": state_changed,
        "state_summary": state_summary or {},
        "tool_chain": tool_chain or [],
        "debug": debug or {},
    }


def _help_reply() -> str:
    return "\n".join([
        "Fitness Agent 可以帮你处理：",
        "- 训练日怎么吃、练前/练后吃什么",
        "- 饮食记录、吃超后的低压力恢复",
        "- 图片粗略记录一餐",
        "- 候选记忆查看与 recall 开关",
        "",
        "可用命令：/recall status、/recall on、/recall off、/memory candidates",
    ])


def _handle_command(text: str, user_id: str, channel: str, message: dict[str, Any], date: str | None) -> dict[str, Any]:
    command = text.strip().lower()
    before = _state_summary(user_id, date=date)
    if command in {"/fitness help", "/fitness", "help"}:
        return _response(
            handled=True,
            handoff=False,
            channel=channel,
            user_id=user_id,
            message_type="command",
            intent="fitness_help",
            reply=_help_reply(),
            state_changed=False,
            state_summary=before,
            tool_chain=["fitness_help"],
            debug={"message": message},
        )

    if command == "/recall on":
        fitness_recall.set_recall_opt_in(user_id=user_id, enabled=True)
        after = _state_summary(user_id, date=date)
        return _response(
            handled=True,
            handoff=False,
            channel=channel,
            user_id=user_id,
            message_type="command",
            intent="recall_opt_in",
            reply="已开启 Fitness 低压力 recall 建议。当前只是生成建议，不会主动发送消息。",
            state_changed=True,
            state_summary=after,
            tool_chain=["set_recall_opt_in"],
            debug={"before": before, "after": after},
        )

    if command == "/recall off":
        fitness_recall.set_recall_opt_in(user_id=user_id, enabled=False)
        after = _state_summary(user_id, date=date)
        return _response(
            handled=True,
            handoff=False,
            channel=channel,
            user_id=user_id,
            message_type="command",
            intent="recall_opt_out",
            reply="已关闭 Fitness recall 建议，不会主动打扰你。",
            state_changed=True,
            state_summary=after,
            tool_chain=["set_recall_opt_in"],
            debug={"before": before, "after": after},
        )

    if command == "/recall status":
        recall_state = fitness_state.get_recall_state(user_id=user_id)
        enabled = bool(recall_state.get("enabled"))
        return _response(
            handled=True,
            handoff=False,
            channel=channel,
            user_id=user_id,
            message_type="command",
            intent="recall_status",
            reply=f"Fitness recall 当前状态：{'已开启' if enabled else '未开启'}。这里只返回建议状态，不会主动推送。",
            state_changed=False,
            state_summary=_state_summary(user_id, date=date),
            tool_chain=["get_recall_state"],
            debug={"recall_state": recall_state},
        )

    if command == "/memory candidates":
        candidates = fitness_memory.list_memory_candidates(user_id=user_id)
        if not candidates:
            reply = "当前没有待确认的 Fitness 候选记忆。"
        else:
            lines = ["当前 Fitness 候选记忆："]
            for candidate in candidates[:5]:
                lines.append(
                    f"- {candidate.get('key')} ({candidate.get('type')}, {candidate.get('status')}, evidence={candidate.get('evidence_count')})"
                )
            if len(candidates) > 5:
                lines.append(f"- 还有 {len(candidates) - 5} 条未显示。")
            reply = "\n".join(lines)
        return _response(
            handled=True,
            handoff=False,
            channel=channel,
            user_id=user_id,
            message_type="command",
            intent="memory_candidates",
            reply=reply,
            state_changed=False,
            state_summary=_state_summary(user_id, date=date),
            tool_chain=["list_memory_candidates"],
            debug={"candidate_count": len(candidates)},
        )

    return _response(
        handled=True,
        handoff=False,
        channel=channel,
        user_id=user_id,
        message_type="command",
        intent="fitness_help",
        reply="这个 Fitness 命令我还不支持。\n\n" + _help_reply(),
        state_changed=False,
        state_summary=before,
        tool_chain=["fitness_help"],
        debug={"unknown_command": text, "message": message},
    )


def _handle_text(text: str, user_id: str, channel: str, message: dict[str, Any], date: str | None) -> dict[str, Any]:
    before_exists = fitness_state.get_user_data_dir(user_id).exists()
    before = _state_summary(user_id, date=date) if before_exists else {}
    result = handle_fitness_message(text, user_id=user_id, channel=channel, date=date)
    if not result.get("handled"):
        return _response(
            handled=False,
            handoff=True,
            channel=channel,
            user_id=user_id,
            message_type="text",
            intent=result.get("intent", "unknown"),
            reply="",
            state_changed=False,
            state_summary={},
            tool_chain=result.get("tool_chain", []),
            debug={"handler_result": result, "message": message, "state_existed_before": before_exists},
        )
    after = _state_summary(user_id, date=date)
    return _response(
        handled=True,
        handoff=False,
        channel=channel,
        user_id=user_id,
        message_type="text",
        intent=result.get("intent", "unknown"),
        reply=result.get("reply", ""),
        state_changed=before != after or bool(result.get("state_changes")),
        state_summary=after,
        tool_chain=result.get("tool_chain", []),
        debug={"handler_result": result, "message": message},
    )


def _handle_image(
    message: dict[str, Any],
    user_id: str,
    channel: str,
    date: str | None,
    provider: str,
) -> dict[str, Any]:
    image_path = message.get("image_path") or message.get("image")
    note = message.get("text")
    before = _state_summary(user_id, date=date)
    try:
        result = fitness_vision.log_meal_from_image(
            image_path,
            user_id=user_id,
            note=note,
            date=date,
            provider=provider,
        )
    except (fitness_state.FitnessStateError, TypeError, ValueError) as exc:
        return _response(
            handled=True,
            handoff=False,
            channel=channel,
            user_id=user_id,
            message_type="image",
            intent="food_photo_log_failed",
            reply="这张图我现在没法读取，你可以重新发一次，或者直接告诉我吃了什么。",
            state_changed=False,
            state_summary=before,
            tool_chain=["log_meal_from_image"],
            debug={"error": f"{type(exc).__name__}: {exc}", "message": message},
        )

    daily = result["daily_state"]
    nutrition = daily.get("nutrition", {})
    image_result = result["image_result"]
    after = {
        "logged_date": daily.get("date"),
        "meal_count_after": len(nutrition.get("meals", []) or []),
        "calories_consumed": nutrition.get("calories_consumed"),
        "calories_remaining": nutrition.get("calories_remaining"),
        "provider": image_result.get("provider"),
        "provider_status": image_result.get("provider_status"),
        "fallback_used": image_result.get("fallback_used"),
    }
    return _response(
        handled=True,
        handoff=False,
        channel=channel,
        user_id=user_id,
        message_type="image",
        intent="food_photo_log",
        reply=result["reply"],
        state_changed=True,
        state_summary=after,
        tool_chain=["log_meal_from_image"],
        debug={"vision_result": result, "message": message, "before": before},
    )


def handle_channel_message(
    message: dict[str, Any],
    user_id: str | None = None,
    channel: str = "local",
    date: str | None = None,
    provider: str = "demo",
    dry_run: bool = False,
) -> dict[str, Any]:
    """Route a normalized channel message to Fitness Agent and return a response object."""
    current_channel = _message_channel(message, channel)
    resolved_user_id = resolve_channel_user_id(
        current_channel,
        str(message.get("sender_id") or message.get("sender") or ""),
        default_user_id=user_id,
    )
    message_type = _message_type(message)
    if message_type not in SUPPORTED_MESSAGE_TYPES:
        return _response(
            handled=False,
            handoff=True,
            channel=current_channel,
            user_id=resolved_user_id,
            message_type=message_type,
            intent="unknown",
            reply="",
            state_changed=False,
            debug={"reason": "unsupported_message_type", "message": message},
        )
    if dry_run:
        return _response(
            handled=False,
            handoff=False,
            channel=current_channel,
            user_id=resolved_user_id,
            message_type=message_type,
            intent="dry_run",
            reply="",
            state_changed=False,
            debug={"message": message, "provider": provider, "date": date},
        )

    text = str(message.get("text") or "")
    if message_type == "command":
        return _handle_command(text, resolved_user_id, current_channel, message, date)
    if message_type == "image":
        return _handle_image(message, resolved_user_id, current_channel, date, provider)
    return _handle_text(text, resolved_user_id, current_channel, message, date)
