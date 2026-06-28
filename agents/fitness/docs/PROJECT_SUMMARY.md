# Fitness Agent v0.1 Project Summary

## Project Name

Fitness Agent v0.1

## One-Line Positioning

A local OpenClaw vertical sub-agent that coordinates training, nutrition, recovery, lapse recovery, and lightweight weekly review through deterministic tools and structured state.

## Why This Is Not Just A Calorie Skill

The legacy calorie skill mainly answers food and calorie-tracking needs. Fitness Agent is broader: it treats nutrition as part of a training and recovery loop.

Instead of only asking "how many calories did this meal have?", the agent keeps track of:

- Today's training context: planned or completed workout, body part, timing, and intensity.
- Nutrition state: calorie budget, rough consumed calories, protein target, and meal logs.
- Recovery state: soreness, fatigue, and recovery need.
- Lapse recovery: non-shaming support when the user overeats or wants to stop logging.
- Cycle state: weekly training, logging, over-budget days, recovery wins, and next-week focus.
- Future recall readiness: recall state exists for later scheduler integration, but proactive recall is not enabled in v0.1.

This makes it a vertical health-management sub-agent rather than a prompt-only calorie calculator.

## v0.1 Completed Capabilities

- Independent `agents/fitness/` directory with agent boundary docs.
- JSON schemas and local JSON state for profile, daily state, cycle state, recall state, and memory candidates.
- Deterministic tools for day classification, daily plan generation, meal logging, workout logging, pre/post-workout meal suggestions, lapse recovery, and weekly review.
- CLI entry point for individual local flows.
- One-command demo runner with five showcase flows.
- Rule-based router for Fitness-domain intent detection.
- Unified handler for OpenClaw-style message handling.
- Routed demo that shows handled/unhandled messages.
- Unit tests covering tools, router, and handler.
- Documentation and demo outputs suitable for portfolio review.

## Current Architecture

Fitness Agent is organized as a thin vertical agent stack:

- `skills/fitness-coach/SKILL.md`: workflow instruction layer for the main agent.
- `agents/fitness/router.py`: deterministic intent detection.
- `agents/fitness/handler.py`: unified message entry point.
- `agents/fitness/tools/fitness_logic.py`: deterministic business logic.
- `agents/fitness/tools/fitness_state.py`: JSON state read/write helpers.
- `agents/fitness/data/`: real local state.
- `agents/fitness/demo_data/`: isolated demo state.
- `agents/fitness/tests/`: local tests.
- `agents/fitness/demo_outputs/`: saved demo transcripts.

## Core Design Highlights

- Clear separation of skill, routing, tools, state, memory candidates, and recall readiness.
- State updates are tool-driven, not prompt-only.
- Routing is rule-first and conservative; unknown inputs hand back to the main agent.
- Demo uses isolated `demo_data/`, so real state is not polluted.
- Replies avoid shaming, extreme restriction, and punitive exercise.
- Tests cover both deterministic tools and routed-message behavior.

## Not Implemented In v0.1

- Real OpenClaw channel binding.
- Scheduler or proactive notifications.
- External APIs, wearable data, or food databases.
- Food photo recognition.
- Medical diagnosis or clinical nutrition advice.
- Complex long-term memory writes.
- Full workout programming or posture analysis.

## Follow-Up Version Plan

- v0.2: Add a minimal OpenClaw channel binding that calls `handle_fitness_message(...)` and falls back when `handled=False`.
- v0.2: Add integration tests for routed IM messages.
- v0.3: Add opt-in scheduler/recall using existing recall state, without changing the deterministic tool contract.
- v0.4: Add memory candidate review/approval flow for durable preferences and repeated patterns.
- v0.5: Consider external integrations only after local routing, state, safety, and tests are stable.
