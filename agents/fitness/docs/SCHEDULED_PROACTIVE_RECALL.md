# Scheduled Proactive Recall

## Status

Fitness Agent v0.5 Step 3 adds a local scheduled proactive recall worker.

Supported path:

```text
local scheduler / launchd / cron
  -> fitness_recall_worker.py scheduled-run
  -> recall opportunity
  -> recall_outbox pending item
  -> optional openclaw_message delivery
  -> openclaw-weixin
```

This is not a direct WeChat SDK integration. It uses `openclaw message send` only through the delivery adapter, and it does not automatically install launchd or cron jobs.

## Scheduler Config

User-level scheduler config lives at:

```text
agents/fitness/data/users/<user_id>/scheduler_config.json
```

Schema:

```python
{
  "version": 1,
  "enabled": False,
  "user_id": "<user_id>",
  "channel": "wechat",
  "delivery_mode": "openclaw_message",
  "send_enabled": False,
  "confirm_send": False,
  "schedule": {
    "type": "local_interval",
    "preferred_hours": [9, 18, 21],
    "timezone": "Asia/Shanghai",
    "max_runs_per_day": 3
  },
  "safety": {
    "respect_quiet_hours": True,
    "respect_cooldown": True,
    "respect_duplicate_guard": True,
    "require_recall_opt_in": True
  },
  "created_at": "...",
  "updated_at": "..."
}
```

The scheduler config stores only timing and safety gates. It does not copy WeChat `target` or `account_id`; those stay in `delivery_config.json`.

## Safety Gates

Default behavior is dry-run or pending outbox creation. Real automatic sending requires all of these:

- recall opt-in;
- scheduler `enabled=true`;
- scheduler `send_enabled=true`;
- scheduler `confirm_send=true`;
- delivery config `enabled=true`;
- delivery config `allow_real_send=true`;
- exact-case `@im.wechat` target;
- account id;
- CLI invocation with `--send --confirm-send`.

The scheduler config `confirm_send=true` is not a permanent bypass. The command still must pass `--send --confirm-send` for each real-send run.

Quiet hours, duplicate guard, and cooldown are still enforced by the worker.

## CLI

Configure scheduler:

```bash
python3 agents/fitness/tools/fitness_scheduler_cli.py configure \
  --user wechat_self_test \
  --enable \
  --channel wechat \
  --delivery-mode openclaw_message \
  --hours 9,18,21 \
  --timezone Asia/Shanghai \
  --max-runs-per-day 3
```

Run once through scheduler gates:

```bash
python3 agents/fitness/tools/fitness_recall_worker.py scheduled-run \
  --user wechat_self_test \
  --date 2026-06-24 \
  --dry-run
```

Run all enabled users:

```bash
python3 agents/fitness/tools/fitness_recall_worker.py scheduled-run-all \
  --date 2026-06-24 \
  --dry-run
```

## launchd And cron

Generate launchd plist:

```bash
python3 agents/fitness/tools/fitness_scheduler_install.py print-launchd \
  --user wechat_self_test \
  --time "21:00" \
  --dry-run
```

Generate cron line:

```bash
python3 agents/fitness/tools/fitness_scheduler_install.py print-cron \
  --user wechat_self_test \
  --time "21:00"
```

These commands do not install system tasks. `write-launchd` is dry-run by default and requires `--write --confirm-write` to write a plist file. No command writes to crontab.

By default generated scheduler commands do not include `--send --confirm-send`. Real automatic sends require explicit `--real-send` in generated snippets and all safety configs above.

## Exact-case WeChat Target

`@im.wechat` targets are case-sensitive. Use the exact target from inbound OpenClaw metadata or the Weixin context-token file. Do not lowercase it.

A lowercase target can produce an OpenClaw core `messageId` but no visible WeChat delivery.

## Demo

```bash
python3 agents/fitness/run_scheduled_recall_demo.py
```

The demo writes only under:

```text
agents/fitness/demo_data/scheduled_recall/
```

It mocks OpenClaw delivery and does not send real messages.
