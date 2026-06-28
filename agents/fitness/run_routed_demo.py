"""Run a local routed-message demo through Fitness Agent handler."""

from __future__ import annotations

import sys
from pathlib import Path


AGENT_ROOT = Path(__file__).resolve().parent
if str(AGENT_ROOT) not in sys.path:
    sys.path.insert(0, str(AGENT_ROOT))

from handler import handle_fitness_message  # noqa: E402
from run_demo import DEMO_DATA_LABEL, _prepare_demo_data  # noqa: E402


DEMO_MESSAGES = [
    "今天晚上练臀，怎么吃？",
    "中午吃了一碗牛肉面",
    "练完了，今天强度很大，练后吃什么？",
    "我今天吃爆了，不想记了",
    "这周怎么样？",
    "帮我把明天的会议整理一下",
]


def _print_result(user_input: str, result: dict) -> None:
    print(f"User input: {user_input}")
    print(f"Handled: {result['handled']}")
    print(f"Detected intent: {result['intent']}")
    print(f"Tool chain: {' -> '.join(result['tool_chain']) if result['tool_chain'] else '(none)'}")
    print("Reply:")
    print(result["reply"] or "(handoff to main agent)")
    print()


def main() -> None:
    _prepare_demo_data()
    print("Fitness Agent v0.1 Routed Demo")
    print(f"Demo state directory: {DEMO_DATA_LABEL}")
    print("Real state under agents/fitness/data is not read or modified.\n")

    for index, message in enumerate(DEMO_MESSAGES, 1):
        print(f"=== Routed Demo {index} ===")
        _print_result(message, handle_fitness_message(message, user_id="default", channel="routed_demo"))


if __name__ == "__main__":
    main()
