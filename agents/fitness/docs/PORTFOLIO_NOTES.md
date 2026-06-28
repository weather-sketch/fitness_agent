# Fitness Agent v0.1 Portfolio Notes

## Project Background

Fitness Agent started as a separate implementation path from the existing calorie skill. The goal was to explore a vertical OpenClaw sub-agent that can coordinate training, nutrition, recovery, lapse recovery, and weekly review with structured local state.

## User Pain Points

- Food logging alone does not understand training context.
- Training-day nutrition needs are different from rest-day calorie control.
- After overeating, users often stop logging entirely.
- Weekly reviews often focus on failure instead of recovery and continuity.
- Prompt-only agents can sound helpful but fail to maintain reliable state.

## Product Goal

Build a small, testable Fitness sub-agent that helps the user make practical training and nutrition decisions while preserving state boundaries and avoiding shame-based feedback.

## Agent Architecture

The project uses a vertical sub-agent pattern:

- Main Agent: owns broad conversation and future channel routing.
- Fitness Skill: tells the main agent when and how to route fitness-domain messages.
- Router: detects Fitness intent through deterministic rules.
- Handler: calls the right local tools and returns an IM-ready response.
- Tools: implement deterministic planning, logging, recovery, and review logic.
- State: stores local profile, daily state, cycle state, recall state, and memory candidates.
- Demo/Test: prove the flow without connecting external services.

## Core Modules

- `router.py`: rule-based intent detection.
- `handler.py`: unified message entry point.
- `fitness_logic.py`: deterministic business logic.
- `fitness_state.py`: local JSON state management.
- `run_demo.py`: portfolio demo with five product flows.
- `run_routed_demo.py`: routed-message demo with handled/unhandled examples.
- `tests/`: unit tests for tools, router, and handler.

## Demo Flow

- Training day nutrition plan.
- Meal logging and dynamic adjustment.
- Post-workout meal suggestion.
- Lapse recovery after overeating.
- Lightweight weekly review.
- Routed-message fallback for non-fitness input.
- Food photo logging demo: image input -> rough estimate -> confirmation/correction -> daily meal log.

## Showcase Runner

v0.4 Step 3 packages the scattered demos into one recording-friendly runner:

```bash
python3 agents/fitness/run_showcase_demo.py
```

The runner presents six fixed flows:

- training day food plan;
- lapse recovery;
- food photo logging through the provider adapter;
- memory candidate approval and active preference application;
- opt-in recall before/after state;
- non-fitness fallback;
- channel adapter routing for simulated WeChat/IM messages;
- OpenClaw integration scaffold with response payload and handoff payload.

Each flow shows only the user input, IM-ready reply, key state/provider summary, and product highlight by default. Full structured details are available with `--debug`.

For lightweight hands-on exploration:

```bash
python3 agents/fitness/playground.py
```

Both entry points use isolated demo state under `agents/fitness/demo_data/` and do not read or modify the real default user state.

## Channel Adapter / OpenClaw-ready Router

v0.4 Step 4 adds a local channel adapter contract:

```text
channel message -> user mapping -> Fitness routing -> channel-safe response
```

It supports text, image, and command messages without depending on a real WeChat SDK or OpenClaw runtime. The adapter maps `channel + sender_id` into a stable Fitness `user_id`, routes fitness text to the existing handler, routes image messages to the food-photo provider adapter, and returns `handled=false / handoff=true` for non-fitness requests.

Portfolio framing:

```text
Designed a Channel Adapter that abstracts WeChat/IM messages into a unified message schema and routes them to Fitness Agent text, image, memory, and recall capabilities. Non-health requests are handed back to the main agent to preserve the vertical Agent boundary.
```

Do not claim this as real WeChat production integration.

## OpenClaw Integration Scaffold

v0.4 Step 5 adds an OpenClaw-ready integration layer:

```text
OpenClaw-like runtime event -> normalized channel message -> Fitness Channel Adapter -> OpenClaw-compatible response payload
```

The scaffold keeps the runtime boundary explicit. Fitness can return a channel-safe text reply for handled messages, or a `handoff_payload` for non-fitness messages:

```text
target=main_agent
reason=non_fitness_intent
```

Portfolio framing:

```text
Designed an OpenClaw-ready Integration Scaffold that standardizes runtime events into the Fitness channel message contract, reuses the Channel Adapter for text/image/command routing, and returns either a reply payload or main-agent handoff payload.
```

Do not claim this as real OpenClaw runtime binding.

## Runtime Binding Discovery

v0.4 Step 6 inspected the workspace for a real OpenClaw runtime dispatcher, WeChat SDK callback, message callback, skill/plugin manifest, or runtime entrypoint. None was exposed in the current workspace.

Discovery summary:

- Real OpenClaw runtime entrypoint: not found.
- Real WeChat / IM message callback: not found.
- Runtime plugin manifest: not found.
- Main Agent invocation convention: route Fitness-domain messages via workspace skill guidance and return only user-facing replies.

Resulting framing:

```text
OpenClaw-ready scaffold and skill-guided binding, not real OpenClaw runtime integration.
```

The next real integration should be a thin wrapper around `handle_openclaw_event(...)`, once the runtime exposes its event and reply API.

## Proactive Recall Outbox

v0.5 Step 1 upgrades recall suggestions into a conservative outbox model:

```text
recall rules -> opt-in / cooldown / quiet hours / duplicate guard -> recall_outbox pending item
```

This is not real proactive push. The delivery adapter currently supports `dry_run` and `console` preview only. `future_openclaw` is an explicit unavailable placeholder and must fail until a real OpenClaw send API exists.

v0.5 Step 2 adds `openclaw_message` delivery through `openclaw message send` and the `openclaw-weixin` channel plugin. It is still gated: dry-run by default, no direct WeChat SDK calls, and real send requires `--send --confirm-send` plus user delivery config with `enabled=true` and `allow_real_send=true`.

v0.5 Step 3 adds a scheduled proactive recall worker and local launchd/cron snippet generation:

```text
local scheduler -> scheduled-run -> outbox -> openclaw_message delivery
```

It does not auto-install system jobs and does not default to real sending. Real automatic WeChat delivery requires opt-in, scheduler enablement, scheduler real-send enablement, delivery config enablement, `allow_real_send=true`, exact-case `@im.wechat` target, account id, and explicit `--send --confirm-send`.

Portfolio framing:

```text
Built a proactive recall outbox and scheduled worker as a safety buffer before real messaging: opt-in required, quiet hours respected, duplicates guarded, exact-case WeChat targets preserved, and real sending disabled unless every explicit gate is enabled.
```

Do not claim this as an always-on production push system. It is a local scheduled trigger path with conservative real-send gates.

## Design Highlights

- The product is not just calorie tracking; it coordinates training, recovery, and nutrition.
- Unknown inputs are handed back to the main agent instead of forcing a wrong answer.
- State updates are deterministic and testable.
- Demo state is isolated from real state.
- Safety is designed into the product tone and tool outputs.
- Food photo logging is positioned as a low-friction demo adapter, not high-precision recognition.

## Food Photo Logging And Vision Provider Demo

The v0.4 Food Photo Demo Adapter adds an image entry point for meal logging. Step 2 extends it into a replaceable Vision Provider Adapter. The product goal is to reduce recording friction, not to pretend exact nutrition recognition.

The adapter returns:

- provider and fallback status;
- coarse detected food;
- calorie range;
- rough protein estimate;
- confidence;
- uncertainty factors;
- correction prompt.

The logged result uses the same daily meal state as text meal logs and adds `source="image"`. Ordinary food photos do not create memory candidates or long-term preferences.

Supported provider modes:

- `demo`: stable local fixture provider for portfolio demos and tests.
- `manual`: structured food description for real-image walkthroughs without API dependency.
- `vision_api`: placeholder contract for future real image understanding, disabled by default.
- `auto`: explicit fallback flow when the real provider is unavailable.

This creates a clean product contract:

```text
image -> structured food analysis -> rough estimate -> confirmation/correction -> daily meal log
```

## Technical Implementation

- Python-only local prototype.
- JSON files as the local state store.
- Rule-first routing.
- Thin handler that reuses existing deterministic tools.
- No scheduler, default external API call, database, or high-precision image recognition.
- No real WeChat/OpenClaw dispatcher binding; channel adapter is a local contract and simulator.
- OpenClaw integration is a scaffold and simulator, not a runtime plugin.
- Step 6 binding discovery found no real runtime binding point exposed in this workspace.
- v0.5 proactive recall creates outbox items only; it does not send real messages.
- v0.5 OpenClaw message delivery is manual and safety-gated; it is not automatic scheduled push.
- Unit tests run through Python `unittest`.

## Product Capability Reflected

- Defined a scoped vertical-agent problem instead of adding prompt complexity to a generic assistant.
- Separated workflow instructions, routing, tools, state, and future memory/recall responsibilities.
- Designed demos and acceptance checks that show real stateful behavior without overclaiming production readiness.
- Packaged the prototype into a repeatable showcase/playground so the workflow can be evaluated as a product experience, not just as separate scripts.

## Resume Bullets

- Designed and prototyped a stateful Fitness sub-agent for OpenClaw, separating skill instructions, deterministic tools, local JSON state, intent routing, and IM-ready handler output.
- Built five demo flows covering training-day nutrition, meal logging, post-workout recovery, lapse recovery, and weekly review, with isolated demo state and test coverage.
- Defined v0.1 product boundaries and safety constraints for a health-adjacent agent, including conservative fallback behavior and non-shaming recovery guidance.
