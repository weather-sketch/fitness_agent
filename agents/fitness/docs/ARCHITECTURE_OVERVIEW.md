# Fitness Agent Architecture Overview

## Main Agent And Fitness Agent

The main Agent owns the general conversation and future OpenClaw channel routing. Fitness Agent is a vertical sub-agent for training, nutrition, recovery, lapse recovery, weekly review, memory review, and active preferences.

In v0.4, the main Agent can use skill-guided local binding, but no real OpenClaw runtime dispatcher, WeChat callback, or plugin manifest was found in this workspace.

Preferred local integration points are:

```python
from agents.fitness.channel_adapter import handle_channel_message
from agents.fitness.integrations.openclaw_adapter import handle_openclaw_event
```

The legacy text-only entry point remains:

```python
from agents.fitness.handler import handle_fitness_message
```

## Component Relationships

- Fitness Skill: workflow guidance for when the main agent should use Fitness Agent.
- Router: detects Fitness intent using deterministic rules.
- Channel Adapter: local IM/OpenClaw-style message contract for text, image, command, user mapping, and handoff.
- OpenClaw Scaffold: converts OpenClaw-like events into channel messages and returns reply/handoff payloads.
- Handler: legacy text message-processing entry point.
- Tools: deterministic logic for planning, logging, recovery, and review.
- State: local JSON state files.
- Memory Candidate: stores possible durable memories for review.
- Active Preference: approved memory that changes future recommendation behavior.
- Recall State: stores readiness for future recall/scheduler integration, but no scheduler runs in v0.1.
- Demo/Test: local proof that the agent works without OpenClaw channel binding.

## Text Architecture Diagram

```text
User / IM message
  |
  v
Main Agent / future OpenClaw channel routing
  |
  | fitness-domain candidate
  v
skills/fitness-coach/SKILL.md
  |
  | calls adapter entry point
  v
agents/fitness/channel_adapter.py
  |
  | text-only path
  v
agents/fitness/handler.py
  |
  v
agents/fitness/router.py
  |
  | intent + suggested tool chain
  v
agents/fitness/tools/fitness_logic.py
  |
  v
agents/fitness/tools/fitness_state.py
  |
  +--> agents/fitness/tools/fitness_memory.py
  |
  v
agents/fitness/data/*.json
  |
  v
IM-ready reply + debug/state_changes
```

## Data Flow

1. User input arrives from a local demo or future IM channel.
2. The main Agent identifies that the message may belong to the Fitness domain.
3. The Fitness skill instructs the system to use `handle_channel_message(...)`, `handle_openclaw_event(...)`, or the compatible `handle_fitness_message(...)` fallback.
4. The adapter resolves channel user id without defaulting to `default`.
5. The handler calls `detect_fitness_intent(user_text)`.
6. The router returns intent, confidence, reason, and suggested tool chain.
7. If intent is `unknown`, the adapter returns `handled=False` / `handoff=True` for main-Agent fallback.
8. If intent is known, the handler calls existing deterministic tools.
9. Tools read active preferences from `profile.json` and update local JSON state through `fitness_state.py`.
10. Approved memory candidates can write compact active preferences into profile preferences.
11. The adapter returns a concise reply, state summary, and debug metadata.
12. The caller sends only the user-facing reply text to the user.

## Active Memory Flow

```text
user preference text
  |
  v
memory candidate
  |
  | admin approve
  v
profile.preferences.food_avoidance
  |
  v
preference-aware recommendation
```

Example: approving `avoid_yogurt_pre_workout` writes a compact food avoidance rule. Later `generate_daily_plan(...)`, `recommend_pre_workout_meal(...)`, and `recommend_post_workout_meal(...)` filter candidate food options before composing the reply.

Handler debug may record `active_preferences_applied`, but user-visible replies do not expose debug or raw memory JSON.

## Fallback Behavior

Unknown or non-fitness input is not forced into a Fitness answer. The handler returns:

```python
{
  "handled": False,
  "intent": "unknown",
  "reply": "",
  "tool_chain": [],
  "state_changes": {},
  "safety_flags": [],
  "debug": {...}
}
```

This keeps the vertical sub-agent narrow and lets the main Agent continue handling general tasks.

For OpenClaw runtime discovery details, see `OPENCLAW_RUNTIME_DISCOVERY.md`. Current status is OpenClaw-ready scaffold and skill-guided invocation, not real runtime binding.
