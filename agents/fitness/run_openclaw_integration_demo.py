"""Showcase demo for Fitness Agent OpenClaw integration scaffold."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path
from typing import Any


AGENT_ROOT = Path(__file__).resolve().parent
TOOLS_DIR = AGENT_ROOT / "tools"
INTEGRATIONS_DIR = AGENT_ROOT / "integrations"
OPENCLAW_DATA_DIR = AGENT_ROOT / "demo_data" / "openclaw"
OPENCLAW_DATA_LABEL = "agents/fitness/demo_data/openclaw"
DEMO_ASSETS_DIR = AGENT_ROOT / "demo_assets" / "vision"

for path in (AGENT_ROOT, TOOLS_DIR, INTEGRATIONS_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from openclaw_adapter import handle_openclaw_event, normalize_openclaw_event  # noqa: E402
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
    if OPENCLAW_DATA_DIR.exists():
        shutil.rmtree(OPENCLAW_DATA_DIR)
    OPENCLAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    fitness_state.DATA_DIR = OPENCLAW_DATA_DIR


def _event(event_id: str, message_type: str, text: str = "", sender: str = "demo_user", **extra: Any) -> dict[str, Any]:
    message = {"type": message_type, "text": text}
    if "image_path" in extra:
        message["image_path"] = extra["image_path"]
    return {
        "event_id": event_id,
        "source": "openclaw",
        "channel": "wechat",
        "sender_id": sender,
        "conversation_id": "conv_demo",
        "message": message,
        "timestamp": "2026-06-24T20:00:00",
        "metadata": {},
        **({"date": extra["date"]} if "date" in extra else {}),
    }


def _show(number: int, title: str, event: dict[str, Any], response: dict[str, Any]) -> None:
    normalized = normalize_openclaw_event(event)
    print(f"=== OpenClaw Demo {number}: {title} ===\n")
    _print_block("Event normalized", [
        f"message_id: {normalized.get('message_id')}",
        f"channel: {normalized.get('channel')}",
        f"sender_id: {normalized.get('sender_id')}",
        f"type: {normalized.get('type')}",
        f"text: {normalized.get('text')}",
    ])
    _print_block("Fitness result", [
        f"ok: {str(response.get('ok')).lower()}",
        f"handled: {str(response.get('handled')).lower()}",
        f"handoff: {str(response.get('handoff')).lower()}",
        f"agent: {response.get('agent')}",
        f"state_changed: {str(response.get('state_changed')).lower()}",
    ])
    reply = response.get("reply")
    _print_block("Reply", reply.get("text") if reply else "handoff to main_agent")
    if response.get("state_summary"):
        _print_block("State summary", [f"{key}: {value}" for key, value in response["state_summary"].items()])
    if response.get("handoff_payload"):
        _print_block("Handoff payload", [
            f"target: {response['handoff_payload'].get('target')}",
            f"reason: {response['handoff_payload'].get('reason')}",
        ])


def main() -> None:
    _reset_demo_state()
    print("Fitness Agent v0.4 OpenClaw Integration Scaffold Demo")
    print(f"Demo state directory: {OPENCLAW_DATA_LABEL}")
    print("Real state under agents/fitness/data is not read or modified.")
    print("This is local scaffold only; it does not call OpenClaw runtime, WeChat SDKs, or send messages.\n")
    print("This is an OpenClaw-ready scaffold. No real runtime dispatcher was found in this workspace, so this demo uses local OpenClaw-like events.\n")

    text_event = _event("evt-001", "text", "今天晚上练臀，怎么吃？", date="2026-06-24")
    _show(1, "OpenClaw text event -> Fitness response", text_event, handle_openclaw_event(text_event))

    image_event = _event(
        "evt-002",
        "image",
        "午餐",
        image_path=str(DEMO_ASSETS_DIR / "beef_noodle_demo.jpg"),
        date="2026-06-24",
    )
    _show(2, "OpenClaw image event -> Food photo log", image_event, handle_openclaw_event(image_event, provider="demo"))

    recall_on = _event("evt-003", "command", "/recall on")
    _show(3, "OpenClaw command event -> Recall on", recall_on, handle_openclaw_event(recall_on))
    recall_status = _event("evt-004", "command", "/recall status")
    _show(3, "OpenClaw command event -> Recall status", recall_status, handle_openclaw_event(recall_status))

    memory_event = _event("evt-005", "text", "以后练前别推荐酸奶，我会胃不舒服。")
    memory_response = handle_openclaw_event(memory_event)
    _show(4, "OpenClaw memory preference event", memory_event, memory_response)
    candidates = fitness_memory.list_memory_candidates(user_id="wechat_demo_user")
    if candidates:
        _print_block("Candidate summary", [
            f"type: {candidates[-1].get('type')}",
            f"key: {candidates[-1].get('key')}",
            f"status: {candidates[-1].get('status')}",
        ])

    fallback_event = _event("evt-006", "text", "帮我把明天的会议整理一下", sender="meeting_user")
    _show(5, "Non-fitness event -> main agent handoff", fallback_event, handle_openclaw_event(fallback_event))

    _print_block(
        "Product highlight",
        "OpenClaw-ready scaffold 将本地 OpenClaw-like event 标准化后复用 Channel Adapter；非健康请求生成 handoff payload。",
    )


if __name__ == "__main__":
    main()
