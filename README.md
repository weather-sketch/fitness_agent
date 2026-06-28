# Fitness Agent

Fitness Agent is an OpenClaw sub-agent for personal training and nutrition coordination. It is designed for long-running health-management workflows that need structured state, lightweight tools, candidate memory, and low-pressure recall state.

The existing `skills/weixin-calorie-manager` remains unchanged. Fitness Agent v0.1 starts as a separate implementation path so calorie tracking keeps working while the broader training/nutrition agent is built incrementally.

## v0.1 Scope

v0.1 is a minimal demonstrable foundation. It includes:

- Basic sub-agent documentation and boundaries.
- Minimal schemas for profile, daily state, cycle state, recall state, and memory candidates.
- Empty initial JSON state files.
- Tool module skeletons with narrow responsibilities.
- Demo fixtures for training day planning, meal logging, post-workout recovery, lapse recovery, and weekly review.
- A local CLI for running individual flows.
- A one-command portfolio demo runner.
- A lightweight workflow skill under `skills/fitness-coach`.

v0.1 intentionally does not include:

- Full scheduler automation.
- External wearable, sleep, workout, or weight integrations.
- Food photo recognition.
- Complex long-term memory writes.
- Full workout planning or posture analysis.
- Medical diagnosis or clinical nutrition advice.

## Run Tests

From the workspace root:

```bash
python3 -m unittest agents/fitness/tests/test_fitness_tools.py
```

The unit tests use a temporary data directory and do not modify `agents/fitness/data/`.

## Run The CLI

The CLI runs one local flow at a time and uses `agents/fitness/data/` as its state store:

```bash
python3 agents/fitness/tools/fitness_cli.py daily-plan "今天晚上练臀，怎么吃？"
python3 agents/fitness/tools/fitness_cli.py log-meal "中午吃了一碗牛肉面。"
python3 agents/fitness/tools/fitness_cli.py log-workout "练完了，今天强度很大，练后吃什么？"
python3 agents/fitness/tools/fitness_cli.py lapse "我今天吃爆了，不想记了。"
python3 agents/fitness/tools/fitness_cli.py weekly-review
```

## State Backup And Validation

Fitness Agent includes a local admin CLI for state validation, manual backups, and dry-run restore. This is for maintenance only; it is not exposed to normal chat users.

```bash
python3 agents/fitness/tools/fitness_admin_cli.py validate --user default
python3 agents/fitness/tools/fitness_admin_cli.py backup --user default --label before-routing
python3 agents/fitness/tools/fitness_admin_cli.py list-backups --user default
python3 agents/fitness/tools/fitness_admin_cli.py restore --user default --backup-id <id> --dry-run
python3 agents/fitness/tools/fitness_admin_cli.py restore --user default --backup-id <id> --apply
```

Backups are stored outside the active state tree under `agents/fitness/data_backups/users/<user_id>/<backup_id>/`. Restore is dry-run by default and creates a pre-restore backup before applying changes.

## Memory Candidate Review

Fitness Agent can store conservative long-term memory candidates for explicit preferences, corrections, feedback style, routines, and repeated behavior patterns. Candidates are not active memory by default and require admin review.

```bash
python3 agents/fitness/tools/fitness_memory_cli.py list --user default
python3 agents/fitness/tools/fitness_memory_cli.py list --user default --status candidate
python3 agents/fitness/tools/fitness_memory_cli.py active --user default
python3 agents/fitness/tools/fitness_memory_cli.py approve --user default --candidate-id <id>
python3 agents/fitness/tools/fitness_memory_cli.py reject --user default --candidate-id <id> --note "not stable"
python3 agents/fitness/tools/fitness_memory_cli.py archive --user default --candidate-id <id>
```

Ordinary one-off meal logs and workout logs should remain daily state, not long-term memory candidates.

Repeated candidates with the same `type` and `key` merge evidence instead of creating duplicates while their status is `candidate` or `approved`. Rejected and archived candidates are not merged into.

Approved candidates can also write active preferences into `profile.json`. For example, approving `avoid_yogurt_pre_workout` makes later training-day recommendations avoid yogurt. See `docs/ACTIVE_MEMORY_APPLICATION.md`.

## Opt-in Recall Suggestions

Fitness Agent can generate low-pressure recall suggestions after explicit opt-in. This is only a local rules engine: it does not schedule, push, or send messages by itself.

```bash
python3 agents/fitness/tools/fitness_recall_cli.py status --user default
python3 agents/fitness/tools/fitness_recall_cli.py opt-in --user default
python3 agents/fitness/tools/fitness_recall_cli.py opt-out --user default
python3 agents/fitness/tools/fitness_recall_cli.py suggest --user default
python3 agents/fitness/tools/fitness_recall_cli.py suggest --user default --type lapse_recovery_followup
```

Default recall state is `enabled=false`. `suggest` can preview what the agent would say, but `should_send=true` only after opt-in and outside cooldown. See `docs/OPT_IN_RECALL_RULES.md` for recall types and copy rules.

## Run The One-Command Demo

For portfolio or interview review:

```bash
python3 agents/fitness/run_demo.py
```

The demo prints five readable flows with detected intent, tool chain, agent reply, key state changes, and product highlights.

Demo state is isolated under `agents/fitness/demo_data/`. The runner rebuilds that directory on every run and does not read or modify real state under `agents/fitness/data/`.

For a concise walkthrough, see `DEMO.md`.

To preview opt-in recall behavior without touching real state:

```bash
python3 agents/fitness/run_recall_demo.py
```

To show an approved memory changing later recommendations:

```bash
python3 agents/fitness/run_memory_demo.py
```

## Run The Showcase Demo And Playground

For recording, screenshots, portfolio review, or interview walkthroughs, use the unified showcase runner:

```bash
python3 agents/fitness/run_showcase_demo.py
python3 agents/fitness/run_showcase_demo.py --flow all
python3 agents/fitness/run_showcase_demo.py --flow text
python3 agents/fitness/run_showcase_demo.py --flow vision
python3 agents/fitness/run_showcase_demo.py --flow memory
python3 agents/fitness/run_showcase_demo.py --flow recall
python3 agents/fitness/run_showcase_demo.py --flow fallback
python3 agents/fitness/run_showcase_demo.py --flow channel
python3 agents/fitness/run_showcase_demo.py --flow openclaw
```

The showcase runner writes only under `agents/fitness/demo_data/showcase/` and prints that real state under `agents/fitness/data/` is not read or modified.

For a lightweight local interactive experience:

```bash
python3 agents/fitness/playground.py
```

The playground uses `agents/fitness/demo_data/playground/` by default and does not depend on external APIs. See `docs/DEMO_PLAYGROUND.md`.

## Channel Adapter / OpenClaw-ready Router

Fitness Agent includes a local channel adapter contract for IM/OpenClaw-style message routing. It does not call WeChat SDKs, does not connect to OpenClaw runtime, and does not send real messages.

Step 6 runtime discovery found no real OpenClaw dispatcher, WeChat SDK callback, or plugin manifest in this workspace. Current binding mode is skill-guided and OpenClaw-ready, not real runtime binding.

Current best path to real WeChat testing is skill-guided routing, not direct runtime binding, because no dispatcher/callback API is exposed in this workspace.

```bash
python3 agents/fitness/run_channel_demo.py
python3 agents/fitness/tools/fitness_channel_cli.py text --text "今天晚上练臀，怎么吃？" --channel wechat --sender demo_user --date 2026-06-24
python3 agents/fitness/tools/fitness_channel_cli.py image --image agents/fitness/demo_assets/vision/beef_noodle_demo.jpg --text "午餐" --channel wechat --sender demo_user --date 2026-06-24 --provider demo
python3 agents/fitness/tools/fitness_channel_cli.py command --text "/fitness help" --channel wechat --sender demo_user
```

The adapter maps `channel + sender_id` to a stable Fitness `user_id`, routes text/image/command messages, and returns a channel-safe response object. Non-fitness messages return `handled=false` and `handoff=true` so the main agent can handle them. See `docs/CHANNEL_ADAPTER.md`.

## OpenClaw Integration Scaffold

Fitness Agent also includes an OpenClaw-ready integration scaffold. It converts OpenClaw-like runtime events into the channel message schema, calls the channel adapter, and returns an OpenClaw-compatible response payload. It does not bind to the real OpenClaw runtime or send messages.

```bash
python3 agents/fitness/run_openclaw_integration_demo.py
python3 agents/fitness/tools/fitness_openclaw_cli.py text --text "今天晚上练臀，怎么吃？" --channel wechat --sender demo_user --conversation conv_demo --date 2026-06-24
python3 agents/fitness/tools/fitness_openclaw_cli.py image --image agents/fitness/demo_assets/vision/beef_noodle_demo.jpg --text "午餐" --channel wechat --sender demo_user --conversation conv_demo --date 2026-06-24 --provider demo
python3 agents/fitness/tools/fitness_openclaw_cli.py command --text "/fitness help" --channel wechat --sender demo_user --conversation conv_demo
```

Non-fitness events return a `handoff_payload` targeting `main_agent`. See `docs/OPENCLAW_INTEGRATION.md`.

For a read-only local binding check:

```bash
python3 agents/fitness/tools/fitness_binding_check.py
python3 agents/fitness/tools/fitness_wechat_routing_check.py
```

See `docs/OPENCLAW_RUNTIME_DISCOVERY.md` for the discovery summary and future thin-wrapper guidance. See `docs/WECHAT_MANUAL_TEST_GUIDE.md` for real WeChat hand testing through main-Agent skill routing.

## Proactive Recall Outbox

Fitness Agent v0.5 adds a proactive recall outbox and scheduled worker. The outbox remains the safety buffer:

```text
recall opportunity -> outbox pending item
```

Recall must be opt-in. Delivery modes are `dry_run`, `console`, safety-gated `openclaw_message`, and unavailable placeholder `future_openclaw`.

```bash
python3 agents/fitness/run_proactive_recall_demo.py
python3 agents/fitness/run_scheduled_recall_demo.py
python3 agents/fitness/tools/fitness_recall_worker.py run-once --user wechat_demo_user --date 2026-06-24 --channel wechat --dry-run
python3 agents/fitness/tools/fitness_recall_worker.py scheduled-run --user wechat_demo_user --date 2026-06-24 --dry-run
python3 agents/fitness/tools/fitness_recall_worker.py list-outbox --user wechat_demo_user
python3 agents/fitness/tools/fitness_recall_worker.py clear-outbox --user wechat_demo_user
```

See `docs/PROACTIVE_RECALL_OUTBOX.md` and `docs/SCHEDULED_PROACTIVE_RECALL.md`.

## OpenClaw Message Delivery

Fitness Agent can now dry-run OpenClaw outbound delivery for recall outbox items through:

```text
openclaw message send -> openclaw-weixin
```

This is not a direct WeChat SDK call and it is not automatic scheduled push. Default behavior is dry-run. Real sending requires explicit `--send --confirm-send` plus user delivery config with `enabled=true` and `allow_real_send=true`.

```bash
python3 agents/fitness/run_openclaw_delivery_demo.py
python3 agents/fitness/tools/fitness_delivery_cli.py test-wechat --user wechat_demo_user --message "dry run test" --dry-run
python3 agents/fitness/tools/fitness_recall_worker.py run-once --user wechat_demo_user --date 2026-06-24 --channel wechat --delivery-mode openclaw_message --dry-run
```

`@im.wechat` targets are case-sensitive. Configure the exact target from OpenClaw inbound metadata; do not lowercase it.

## Scheduled Proactive Recall

Fitness Agent can generate local launchd plist and cron snippets that trigger:

```text
fitness_recall_worker.py scheduled-run
```

The generator does not install system jobs automatically. Scheduled real sending is off by default and requires all gates: recall opt-in, scheduler enabled, scheduler real-send enabled, delivery config enabled, `allow_real_send=true`, exact-case target, account id, and command-level `--send --confirm-send`.

```bash
python3 agents/fitness/tools/fitness_scheduler_cli.py configure --user wechat_self_test --enable --channel wechat --delivery-mode openclaw_message --hours 9,18,21 --timezone Asia/Shanghai --max-runs-per-day 3
python3 agents/fitness/tools/fitness_recall_worker.py scheduled-run --user wechat_self_test --date 2026-06-24 --dry-run
python3 agents/fitness/tools/fitness_scheduler_install.py print-launchd --user wechat_self_test --time "21:00" --dry-run
python3 agents/fitness/tools/fitness_scheduler_install.py print-cron --user wechat_self_test --time "21:00"
```

See `docs/OPENCLAW_MESSAGE_DELIVERY.md` and `docs/SCHEDULED_PROACTIVE_RECALL.md`.

## Food Photo Logging And Vision Provider Demo

Fitness Agent includes a food-photo adapter for low-friction meal logging. It is not a high-precision vision system. v0.4 adds a replaceable provider contract so demo, manual, and future vision providers all produce the same coarse structure: food category, calorie range, protein estimate, confidence, uncertainty factors, and a correction path.

```bash
python3 agents/fitness/run_vision_demo.py
python3 agents/fitness/run_vision_provider_demo.py
python3 agents/fitness/tools/fitness_vision_cli.py analyze --image agents/fitness/demo_assets/vision/beef_noodle_demo.jpg --provider demo
python3 agents/fitness/tools/fitness_vision_cli.py analyze --image agents/fitness/demo_assets/vision/beef_noodle_demo.jpg --provider manual --manual-food "牛肉面" --manual-category noodle --manual-confidence medium
python3 agents/fitness/tools/fitness_vision_cli.py log --image agents/fitness/demo_assets/vision/beef_noodle_demo.jpg --user v04_vision_check --note "午餐" --date 2026-06-24 --provider manual --manual-food "牛肉面" --manual-category noodle --manual-confidence medium
```

Supported providers:

- `demo`: deterministic filename/note fixture provider for local demos.
- `manual`: structured manual description for real-image walkthroughs without an API key.
- `vision_api`: safe placeholder contract; not enabled by default and does not call external APIs in this version.
- `auto`: tries `vision_api` and falls back to the configured fallback provider when unavailable.

Core value: image -> structured food analysis -> rough estimate -> user confirmation/correction -> existing daily meal state. Food photo logs use `source="image"` and do not create memory candidates. See `docs/FOOD_PHOTO_DEMO.md` and `docs/VISION_PROVIDER_ADAPTER.md`.

For acceptance checks, read the same explicit date and use the canonical meal list at `state["nutrition"]["meals"]`. If `--date` is omitted, the CLI writes to the date returned by `get_today_str()` when the command runs.

## Run The Routed Demo

To test the thin OpenClaw-style message entry point locally:

```bash
python3 agents/fitness/run_routed_demo.py
```

The routed demo calls `handle_fitness_message(...)` from `agents/fitness/handler.py`, prints whether each message was handled, and shows the detected intent, tool chain, and IM-ready reply. It uses the same isolated `agents/fitness/demo_data/` directory as the one-command demo.

## v0.1 Capability Boundaries

Current v0.1 behavior is deterministic and local-only:

- It can classify basic training, meal, post-workout, lapse recovery, and weekly-review flows.
- It can update small local JSON state files.
- It exposes a thin local routing handler for future OpenClaw channel binding.
- It uses rough calorie and protein estimates for a few demo food categories.
- It avoids extreme dieting, punitive exercise, and shaming language.
- It is not connected to a direct WeChat SDK, external health APIs, or production image recognition.
- It does not perform medical diagnosis or complex long-term memory writes.

## Directory Structure

```text
agents/fitness/
  README.md
  DEMO.md
  run_demo.py
  run_routed_demo.py
  router.py
  handler.py
  AGENT.md

  schemas/
    profile.schema.json
    daily_state.schema.json
    cycle_state.schema.json
    recall_state.schema.json
    memory_candidate.schema.json

  tools/
    fitness_state.py
    fitness_logic.py
    fitness_cli.py

  data/
    profile.json
    daily_state.json
    cycle_state.json
    recall_state.json
    memory_candidates.json

  demo_data/
    generated by run_demo.py; safe to delete

  tests/
    fixtures/
      training_day.json
      lapse_recovery.json
      weekly_review.json
```

## Design Notes

- `AGENT.md` defines the sub-agent boundary and routing expectations.
- `schemas/` defines the smallest useful v0.1 state contract.
- `data/` stores local structured state for this sub-agent only.
- `tools/` will hold deterministic state and planning helpers.
- `tests/fixtures/` captures demo flows before implementation expands.
- `skills/fitness-coach/SKILL.md` is a workflow instruction layer, not the state store or business-logic engine.
