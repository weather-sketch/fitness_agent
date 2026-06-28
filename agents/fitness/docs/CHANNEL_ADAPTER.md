# Channel Adapter

## Purpose

Fitness Agent v0.4 Step 4 adds an OpenClaw-ready channel adapter. It does not connect to WeChat, does not call OpenClaw runtime, and does not send messages. It defines a stable local contract:

Step 6 discovery found no real runtime dispatcher or WeChat callback in this workspace, so this adapter is still a local contract for skill-guided binding.

Current best path to real WeChat testing is skill-guided routing, not direct runtime binding, because no dispatcher/callback API is exposed in this workspace. The main Agent should use `skills/fitness-coach/SKILL.md` to decide when to build a WeChat-like message and call `handle_channel_message(...)`.

```text
IM / WeChat / OpenClaw-like message
  -> normalize message schema
  -> resolve channel user
  -> route text / image / command
  -> return channel-safe response object
  -> handoff non-fitness requests
```

## Message Schema

```python
{
  "message_id": "msg-001",
  "channel": "wechat",
  "sender_id": "wechat-user-001",
  "conversation_id": "conv-001",
  "type": "text",
  "text": "今天晚上练臀，怎么吃？",
  "image_path": "agents/fitness/demo_assets/vision/beef_noodle_demo.jpg",
  "timestamp": "2026-06-24T20:00:00",
  "metadata": {}
}
```

Supported message types:

- `text`
- `image`
- `command`

## Response Schema

```python
{
  "handled": True,
  "handoff": False,
  "channel": "wechat",
  "user_id": "wechat_demo_user",
  "message_type": "text",
  "intent": "daily_plan",
  "reply": "...",
  "state_changed": True,
  "state_summary": {},
  "tool_chain": [],
  "debug": {}
}
```

`reply` is channel-safe user-facing text. Full internals stay under `debug`.

## User Mapping

Explicit `user_id` wins. Otherwise:

```text
channel + sender_id -> fitness user_id
```

Examples:

```text
wechat + demo_user -> wechat_demo_user
local + demo_user -> local_demo_user
```

Unsafe characters are normalized to `_`. The adapter does not put every channel user into `default`.

## Routing

Text messages call the existing `handle_fitness_message(...)`.

Image messages call the food photo provider adapter and write to the current user's `nutrition.meals` only when the image is readable.

Command messages support:

```text
/fitness help
/recall status
/recall on
/recall off
/memory candidates
```

Unknown commands return the help message.

Non-fitness text returns:

```python
{
  "handled": False,
  "handoff": True,
  "intent": "unknown"
}
```

and should be handed back to the main agent. It should not create Fitness state or memory candidates.

## CLI

```bash
python3 agents/fitness/tools/fitness_channel_cli.py text \
  --text "今天晚上练臀，怎么吃？" \
  --channel wechat \
  --sender demo_user \
  --date 2026-06-24

python3 agents/fitness/tools/fitness_channel_cli.py image \
  --image agents/fitness/demo_assets/vision/beef_noodle_demo.jpg \
  --text "午餐" \
  --channel wechat \
  --sender demo_user \
  --date 2026-06-24 \
  --provider demo

python3 agents/fitness/tools/fitness_channel_cli.py command \
  --text "/fitness help" \
  --channel wechat \
  --sender demo_user
```

## Demo

```bash
python3 agents/fitness/run_channel_demo.py
python3 agents/fitness/run_showcase_demo.py --flow channel
```

Demo state writes only under:

```text
agents/fitness/demo_data/channel/
agents/fitness/demo_data/showcase/
```

## Future Real Binding

To connect a real channel later, convert OpenClaw or WeChat events into the message schema above and pass them to `handle_channel_message(...)`. The caller remains responsible for sending the returned `reply` through the real channel or handing off non-fitness requests.

For OpenClaw-like runtime events, use the Step 5 scaffold:

```bash
python3 agents/fitness/run_openclaw_integration_demo.py
```

See `docs/OPENCLAW_INTEGRATION.md`.

Do not describe this as completed real WeChat integration. Current status is an OpenClaw-ready adapter contract and local simulator.
