---
name: "fitness-coach"
description: "Fitness Agent workflow for training, nutrition, recovery, recall, and weekly review."
---

# Fitness Coach Workflow

Use this skill when routing messages to Fitness Agent for training, nutrition,
meal logging, calories, protein, pre-workout meals, post-workout meals,
recovery, lapse recovery, proactive recall, or weekly review.

This public skill file is a routing and workflow guide only. Structured state,
tools, fixtures, recall state, and memory candidates live under
`agents/fitness/`. Do not store personal user state, WeChat targets, account
IDs, tokens, delivery configs, scheduler configs, outboxes, or logs in this
skill.

Current status: skill-guided local integration and OpenClaw-ready scaffolding.
Do not claim real WeChat integration. Do not claim real OpenClaw runtime
integration. The public repository must not include real channel credentials or
real runtime binding data.

## Entry Points

For IM-style text, image, and command messages, prefer the channel adapter:

```python
from agents.fitness.channel_adapter import handle_channel_message

result = handle_channel_message(
    {
        "channel": channel,
        "sender_id": sender_id,
        "conversation_id": conversation_id,
        "type": "text",
        "text": user_text,
    },
    date=date,
)
```

For OpenClaw-like event objects, prefer the integration scaffold:

```python
from agents.fitness.integrations.openclaw_adapter import handle_openclaw_event

result = handle_openclaw_event(runtime_like_event, provider="demo")
```

For legacy local text-only calls, use:

```python
from agents.fitness.handler import handle_fitness_message

result = handle_fitness_message(user_text, user_id=user_id, channel=channel, date=date)
```

If the adapter or handler returns `handled=True`, send only the user-facing
reply text. Never expose debug fields, state changes, tool chains, safety
internals, or raw JSON to chat users.

If it returns `handled=False`, `handoff=True`, or cannot complete safely, hand
off the non-fitness request to the main agent. Non-fitness requests must not be
forced into Fitness Agent.

## Safety

Do not recommend extreme restriction, skipping meals as compensation, punitive
workouts, or training through meaningful pain or severe fatigue. Keep replies
short, concrete, non-judgmental, and focused on restoring rhythm.
