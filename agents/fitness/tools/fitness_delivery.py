"""Delivery adapter contract for Fitness recall outbox."""

from __future__ import annotations

import json
import subprocess
from typing import Any

import fitness_delivery_config


SUPPORTED_MODES = {"dry_run", "console", "future_openclaw", "openclaw_message"}
DEFAULT_OPENCLAW_CHANNEL = "openclaw-weixin"


def mask_target(value: str | None) -> str:
    if not value:
        return "(missing)"
    if value.endswith("@im.wechat"):
        return "***@im.wechat"
    if len(value) <= 6:
        return "***"
    return f"{value[:2]}***{value[-2:]}"


def mask_account(value: str | None) -> str:
    if not value:
        return "(missing)"
    if len(value) <= 6:
        return "***"
    return f"{value[:2]}***{value[-2:]}"


def build_openclaw_message_command(
    *,
    target: str,
    text: str,
    account_id: str | None = None,
    openclaw_channel: str = DEFAULT_OPENCLAW_CHANNEL,
    dry_run: bool = True,
    json_output: bool = True,
) -> list[str]:
    command = [
        "openclaw",
        "message",
        "send",
        "--channel",
        openclaw_channel,
        "--target",
        target,
        "--message",
        text,
    ]
    if account_id:
        command.extend(["--account", account_id])
    if dry_run:
        command.append("--dry-run")
    if json_output:
        command.append("--json")
    return command


def _command_preview(command: list[str]) -> str:
    preview: list[str] = []
    skip_next = False
    for index, part in enumerate(command):
        if skip_next:
            skip_next = False
            continue
        if part == "--target" and index + 1 < len(command):
            preview.extend([part, mask_target(command[index + 1])])
            skip_next = True
        elif part == "--account" and index + 1 < len(command):
            preview.extend([part, mask_account(command[index + 1])])
            skip_next = True
        elif part == "--message" and index + 1 < len(command):
            preview.extend([part, "..."])
            skip_next = True
        else:
            preview.append(part)
    return " ".join(preview)


def send_via_openclaw_message(
    *,
    target: str,
    text: str,
    account_id: str | None = None,
    openclaw_channel: str = DEFAULT_OPENCLAW_CHANNEL,
    dry_run: bool = True,
    send_enabled: bool = False,
    confirm_send: bool = False,
    timeout_seconds: int = 30,
) -> dict[str, Any]:
    if not target:
        return {
            "delivered": False,
            "mode": "openclaw_message",
            "dry_run": dry_run,
            "status": "failed",
            "reason": "target_missing",
            "command_preview": "",
        }
    if not dry_run and not (send_enabled and confirm_send):
        return {
            "delivered": False,
            "mode": "openclaw_message",
            "dry_run": dry_run,
            "status": "failed",
            "reason": "real_send_not_confirmed",
            "command_preview": "",
        }

    command = build_openclaw_message_command(
        target=target,
        text=text,
        account_id=account_id,
        openclaw_channel=openclaw_channel,
        dry_run=dry_run,
        json_output=True,
    )
    preview = _command_preview(command)
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "delivered": False,
            "mode": "openclaw_message",
            "dry_run": dry_run,
            "status": "failed",
            "reason": "openclaw_message_timeout",
            "exit_code": None,
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or "",
            "command_preview": preview,
        }

    delivered = completed.returncode == 0 and not dry_run
    reason = "dry_run_no_send" if completed.returncode == 0 and dry_run else (
        "openclaw_message_sent" if delivered else "openclaw_message_failed"
    )
    status = "pending" if completed.returncode == 0 and dry_run else ("sent" if delivered else "failed")
    return {
        "delivered": delivered,
        "mode": "openclaw_message",
        "dry_run": dry_run,
        "status": status,
        "reason": reason,
        "exit_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "command_preview": preview,
    }


def _openclaw_message_delivery(
    item: dict[str, Any],
    *,
    dry_run: bool,
    send_enabled: bool,
    confirm_send: bool,
) -> dict[str, Any]:
    user_id = str(item.get("user_id") or "")
    channel = str(item.get("delivery_channel") or "wechat")
    channel_config = fitness_delivery_config.get_channel_config(user_id, channel)
    if not channel_config:
        return {
            "delivered": False,
            "mode": "openclaw_message",
            "dry_run": dry_run,
            "status": "failed",
            "reason": "config_missing",
        }
    if not channel_config.get("enabled"):
        return {
            "delivered": False,
            "mode": "openclaw_message",
            "dry_run": dry_run,
            "status": "failed",
            "reason": "config_disabled",
        }
    if not channel_config.get("target"):
        return {
            "delivered": False,
            "mode": "openclaw_message",
            "dry_run": dry_run,
            "status": "failed",
            "reason": "target_missing",
        }
    if not channel_config.get("account_id"):
        return {
            "delivered": False,
            "mode": "openclaw_message",
            "dry_run": dry_run,
            "status": "failed",
            "reason": "account_id_missing",
        }
    if not dry_run and not channel_config.get("allow_real_send"):
        return {
            "delivered": False,
            "mode": "openclaw_message",
            "dry_run": dry_run,
            "status": "failed",
            "reason": "real_send_not_allowed",
        }
    return send_via_openclaw_message(
        target=str(channel_config.get("target")),
        account_id=str(channel_config.get("account_id")),
        openclaw_channel=str(channel_config.get("openclaw_channel") or DEFAULT_OPENCLAW_CHANNEL),
        text=str(item.get("text") or ""),
        dry_run=dry_run,
        send_enabled=send_enabled,
        confirm_send=confirm_send,
    )


def deliver_outbox_item(
    item: dict[str, Any],
    mode: str = "dry_run",
    *,
    dry_run: bool = True,
    send_enabled: bool = False,
    confirm_send: bool = False,
) -> dict[str, Any]:
    """Deliver or simulate delivery for one outbox item."""
    if mode not in SUPPORTED_MODES:
        return {
            "delivered": False,
            "mode": mode,
            "status": "failed",
            "reason": "unsupported_delivery_mode",
        }

    if mode == "dry_run":
        return {
            "delivered": False,
            "mode": "dry_run",
            "status": "pending",
            "reason": "dry_run_no_send",
        }

    if mode == "console":
        print("Fitness Recall Console Delivery")
        print(f"To: {item.get('delivery_channel')}:{item.get('user_id')}")
        print(f"Message: {item.get('text')}")
        return {
            "delivered": False,
            "mode": "console",
            "status": "pending",
            "reason": "console_preview_no_send",
        }

    if mode == "openclaw_message":
        return _openclaw_message_delivery(
            item,
            dry_run=dry_run,
            send_enabled=send_enabled,
            confirm_send=confirm_send,
        )

    return {
        "delivered": False,
        "mode": "future_openclaw",
        "status": "failed",
        "reason": "openclaw_send_api_not_configured",
    }
