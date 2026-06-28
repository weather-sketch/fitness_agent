# OpenClaw Runtime Discovery

## Discovery Result

Step 6 checked the current workspace for a real OpenClaw runtime dispatcher, WeChat SDK callback, message callback, skill/plugin manifest, or runtime entrypoint.

No real OpenClaw runtime dispatcher / WeChat SDK callback / plugin manifest was found in the current workspace.

Discovery commands used:

```bash
find . -maxdepth 8 -type f | grep -Ei "manifest|config|skill|agent|router|gateway|runtime|message|event|wechat|weixin|entry|dispatch|handler|callback|plugin"
grep -R "handle_message\|on_message\|dispatch\|entrypoint\|wechat\|weixin\|gateway\|runtime\|skill\|callback\|plugin" -n . | head -500
grep -R "fitness-coach\|handle_fitness_message\|routing_adapter\|agents/fitness\|handle_openclaw_event\|channel_adapter" -n . | head -500
```

Findings:

- Real OpenClaw runtime entrypoint: not found.
- Real WeChat / IM message callback: not found.
- Skill manifest / plugin manifest: only workspace skill files were found, including `skills/fitness-coach/SKILL.md`; no runtime plugin manifest was found.
- Main Agent skill invocation convention: `AGENTS.md` routes Fitness-domain messages to Fitness Agent and says to return only the user-facing reply when handled.
- Exposed binding point: no real runtime binding point exposed in this workspace.

The relevant files found are Fitness-owned docs, adapters, tests, and workspace instructions:

```text
skills/fitness-coach/SKILL.md
AGENTS.md
agents/fitness/routing_adapter.py
agents/fitness/AGENT.md
agents/fitness/channel_adapter.py
agents/fitness/integrations/openclaw_adapter.py
.openclaw/workspace-state.json
```

## Step 7 WeChat Skill Routing

Current best path to real WeChat testing is skill-guided routing, not direct runtime binding, because no dispatcher/callback API is exposed in this workspace.

The expected manual path is:

```text
WeChat message
  -> OpenClaw main Agent
  -> skills/fitness-coach/SKILL.md
  -> agents.fitness.channel_adapter.handle_channel_message(...)
```

Use `WECHAT_MANUAL_TEST_GUIDE.md` for real WeChat hand testing and `agents/fitness/tools/fitness_wechat_routing_check.py` for local preflight.

## Current Integration Status

Implemented:

- channel message adapter
- OpenClaw-like event scaffold
- local OpenClaw CLI simulator
- handoff payload for non-fitness requests
- date propagation from CLI/event to Fitness state

Not implemented:

- real OpenClaw runtime binding
- real WeChat SDK callback
- real message sending
- proactive push

## Recommended Future Binding

When the real OpenClaw runtime exposes a dispatcher or callback, add only a thin wrapper. Do not move Fitness business logic into the runtime layer.

```python
from agents.fitness.integrations.openclaw_adapter import handle_openclaw_event


def runtime_entrypoint(runtime_event):
    event = convert_runtime_event_to_fitness_event(runtime_event)
    response = handle_openclaw_event(event, provider="demo")
    return convert_fitness_response_to_runtime_reply(response)
```

The wrapper should:

- convert runtime fields into the existing OpenClaw-like event schema;
- call `handle_openclaw_event(...)`;
- return the runtime's expected reply or handoff payload;
- avoid hard-coded real WeChat users;
- avoid secrets;
- avoid writing unknown users into `default`;
- avoid sending messages unless the runtime API explicitly requires it.

## Skill-level Invocation Guidance

For text, image, and command input from a channel, prefer:

```python
from agents.fitness.channel_adapter import handle_channel_message
```

For OpenClaw-like events, prefer:

```python
from agents.fitness.integrations.openclaw_adapter import handle_openclaw_event
```

For legacy text-only local use, this remains compatible:

```python
from agents.fitness.handler import handle_fitness_message
```

Non-fitness requests must hand off to the main Agent. Image diet records should enter through the channel adapter or OpenClaw adapter, not direct vision-tool calls. User-facing chat must not expose debug JSON. Channel users should be resolved from channel and sender metadata instead of defaulting to `default`. Recall remains opt-in and does not proactively push messages.
