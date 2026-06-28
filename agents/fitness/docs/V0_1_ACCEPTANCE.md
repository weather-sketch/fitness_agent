# Fitness Agent v0.1 Acceptance Report

## Completed Modules

- Independent Fitness sub-agent directory.
- Agent boundary documentation in `AGENT.md`.
- Local JSON schemas and state files.
- Deterministic state helpers.
- Deterministic fitness logic tools.
- CLI for individual flows.
- One-command demo runner.
- Rule-based router.
- Unified local handler.
- Routed demo runner.
- Unit tests for tools, router, and handler.
- Portfolio and acceptance documentation.

## Not Completed In v0.1

- OpenClaw channel binding.
- Scheduler or proactive recall delivery.
- External APIs or wearable integrations.
- Food image recognition.
- Complex long-term memory writes.
- Full workout planning.
- Medical diagnosis or clinical treatment logic.

## Verification Commands

```bash
python3 agents/fitness/run_demo.py
python3 agents/fitness/run_routed_demo.py
python3 -m unittest discover -s agents/fitness/tests
```

## Test Result

Latest local test run:

```text
Ran 17 tests in 0.020s

OK
```

## Five Demo Flow Acceptance

- Training day nutrition plan: passed. The demo detects a lower-body evening training day and generates pre-workout and post-workout nutrition guidance.
- Meal logging and dynamic adjustment: passed. The demo logs beef noodles with a rough calorie range and updates remaining calories and protein.
- Post-workout meal suggestion: passed. The demo records completed high-intensity training and recommends recovery-oriented food.
- Lapse recovery: passed. The demo detects "ate too much / do not want to log" language and shifts to a non-shaming recovery plan.
- Lightweight weekly review: passed. The demo summarizes weekly training, meal logging, over-budget days, recovery success, and one next-week focus.

## Routed-Message Acceptance

- "今天晚上练臀，怎么吃？" routes to `daily_plan` and is handled.
- "中午吃了一碗牛肉面" routes to `log_meal` and is handled.
- "练完了，今天强度很大，练后吃什么？" routes to `post_workout_meal` and is handled.
- "我今天吃爆了，不想记了" routes to `lapse_recovery` and is handled.
- "这周怎么样？" routes to `weekly_review` and is handled.
- Non-fitness input routes to `unknown` and returns `handled=False`.

## Safety Boundary Check

v0.1 replies are designed to avoid:

- Extreme restriction.
- Skipping meals as compensation.
- Punitive exercise.
- Shaming language.
- False medical diagnosis.
- Overconfident precision around rough food estimates.

Safety-sensitive language in lapse recovery pushes toward hydration, normal next meal, protein, vegetables, and returning to rhythm.

## State Isolation Check

The demo runners use `agents/fitness/demo_data/`.

The real local state under `agents/fitness/data/` is not modified by:

```bash
python3 agents/fitness/run_demo.py
python3 agents/fitness/run_routed_demo.py
python3 -m unittest discover -s agents/fitness/tests
```

Tests use temporary data directories. Demo output generation uses isolated demo data.

## Portfolio Demo Readiness

v0.1 meets the portfolio demo standard because it shows:

- A real vertical-agent boundary.
- Deterministic routing and tool calls.
- Local state updates.
- Demo output that is understandable without reading JSON.
- Tests for tools and routing.
- Clear scope limits and safety boundaries.

The project should be presented as a local v0.1 prototype, not a fully deployed production health product.
