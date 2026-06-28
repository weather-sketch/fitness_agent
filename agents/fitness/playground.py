"""Lightweight local playground for Fitness Agent demos."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any


AGENT_ROOT = Path(__file__).resolve().parent
TOOLS_DIR = AGENT_ROOT / "tools"
PLAYGROUND_DATA_DIR = AGENT_ROOT / "demo_data" / "playground"
PLAYGROUND_DATA_LABEL = "agents/fitness/demo_data/playground"

for path in (AGENT_ROOT, TOOLS_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from handler import handle_fitness_message  # noqa: E402
from run_showcase_demo import (  # noqa: E402
    print_flow_result,
    reset_demo_user_state,
    run_active_memory_flow,
    run_food_photo_flow,
    run_lapse_recovery_flow,
    run_non_fitness_fallback_flow,
    run_openclaw_integration_flow,
    run_recall_flow,
    run_channel_adapter_flow,
    run_training_food_plan_flow,
    set_demo_data_dir,
)


MENU = """Fitness Agent Playground

请选择一个 demo:
1. 训练日怎么吃
2. 吃超后怎么接回节奏
3. 图片记录一餐
4. 记忆生效：不推荐酸奶
5. opt-in recall 建议
6. non-fitness fallback
7. 自由输入
8. 模拟微信/IM 消息入口
9. 模拟 OpenClaw runtime event
0. 退出
"""


def run_playground_action(
    choice: str,
    user_id: str = "playground_user",
    free_text: str | None = None,
    data_root: str | Path = PLAYGROUND_DATA_DIR,
) -> dict[str, Any]:
    """Run one playground action without reading stdin."""
    set_demo_data_dir(data_root)
    if choice == "1":
        return {"kind": "flow", "result": run_training_food_plan_flow(user_id=f"{user_id}_text")}
    if choice == "2":
        return {"kind": "flow", "result": run_lapse_recovery_flow(user_id=f"{user_id}_lapse")}
    if choice == "3":
        return {"kind": "flow", "result": run_food_photo_flow(user_id=f"{user_id}_vision")}
    if choice == "4":
        return {"kind": "flow", "result": run_active_memory_flow(user_id=f"{user_id}_memory")}
    if choice == "5":
        return {"kind": "flow", "result": run_recall_flow(user_id=f"{user_id}_recall")}
    if choice == "6":
        return {"kind": "flow", "result": run_non_fitness_fallback_flow(user_id=f"{user_id}_fallback")}
    if choice == "7":
        text = (free_text or "").strip()
        if not text:
            return {"kind": "message", "message": "自由输入不能为空。"}
        result = handle_fitness_message(text, user_id=f"{user_id}_free", channel="playground")
        return {
            "kind": "free_input",
            "result": {
                "handled": result["handled"],
                "intent": result["intent"],
                "reply": result["reply"] if result["handled"] else "交还主 Agent 正常处理。",
                "debug": result.get("debug", {}),
            },
        }
    if choice == "8":
        return {"kind": "flow", "result": run_channel_adapter_flow()}
    if choice == "9":
        return {"kind": "flow", "result": run_openclaw_integration_flow()}
    if choice == "0":
        return {"kind": "exit", "message": "已退出。"}
    return {"kind": "message", "message": "请输入 0-9 之间的选项。"}


def _print_action(action: dict[str, Any]) -> None:
    kind = action.get("kind")
    if kind == "flow":
        print_flow_result(action["result"])
        return
    if kind == "free_input":
        result = action["result"]
        print("Free input result:")
        print(f"- handled: {str(result['handled']).lower()}")
        print(f"- intent: {result['intent']}")
        print("Agent reply:")
        print(result["reply"])
        print()
        return
    print(action.get("message", ""))
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Fitness Agent local playground")
    parser.add_argument("--keep-state", action="store_true", help="Do not reset playground demo state on startup")
    args = parser.parse_args()

    print("Fitness Agent Playground")
    print(f"Demo state directory: {PLAYGROUND_DATA_LABEL}")
    print("Real state under agents/fitness/data is not read or modified.")
    if args.keep_state:
        set_demo_data_dir(PLAYGROUND_DATA_DIR)
        print("Playground state kept for this session.\n")
    else:
        answer = input("Reset playground state before starting? [Y/n] ").strip().lower()
        if answer in {"", "y", "yes"}:
            reset_demo_user_state(PLAYGROUND_DATA_DIR)
            print("Playground state reset.\n")
        else:
            set_demo_data_dir(PLAYGROUND_DATA_DIR)
            print("Playground state kept.\n")

    while True:
        print(MENU)
        choice = input("> ").strip()
        if choice == "7":
            free_text = input("请输入你的消息：").strip()
            action = run_playground_action(choice, free_text=free_text)
        else:
            action = run_playground_action(choice)
        _print_action(action)
        if action.get("kind") == "exit":
            break


if __name__ == "__main__":
    main()
