# Fitness Routing Integration Check

Date: 2026-06-20

## Scope

This check covers Fitness Agent v0.1 natural-language routing readiness. It does not add scheduler behavior, proactive recall, external APIs, image recognition, multi-user state, or OpenClaw runtime/channel changes.

## Manual Trigger Baseline

Manual trigger was previously verified through OpenClaw/WeChat by asking the main Agent to call `agents/fitness/handler.py::handle_fitness_message(...)`.

Verified effects:

- `agents/fitness/data/daily_state.json` was written.
- `day_type` became `training_day`.
- `training.type` became `glutes`.
- `training.time` became `evening`.
- A workout log was appended.

## Natural-Language Trigger Check

Test message:

```text
今天晚上练臀，怎么吃？
```

Local validation path:

- Called the same Fitness entry point through a local main-agent routing adapter pattern.
- Checked `agents/fitness/data/daily_state.json`.
- Backed up and restored the real state after validation to avoid lasting state pollution.

Expected:

- Fitness handler is called.
- `handled=True`.
- Intent is `daily_plan`.
- State reflects an evening glutes training day.
- Workout count increases during the validation call.
- User-visible reply resembles the Fitness Agent demo structure.
- User-visible reply does not expose `debug`, `state_changes`, `tool_chain`, or raw JSON.

Actual local result:

- `handled=True`.
- Intent: `daily_plan`.
- Reply included the demo-style structure: day type, training-day focus, pre-workout, post-workout, dinner, and minimum action.
- `workout_count` changed from 1 to 2 during validation.
- `day_type` remained `training_day`.
- `training.type` was `glutes`.
- `training.time` was `evening`.
- No debug JSON was present in the user-visible reply.
- The original real state file was restored after the check.

## Fallback Check

Fallback test message:

```text
帮我整理明天的会议
```

Expected:

- Fitness handler does not handle it.
- No Fitness state write.
- Main Agent can continue normal handling.

Actual local result:

- `handled=False`.
- Intent: `unknown`.
- Reply was empty.
- `agents/fitness/data/daily_state.json` did not change.

## Routing Instruction Updates

Updated instruction surfaces now state that natural-language Fitness-domain messages should call:

```python
agents/fitness/handler.py::handle_fitness_message(...)
```

The user-visible response must use only `result["reply"]`. `debug`, `state_changes`, `tool_chain`, safety internals, and raw JSON must not be exposed. `handled=False` or handler errors must fall back to the main Agent.

## Current Limitations

- True OpenClaw/WeChat channel binding was not changed in this stage.
- This check verifies local routing behavior and instruction-level integration readiness, not a production channel hook.
- Fitness routing is intentionally narrow and should not catch unrelated messages.
- State is still single-user local JSON under `agents/fitness/data/`.

## Needed For Real Channel Binding

To verify true natural use in WeChat/OpenClaw, the next stage needs:

- The exact OpenClaw message-dispatch entry point used by the WeChat channel.
- How the main Agent selects and invokes workspace skills or sub-agent handlers.
- User/channel identity fields to pass as `user_id` and `channel`.
- A safe fallback contract for `handled=False` and exceptions.
- A small integration test or trace showing the direct message "今天晚上练臀，怎么吃？" invokes `handle_fitness_message(...)` without the user naming the handler.
