# Opt-in Recall Rules

## Why Recall Must Be Opt-in

Fitness recall can feel intrusive if it is enabled by default. The agent may notice gaps, recovery signals, travel, social meals, or weekly review opportunities, but those signals should not become proactive messages unless the user has explicitly opted in.

v0.2 Step 5 keeps recall conservative:

- Default `enabled=false`.
- No scheduler.
- No active push.
- No OpenClaw dispatcher binding.
- No external API.
- Suggestions are generated locally and can be previewed through CLI or demo.

## Recall vs Scheduler

Recall rules answer: "If the system were allowed to follow up, what kind of low-pressure message would fit this state?"

Scheduler answers: "When and how should that message be sent?"

This step only implements the first question. A later scheduler or OpenClaw cron binding can call the rule engine after opt-in, but this module does not send messages by itself.

## Recall State

Recall state lives at:

```text
agents/fitness/data/users/<user_id>/recall_state.json
```

Key fields:

```json
{
  "enabled": false,
  "last_active_at": null,
  "last_recall_at": null,
  "last_recall_type": null,
  "recall_count_recent": 0,
  "cooldown_until": null,
  "preferred_recall_style": "gentle",
  "last_known_context": null,
  "last_risk_signal": null,
  "last_completed_action": null,
  "user_response_to_last_recall": null
}
```

`enabled=false` is the default. CLI/demo can still show what would be suggested if recall were enabled, but `should_send=false` until opt-in.

## Recall Types

- `training_day_no_meal_log`: Training day is planned, there are no or few meal logs, and the day is near the training window.
- `post_workout_no_recovery_meal`: Workout is completed, recovery meal has not been logged/suggested, and meal logs are sparse.
- `lapse_recovery_followup`: Lapse recovery context or high lapse risk exists, with no new meal log yet.
- `travel_or_social_meal_reset`: Travel, social meal, or alcohol context exists, and the next step should be reset rather than backfilling.
- `weekly_review_available`: Current week has enough logged activity for a light review, typically near the weekend.
- `low_data_gentle_restart`: There has been little or no recent data and no special context; the goal is restarting with one small action.
- `none`: No useful recall opportunity.

## should_send

The rule engine returns both `recall_type` and `should_send`.

`should_send=true` only when:

- `recall_type` is not `none`;
- `recall_state.enabled=true`;
- `cooldown_until` is empty or already passed.

If recall is disabled, the engine may still return a useful `recall_type`, but `should_send=false` with `blocked_reason=recall_disabled`.

## Cooldown

`update_recall_state_after_recall(..., sent=True)` records `last_recall_at`, increments `recall_count_recent`, and sets a short cooldown. This is ready for future scheduler integration.

`sent=False` is treated as preview/suggestion and does not create cooldown.

## Message Principles

Recall copy must stay low-pressure:

- Do not say "你又忘了".
- Do not use "你已经 X 天没记录了" as pressure.
- Do not ask the user to backfill every missed record.
- Do not suggest extreme dieting.
- Do not suggest punitive exercise.
- Start from the next meal, today, or one small action.
- Make the reply easy to answer with one sentence.

Typical shape:

```text
不用补前面的记录。你只要回我一句【最小动作】，我就可以帮你【下一步价值】。
```

## CLI

```bash
python3 agents/fitness/tools/fitness_recall_cli.py status --user default
python3 agents/fitness/tools/fitness_recall_cli.py opt-in --user default
python3 agents/fitness/tools/fitness_recall_cli.py opt-out --user default
python3 agents/fitness/tools/fitness_recall_cli.py suggest --user default
python3 agents/fitness/tools/fitness_recall_cli.py suggest --user default --type lapse_recovery_followup
```

`suggest` only prints a suggestion. It does not send anything.

## Handler Integration

The handler supports narrow recall commands:

- `recall_opt_in`: user explicitly says they want reminders, such as "以后可以提醒我记录训练和饮食".
- `recall_opt_out`: user says not to remind or disturb them.
- `recall_suggestion`: user asks how the agent would remind them.

Ordinary fitness messages do not enable recall automatically. Non-fitness messages still fallback to the main agent.

## Current Limits

- Rule-based only; no ML classifier or embedding memory.
- No scheduler, cron, or OpenClaw dispatcher binding.
- No proactive send.
- No multi-device notification preference model.
- Cooldown is local JSON state only.
- Weekly recall uses existing local cycle aggregation; it does not run aggregation automatically.

## Future Scheduler / OpenClaw Cron Binding

A later step can safely bind this to a scheduler by:

1. Requiring explicit user opt-in.
2. Mapping channel user IDs to Fitness `user_id`.
3. Calling `detect_recall_opportunity(...)` at limited times.
4. Sending only when `should_send=true`.
5. Calling `update_recall_state_after_recall(..., sent=True)` after an actual send.
6. Respecting opt-out immediately.

Before enabling real channel delivery, run state backup and validation first.
