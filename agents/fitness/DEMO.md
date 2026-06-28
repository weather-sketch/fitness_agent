# Fitness Agent v0.1 Demo

Fitness Agent is a local OpenClaw sub-agent prototype for coordinating training-day nutrition, meal logging, recovery, lapse handling, and lightweight weekly review.

## Demo Flows

The one-command demo runs five flows:

- Training day nutrition plan: handles "今天晚上练臀，怎么吃？"
- Meal logging and dynamic adjustment: handles "中午吃了一碗牛肉面。"
- Post-workout meal suggestion: handles "练完了，今天强度很大，练后吃什么？"
- Lapse recovery: handles "我今天吃爆了，不想记了。"
- Lightweight weekly review: summarizes local `cycle_state`.

## Run

From the workspace root:

```bash
python3 agents/fitness/run_demo.py
```

The demo uses `agents/fitness/demo_data/`, rebuilds that directory on each run, and does not read or modify real state under `agents/fitness/data/`.

## Product Capabilities Shown

- Training-aware nutrition planning: classifies a lower-body evening training day and suggests practical pre-workout and post-workout meals.
- Low-friction food logging: records a rough calorie range and protein estimate without requiring exact grams.
- Recovery-oriented post-workout guidance: recommends protein, hydration, and moderate carbohydrates after high-intensity training.
- Non-shaming lapse recovery: detects "ate too much / do not want to log" signals and shifts to the next small recovery action.
- Weekly review: combines training count, logging days, over-budget days, recovery success, patterns, wins, and one next-week focus.

## Not Implemented Yet

v0.1 intentionally does not include OpenClaw routing, scheduler automation, external APIs, wearable integrations, food photo recognition, medical diagnosis, complex long-term memory writes, or full workout programming.

## Next: OpenClaw Routing Plan

The next integration step is to keep the deterministic tools unchanged and add a thin OpenClaw routing layer:

- Route fitness-related user messages to this sub-agent based on `AGENT.md`.
- Map routed intents to the existing local tools.
- Keep state writes under `agents/fitness/data/`.
- Add integration tests for routed messages before enabling proactive scheduler or recall behavior.
