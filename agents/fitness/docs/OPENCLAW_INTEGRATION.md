# OpenClaw Integration Scaffold

## Purpose

Fitness Agent v0.4 Step 5 adds an OpenClaw-ready integration scaffold. It does not bind to a real OpenClaw runtime, does not call WeChat SDKs, and does not send messages.

Step 6 discovery found no real OpenClaw runtime dispatcher, WeChat SDK callback, or plugin manifest in this workspace. This remains OpenClaw-ready binding guidance, not a real runtime binding. See `OPENCLAW_RUNTIME_DISCOVERY.md`.

Current best path to real WeChat testing is skill-guided routing, not direct runtime binding, because no dispatcher/callback API is exposed in this workspace. See `WECHAT_MANUAL_TEST_GUIDE.md`.

v0.5 proactive recall writes outbox items first. Step 2 adds a manual OpenClaw message delivery adapter using `openclaw message send` and the `openclaw-weixin` channel plugin. It defaults to dry-run and requires explicit `--send --confirm-send` plus enabled delivery config for real sending. See `PROACTIVE_RECALL_OUTBOX.md` and `OPENCLAW_MESSAGE_DELIVERY.md`.

The scaffold defines a stable boundary:

```text
OpenClaw-like runtime event
  -> normalize to channel message
  -> call Fitness channel adapter
  -> format OpenClaw-compatible response payload
```

## Event Schema

```python
{
  "event_id": "evt-001",
  "source": "openclaw",
  "channel": "wechat",
  "sender_id": "demo_user",
  "conversation_id": "conv-001",
  "message": {
    "type": "text",
    "text": "今天晚上练臀，怎么吃？",
    "image_path": "agents/fitness/demo_assets/vision/beef_noodle_demo.jpg"
  },
  "timestamp": "2026-06-24T20:00:00",
  "metadata": {}
}
```

Supported message types:

- `text`
- `image`
- `command`

## Response Schema

Handled Fitness response:

```python
{
  "ok": True,
  "handled": True,
  "handoff": False,
  "agent": "fitness",
  "channel": "wechat",
  "conversation_id": "conv-001",
  "reply": {
    "type": "text",
    "text": "..."
  },
  "state_changed": True,
  "state_summary": {},
  "handoff_payload": None,
  "debug": {}
}
```

Non-fitness handoff:

```python
{
  "ok": True,
  "handled": False,
  "handoff": True,
  "agent": "fitness",
  "reply": None,
  "handoff_payload": {
    "target": "main_agent",
    "reason": "non_fitness_intent",
    "original_text": "帮我把明天的会议整理一下"
  }
}
```

## Three-layer Design

`normalize_openclaw_event(event)`:

- extracts channel, sender, conversation, message type, text, image path, timestamp, and metadata;
- fills safe defaults for missing optional fields;
- never maps missing sender to `default`.

`format_openclaw_response(channel_response, original_event)`:

- converts channel adapter output to an OpenClaw-compatible payload;
- puts user-visible text under `reply.text`;
- creates `handoff_payload` for non-fitness messages.

`handle_openclaw_event(event, provider="demo", dry_run=False)`:

- normalizes the event;
- rejects unsupported message types with `ok=false`;
- calls `channel_adapter.handle_channel_message(...)`;
- returns formatted payload.

## CLI

```bash
python3 agents/fitness/tools/fitness_openclaw_cli.py text \
  --text "今天晚上练臀，怎么吃？" \
  --channel wechat \
  --sender demo_user \
  --conversation conv_demo \
  --date 2026-06-24

python3 agents/fitness/tools/fitness_openclaw_cli.py image \
  --image agents/fitness/demo_assets/vision/beef_noodle_demo.jpg \
  --text "午餐" \
  --channel wechat \
  --sender demo_user \
  --conversation conv_demo \
  --date 2026-06-24 \
  --provider demo

python3 agents/fitness/tools/fitness_openclaw_cli.py command \
  --text "/fitness help" \
  --channel wechat \
  --sender demo_user \
  --conversation conv_demo
```

## Demo

```bash
python3 agents/fitness/run_openclaw_integration_demo.py
python3 agents/fitness/run_showcase_demo.py --flow openclaw
```

Demo state writes only under:

```text
agents/fitness/demo_data/openclaw/
agents/fitness/demo_data/showcase/
```

## Future Real Runtime Binding

When a real OpenClaw runtime event is available, the integration layer should only need a thin wrapper that adapts runtime fields into `handle_openclaw_event(...)`.

```python
from agents.fitness.integrations.openclaw_adapter import handle_openclaw_event


def runtime_entrypoint(runtime_event):
    event = convert_runtime_event_to_fitness_event(runtime_event)
    response = handle_openclaw_event(event, provider="demo")
    return convert_fitness_response_to_runtime_reply(response)
```

The caller remains responsible for sending `response["reply"]["text"]` through the real channel, or handing `handoff_payload` back to the main agent.

Do not describe this as real OpenClaw or WeChat integration. Current status is a local integration scaffold and simulator.

Future real proactive delivery should be added as a separate adapter only after OpenClaw exposes a send API, for example `send_via_openclaw(channel, conversation_id, text)`.
