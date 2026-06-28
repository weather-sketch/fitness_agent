# OpenClaw Message Delivery

## Status

Fitness Agent v0.5 Step 2 adds a configurable OpenClaw message delivery adapter for recall outbox items.

Current delivery path:

```text
recall_outbox pending item
  -> openclaw message send
  -> openclaw-weixin channel plugin
  -> Weixin backend sendMessage
```

This is not a direct WeChat SDK integration. Fitness calls the OpenClaw CLI wrapper only when explicitly requested.

## Safety Defaults

- Default behavior is dry-run.
- Real sending requires `--send --confirm-send`.
- Real sending also requires delivery config `enabled=true` and `allow_real_send=true`.
- Missing config, disabled config, missing target, missing account id, and `allow_real_send=false` all prevent sending.
- Dry-run does not mark outbox items as sent.
- Outbox items are not automatically sent after creation.
- Recall opt-in, quiet hours, duplicate guard, and cooldown still apply before delivery.
- `@im.wechat` target IDs are case-sensitive. Preserve exact casing from inbound OpenClaw metadata or the Weixin context-token file.

## Delivery Config

User-level config lives at:

```text
agents/fitness/data/users/<user_id>/delivery_config.json
```

Schema:

```python
{
  "version": 1,
  "channels": {
    "wechat": {
      "delivery_mode": "openclaw_message",
      "openclaw_channel": "openclaw-weixin",
      "target": "<user@im.wechat>",
      "account_id": "<accountId>",
      "enabled": False,
      "allow_real_send": False,
      "created_at": "...",
      "updated_at": "..."
    }
  }
}
```

The config file is written only when explicitly configured. Do not guess `target` or `account_id`.

Do not lowercase `target`. A lowercase `@im.wechat` target can produce an OpenClaw core `messageId` while no WeChat client message appears.

## Configure And Test

Dry-run test with missing config:

```bash
python3 agents/fitness/tools/fitness_delivery_cli.py test-wechat \
  --user wechat_demo_user \
  --message "dry run test" \
  --dry-run
```

Configure WeChat delivery:

```bash
python3 agents/fitness/tools/fitness_delivery_cli.py configure-wechat \
  --user wechat_demo_user \
  --target "<user@im.wechat>" \
  --account-id "<accountId>" \
  --enable
```

Dry-run through OpenClaw:

```bash
python3 agents/fitness/tools/fitness_delivery_cli.py test-wechat \
  --user wechat_demo_user \
  --message "dry run test" \
  --dry-run
```

Dangerous real-send shape, only after manual confirmation:

```bash
python3 agents/fitness/tools/fitness_delivery_cli.py test-wechat \
  --user wechat_demo_user \
  --message "真实发送测试" \
  --send \
  --confirm-send
```

Real sending also requires `allow_real_send=true` in delivery config.

## Recall Worker Integration

Safe dry-run:

```bash
python3 agents/fitness/tools/fitness_recall_worker.py run-once \
  --user wechat_demo_user \
  --date 2026-06-24 \
  --channel wechat \
  --delivery-mode openclaw_message \
  --dry-run
```

Explicit send-pending dry-run:

```bash
python3 agents/fitness/tools/fitness_recall_worker.py send-pending \
  --user wechat_demo_user \
  --message-id recall-... \
  --delivery-mode openclaw_message \
  --dry-run
```

## Implementation Notes

`fitness_delivery.py` builds commands as an argument list and uses `subprocess.run(..., shell=False)`. The message is passed as a separate argument. Command previews mask the target, account id, and message body.

Dry-run command shape:

```bash
openclaw message send \
  --channel openclaw-weixin \
  --account <accountId> \
  --target <user@im.wechat> \
  --message "<text>" \
  --dry-run \
  --json
```

Do not describe this as automatic scheduled WeChat push. It is manual worker/send-pending delivery with explicit safety gates.

## Scheduled Worker Integration

v0.5 Step 3 adds a local scheduled worker that can call the same delivery adapter:

```bash
python3 agents/fitness/tools/fitness_recall_worker.py scheduled-run \
  --user wechat_self_test \
  --date 2026-06-24 \
  --dry-run
```

launchd/cron generation is documented in `SCHEDULED_PROACTIVE_RECALL.md`. It does not install jobs automatically. Real scheduled sending remains gated by recall opt-in, scheduler config, delivery config, exact-case target, account id, and `--send --confirm-send`.
