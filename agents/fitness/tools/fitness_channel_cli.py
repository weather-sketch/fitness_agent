"""CLI for simulating Fitness channel messages locally."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


TOOLS_DIR = Path(__file__).resolve().parent
AGENT_ROOT = TOOLS_DIR.parent
for path in (AGENT_ROOT, TOOLS_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from channel_adapter import handle_channel_message  # noqa: E402


def _print_response(response: dict[str, Any], debug: bool = False) -> None:
    print(f"Handled: {response['handled']}")
    print(f"Handoff: {response['handoff']}")
    print(f"Intent: {response['intent']}")
    print(f"User ID: {response['user_id']}")
    print("Reply:")
    print(response.get("reply") or "(handoff to main agent)")
    if response.get("state_summary"):
        print("State summary:")
        for key, value in response["state_summary"].items():
            print(f"- {key}: {value}")
    if debug:
        print("Debug:")
        print(json.dumps(response, ensure_ascii=False, indent=2))


def _base_message(args: argparse.Namespace, message_type: str) -> dict[str, Any]:
    return {
        "message_id": args.message_id,
        "channel": args.channel,
        "sender_id": args.sender,
        "conversation_id": args.conversation_id,
        "type": message_type,
        "text": getattr(args, "text", None),
        "timestamp": args.timestamp,
        "metadata": {},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Simulate Fitness Agent channel routing")
    subparsers = parser.add_subparsers(dest="command", required=True)

    def add_common(subparser: argparse.ArgumentParser) -> None:
        subparser.add_argument("--channel", default="wechat")
        subparser.add_argument("--sender", default="demo_user")
        subparser.add_argument("--user", default=None, help="Explicit Fitness user_id override")
        subparser.add_argument("--date", default=None, help="YYYY-MM-DD date for image logging and state summaries")
        subparser.add_argument("--message-id", default="msg-local-001")
        subparser.add_argument("--conversation-id", default="conv-local-001")
        subparser.add_argument("--timestamp", default=None)
        subparser.add_argument("--debug", action="store_true")

    text = subparsers.add_parser("text", help="Route a text channel message")
    text.add_argument("--text", required=True)
    add_common(text)

    image = subparsers.add_parser("image", help="Route an image channel message")
    image.add_argument("--image", required=True)
    image.add_argument("--text", default=None, help="Optional note, such as 午餐")
    image.add_argument("--provider", default="demo")
    add_common(image)

    command = subparsers.add_parser("command", help="Route a command channel message")
    command.add_argument("--text", required=True)
    add_common(command)

    args = parser.parse_args()
    if args.command == "text":
        message = _base_message(args, "text")
        response = handle_channel_message(message, user_id=args.user, channel=args.channel, date=args.date)
    elif args.command == "image":
        message = _base_message(args, "image")
        message["image_path"] = args.image
        response = handle_channel_message(
            message,
            user_id=args.user,
            channel=args.channel,
            date=args.date,
            provider=args.provider,
        )
    else:
        message = _base_message(args, "command")
        response = handle_channel_message(message, user_id=args.user, channel=args.channel, date=args.date)

    _print_response(response, debug=args.debug)


if __name__ == "__main__":
    main()
