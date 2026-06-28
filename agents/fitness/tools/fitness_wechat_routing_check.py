"""Local WeChat skill-routing check for Fitness Agent.

This script does not connect to WeChat or OpenClaw runtime. It simulates the
message shape the main Agent should build after skill-guided routing.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from typing import Any


AGENT_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = AGENT_ROOT.parents[1]
INTEGRATIONS_DIR = AGENT_ROOT / "integrations"

for path in (AGENT_ROOT, AGENT_ROOT / "tools", INTEGRATIONS_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from channel_adapter import handle_channel_message  # noqa: E402
import fitness_state  # noqa: E402


SKILL_FILE = WORKSPACE_ROOT / "skills" / "fitness-coach" / "SKILL.md"
CHANNEL_ADAPTER = AGENT_ROOT / "channel_adapter.py"
OPENCLAW_SCAFFOLD = AGENT_ROOT / "integrations" / "openclaw_adapter.py"


CASES = [
    {
        "label": "Test 1: text fitness request",
        "input": "今天晚上练臀，怎么吃？",
        "expected_route": "fitness",
        "sender_id": "wechat_routing_check_user",
    },
    {
        "label": "Test 2: lapse recovery",
        "input": "我今天吃爆了，不想记了",
        "expected_route": "fitness",
        "sender_id": "wechat_routing_check_user",
    },
    {
        "label": "Test 3: memory preference",
        "input": "以后练前别推荐酸奶，我会胃不舒服",
        "expected_route": "fitness",
        "sender_id": "wechat_routing_check_user",
    },
    {
        "label": "Test 4: non-fitness fallback",
        "input": "帮我整理明天会议",
        "expected_route": "main_agent",
        "sender_id": "wechat_routing_check_meeting_user",
    },
]


def _ok(path: Path) -> str:
    return "OK" if path.exists() else "MISSING"


def _message(text: str, sender_id: str) -> dict[str, Any]:
    return {
        "type": "text",
        "text": text,
        "channel": "wechat",
        "sender_id": sender_id,
        "conversation_id": "wechat-routing-check",
        "metadata": {"source": "local_wechat_routing_check"},
    }


def run_cases(date: str = "2026-06-24") -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for case in CASES:
        response = handle_channel_message(_message(case["input"], case["sender_id"]), channel="wechat", date=date)
        results.append({**case, "response": response})
    return results


def main() -> int:
    old_data_dir = fitness_state.DATA_DIR
    try:
        with tempfile.TemporaryDirectory() as tmp:
            fitness_state.DATA_DIR = Path(tmp) / "fitness-wechat-routing-check"
            results = run_cases()
    finally:
        fitness_state.DATA_DIR = old_data_dir

    print("Fitness WeChat Routing Check")
    print()
    print(f"Skill file: {_ok(SKILL_FILE)}")
    print(f"Channel adapter: {_ok(CHANNEL_ADAPTER)}")
    print(f"OpenClaw scaffold: {_ok(OPENCLAW_SCAFFOLD)}")
    print()

    for result in results:
        response = result["response"]
        print(result["label"])
        print(f"- input: {result['input']}")
        print(f"- expected route: {result['expected_route']}")
        print(f"- handled: {str(bool(response.get('handled'))).lower()}")
        if result["expected_route"] == "main_agent":
            print(f"- handoff: {str(bool(response.get('handoff'))).lower()}")
        print()

    print("Recommended real WeChat test:")
    print("1. 在微信里给 OpenClaw 发：今天晚上练臀，怎么吃？")
    print("2. 如果没有触发 Fitness，请把主 Agent 回复贴回来，用于调整 skill trigger wording。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
