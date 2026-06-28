"""CLI for simulating OpenClaw runtime events for Fitness Agent."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


TOOLS_DIR = Path(__file__).resolve().parent
AGENT_ROOT = TOOLS_DIR.parent
INTEGRATIONS_DIR = AGENT_ROOT / "integrations"
for path in (AGENT_ROOT, TOOLS_DIR, INTEGRATIONS_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from openclaw_adapter import handle_openclaw_event  # noqa: E402


def _build_event(args: argparse.Namespace, message_type: str) -> dict[str, Any]:
    message: dict[str, Any] = {
        "type": message_type,
        "text": getattr(args, "text", None),
    }
    if message_type == "image":
        message["image_path"] = args.image
    event = {
        "event_id": args.event_id,
        "source": "openclaw",
        "channel": args.channel,
        "sender_id": args.sender,
        "conversation_id": args.conversation,
        "message": message,
        "timestamp": args.timestamp,
        "metadata": {},
    }
    if args.date:
        event["date"] = args.date
    return event


def _print_response(event: dict[str, Any], response: dict[str, Any], debug: bool = False) -> None:
    message = event.get("message", {})
    print("OpenClaw event:")
    print(f"- channel: {event.get('channel')}")
    print(f"- sender: {event.get('sender_id')}")
    print(f"- conversation: {event.get('conversation_id')}")
    print(f"- message_type: {message.get('type')}")
    print()
    print("Fitness result:")
    print(f"- ok: {str(response.get('ok')).lower()}")
    print(f"- handled: {str(response.get('handled')).lower()}")
    print(f"- handoff: {str(response.get('handoff')).lower()}")
    print(f"- agent: {response.get('agent')}")
    if response.get("state_summary"):
        print("State summary:")
        for key, value in response["state_summary"].items():
            print(f"- {key}: {value}")
    print()
    print("Reply:")
    reply = response.get("reply")
    if reply:
        print(reply.get("text") or "")
    elif response.get("handoff_payload"):
        print("Handoff to main_agent")
    else:
        print("(no reply)")
    if debug:
        print()
        print("Debug:")
        print(json.dumps(response, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Simulate Fitness OpenClaw runtime events")
    subparsers = parser.add_subparsers(dest="command", required=True)

    def add_common(subparser: argparse.ArgumentParser) -> None:
        subparser.add_argument("--channel", default="wechat")
        subparser.add_argument("--sender", default="demo_user")
        subparser.add_argument("--conversation", default="conv_demo")
        subparser.add_argument("--date", default=None)
        subparser.add_argument("--event-id", default="evt-local-001")
        subparser.add_argument("--timestamp", default=None)
        subparser.add_argument("--debug", action="store_true")

    text = subparsers.add_parser("text", help="Simulate a text runtime event")
    text.add_argument("--text", required=True)
    add_common(text)

    image = subparsers.add_parser("image", help="Simulate an image runtime event")
    image.add_argument("--image", required=True)
    image.add_argument("--text", default=None)
    image.add_argument("--provider", default="demo")
    add_common(image)

    command = subparsers.add_parser("command", help="Simulate a command runtime event")
    command.add_argument("--text", required=True)
    add_common(command)

    args = parser.parse_args()
    event = _build_event(args, args.command)
    response = handle_openclaw_event(event, provider=getattr(args, "provider", "demo"))
    _print_response(event, response, debug=args.debug)


if __name__ == "__main__":
    main()
