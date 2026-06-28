# Proactive Recall Outbox

## Status

Fitness Agent v0.5 Step 1 supports proactive recall outbox simulation.

Current supported path:

```text
recall opportunity -> outbox pending item
```

Implemented in later v0.5 steps:

```text
outbox pending item -> safety-gated openclaw_message delivery
local scheduler / launchd / cron trigger -> scheduled-run
```

Fitness still does not call a WeChat SDK directly. launchd/cron support is generated only; no system job is installed automatically.

## Safety Model

- Recall must be opt-in.
- Recall disabled or opt-out users do not get new outbox items.
- Quiet hours default to 23:00-08:00.
- Minimum interval defaults to 12 hours for active pending/sent outbox items.
- Duplicate guard allows only one pending/sent item per `user_id + recall_type + date`.
- Recall copy must stay low-pressure and non-shaming.
- The outbox is a buffer before any future proactive push.

Quiet-hours behavior in this version: the worker writes a `skipped` item with `skip_reason="quiet_hours"` and `scheduled_for` set to the next 08:00. It does not create a pending item during quiet hours.

## Outbox Schema

```python
{
  "version": 1,
  "items": [
    {
      "message_id": "recall-...",
      "user_id": "wechat_demo_user",
      "recall_type": "training_day_no_meal_log",
      "text": "...",
      "status": "pending",
      "delivery_channel": "wechat",
      "delivery_mode": "dry_run",
      "created_at": "2026-06-24T18:00:00",
      "scheduled_for": None,
      "sent_at": None,
      "skip_reason": None,
      "metadata": {
        "date": "2026-06-24",
        "cooldown_applied": True,
        "source": "recall_worker"
      }
    }
  ]
}
```

Supported item statuses:

- `pending`
- `sent`
- `skipped`
- `failed`

## Delivery Modes

`dry_run`:

- Does not send.
- Keeps item pending.
- Returns `reason="dry_run_no_send"`.

`console`:

- Prints the message locally.
- Does not send to an external system.
- Keeps item pending. It does not mark sent unless a future caller explicitly uses `mark_sent(...)`.

`openclaw_message`:

- Uses `openclaw message send` through the `openclaw-weixin` channel plugin.
- Defaults to dry-run.
- Real sending requires `--send --confirm-send`, delivery config `enabled=true`, and `allow_real_send=true`.
- Dry-run does not mark an item as sent.
- `@im.wechat` targets are case-sensitive and must be preserved exactly.

`future_openclaw`:

- Placeholder only.
- Returns `reason="openclaw_send_api_not_configured"`.
- Worker marks the item failed.

## CLI

```bash
python3 agents/fitness/tools/fitness_recall_worker.py run-once \
  --user wechat_demo_user \
  --date 2026-06-24 \
  --channel wechat \
  --dry-run

python3 agents/fitness/tools/fitness_recall_worker.py list-outbox \
  --user wechat_demo_user

python3 agents/fitness/tools/fitness_recall_worker.py clear-outbox \
  --user wechat_demo_user
```

## Demo

```bash
python3 agents/fitness/run_proactive_recall_demo.py
python3 agents/fitness/run_scheduled_recall_demo.py
```

The demo writes only under:

```text
agents/fitness/demo_data/proactive_recall/
```

## Future OpenClaw Send Adapter

OpenClaw message delivery is documented in `OPENCLAW_MESSAGE_DELIVERY.md`. If OpenClaw later exposes a lower-level send API, add a separate delivery adapter:

```python
send_via_openclaw(channel, conversation_id, text)
```

That future adapter must preserve opt-in, quiet hours, duplicate guard, and status updates. Do not treat current `future_openclaw` mode as a real sender.

## Scheduled Worker

Scheduled proactive recall is documented in `SCHEDULED_PROACTIVE_RECALL.md`.

The scheduler layer only decides when to call the worker. The outbox remains the safety buffer, and real sending still requires scheduler config, delivery config, exact-case target, account id, and explicit `--send --confirm-send`.
