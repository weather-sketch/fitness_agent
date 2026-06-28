"""CLI for Fitness delivery configuration and OpenClaw message dry-runs."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import fitness_delivery  # noqa: E402
import fitness_delivery_config  # noqa: E402


def _print_config(user_id: str) -> None:
    config = fitness_delivery_config.load_delivery_config(user_id)
    print("Fitness Delivery Config")
    print()
    print(f"User: {user_id}")
    channels = config.get("channels", {})
    if not channels:
        print("Channels: none")
        return
    for channel, channel_config in channels.items():
        print(f"Channel: {channel}")
        print(f"- delivery_mode: {channel_config.get('delivery_mode')}")
        print(f"- openclaw_channel: {channel_config.get('openclaw_channel')}")
        print(f"- target: {fitness_delivery.mask_target(channel_config.get('target'))}")
        print(f"- account_id: {fitness_delivery.mask_account(channel_config.get('account_id'))}")
        print(f"- enabled: {str(bool(channel_config.get('enabled'))).lower()}")
        print(f"- allow_real_send: {str(bool(channel_config.get('allow_real_send'))).lower()}")


def _print_delivery_result(result: dict) -> None:
    print("Fitness Delivery Test")
    print()
    print(f"mode: {result.get('mode')}")
    print(f"dry_run: {str(bool(result.get('dry_run'))).lower()}")
    print(f"delivered: {str(bool(result.get('delivered'))).lower()}")
    print(f"status: {result.get('status')}")
    print(f"reason: {result.get('reason')}")
    print(f"exit_code: {result.get('exit_code')}")
    if result.get("command_preview"):
        print(f"command_preview: {result.get('command_preview')}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Fitness delivery config CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    configure = subparsers.add_parser("configure-wechat")
    configure.add_argument("--user", required=True)
    configure.add_argument("--target", required=True)
    configure.add_argument("--account-id", required=True)
    configure.add_argument("--enable", action="store_true")
    configure.add_argument("--allow-real-send", action="store_true")

    show = subparsers.add_parser("show")
    show.add_argument("--user", required=True)

    disable = subparsers.add_parser("disable")
    disable.add_argument("--user", required=True)
    disable.add_argument("--channel", default="wechat")

    test = subparsers.add_parser("test-wechat")
    test.add_argument("--user", required=True)
    test.add_argument("--message", required=True)
    test.add_argument("--dry-run", action="store_true")
    test.add_argument("--send", action="store_true")
    test.add_argument("--confirm-send", action="store_true")

    args = parser.parse_args()
    if args.command == "configure-wechat":
        fitness_delivery_config.configure_wechat_delivery(
            user_id=args.user,
            target=args.target,
            account_id=args.account_id,
            enabled=args.enable,
            allow_real_send=args.allow_real_send,
        )
        _print_config(args.user)
        return 0
    if args.command == "show":
        _print_config(args.user)
        return 0
    if args.command == "disable":
        fitness_delivery_config.disable_channel(args.user, args.channel)
        _print_config(args.user)
        return 0
    if args.command == "test-wechat":
        if args.send and not args.confirm_send:
            print("Refusing real send: --send requires --confirm-send")
            return 2
        dry_run = not (args.send and args.confirm_send)
        item = {
            "user_id": args.user,
            "delivery_channel": "wechat",
            "delivery_mode": "openclaw_message",
            "text": args.message,
            "status": "pending",
        }
        result = fitness_delivery.deliver_outbox_item(
            item,
            mode="openclaw_message",
            dry_run=dry_run,
            send_enabled=args.send,
            confirm_send=args.confirm_send,
        )
        _print_delivery_result(result)
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
