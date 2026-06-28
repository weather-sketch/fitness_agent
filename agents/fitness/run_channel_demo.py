"""Showcase demo for Fitness Agent channel adapter."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path
from typing import Any


AGENT_ROOT = Path(__file__).resolve().parent
TOOLS_DIR = AGENT_ROOT / "tools"
CHANNEL_DATA_DIR = AGENT_ROOT / "demo_data" / "channel"
CHANNEL_DATA_LABEL = "agents/fitness/demo_data/channel"
DEMO_ASSETS_DIR = AGENT_ROOT / "demo_assets" / "vision"

for path in (AGENT_ROOT, TOOLS_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from channel_adapter import handle_channel_message, resolve_channel_user_id  # noqa: E402
import fitness_memory  # noqa: E402
import fitness_state  # noqa: E402


def _print_block(title: str, body: str | list[str]) -> None:
    print(f"{title}:")
    if isinstance(body, list):
        for item in body:
            print(f"- {item}")
    else:
        print(body)
    print()


def _reset_demo_state() -> None:
    if CHANNEL_DATA_DIR.exists():
        shutil.rmtree(CHANNEL_DATA_DIR)
    CHANNEL_DATA_DIR.mkdir(parents=True, exist_ok=True)
    fitness_state.DATA_DIR = CHANNEL_DATA_DIR


def _show(number: int, title: str, message: dict[str, Any], response: dict[str, Any]) -> None:
    print(f"=== Channel Demo {number}: {title} ===\n")
    _print_block("Channel message", [
        f"channel: {message.get('channel')}",
        f"sender_id: {message.get('sender_id')}",
        f"type: {message.get('type')}",
        f"text: {message.get('text')}",
    ])
    _print_block("Adapter summary", [
        f"user_id: {response['user_id']}",
        f"handled: {str(response['handled']).lower()}",
        f"handoff: {str(response['handoff']).lower()}",
        f"intent: {response['intent']}",
        f"state_changed: {str(response['state_changed']).lower()}",
    ])
    _print_block("Reply", response.get("reply") or "交还主 Agent 正常处理。")
    if response.get("state_summary"):
        _print_block("State summary", [f"{key}: {value}" for key, value in response["state_summary"].items()])


def main() -> None:
    _reset_demo_state()
    channel = "wechat"
    sender = "demo_user"
    user_id = resolve_channel_user_id(channel, sender)

    print("Fitness Agent v0.4 Channel Adapter Demo")
    print(f"Demo state directory: {CHANNEL_DATA_LABEL}")
    print("Real state under agents/fitness/data is not read or modified.")
    print("This is local message routing only; it does not call WeChat/OpenClaw SDKs or send messages.\n")

    message = {
        "message_id": "msg-001",
        "channel": channel,
        "sender_id": sender,
        "conversation_id": "conv-demo",
        "type": "text",
        "text": "今天晚上练臀，怎么吃？",
        "metadata": {},
    }
    response = handle_channel_message(message, date="2026-06-24")
    _show(1, "WeChat text fitness request", message, response)

    image_message = {
        "message_id": "msg-002",
        "channel": channel,
        "sender_id": sender,
        "conversation_id": "conv-demo",
        "type": "image",
        "text": "午餐",
        "image_path": str(DEMO_ASSETS_DIR / "beef_noodle_demo.jpg"),
        "metadata": {},
    }
    response = handle_channel_message(image_message, date="2026-06-24", provider="demo")
    _show(2, "WeChat image meal log", image_message, response)

    memory_message = {
        "message_id": "msg-003",
        "channel": channel,
        "sender_id": sender,
        "conversation_id": "conv-demo",
        "type": "text",
        "text": "以后练前别推荐酸奶，我会胃不舒服。",
        "metadata": {},
    }
    response = handle_channel_message(memory_message)
    candidates = fitness_memory.list_memory_candidates(user_id=user_id)
    _show(3, "Memory candidate through channel", memory_message, response)
    _print_block("Candidate summary", [
        f"type: {candidates[-1].get('type')}",
        f"key: {candidates[-1].get('key')}",
        f"status: {candidates[-1].get('status')}",
    ])

    command_on = {
        "message_id": "msg-004",
        "channel": channel,
        "sender_id": sender,
        "conversation_id": "conv-demo",
        "type": "command",
        "text": "/recall on",
        "metadata": {},
    }
    response_on = handle_channel_message(command_on)
    _show(4, "Recall command on", command_on, response_on)

    command_status = {**command_on, "message_id": "msg-005", "text": "/recall status"}
    response_status = handle_channel_message(command_status)
    _show(4, "Recall command status", command_status, response_status)

    fallback_message = {
        "message_id": "msg-006",
        "channel": channel,
        "sender_id": "meeting_user",
        "conversation_id": "conv-demo",
        "type": "text",
        "text": "帮我把明天的会议整理一下",
        "metadata": {},
    }
    response = handle_channel_message(fallback_message)
    _show(5, "Non-fitness fallback", fallback_message, response)

    _print_block(
        "Product highlight",
        "Channel Adapter 将 IM/OpenClaw-like message 规范化后再路由到 Fitness Agent；非健康管理请求 handoff 给主 Agent。",
    )


if __name__ == "__main__":
    main()
