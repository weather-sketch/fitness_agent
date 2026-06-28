# Fitness Agent v0.2 Daily Rollover And Weekly Aggregation

## Why Daily Rollover Is Needed

Fitness Agent is now intended for longer-running personal use. A single global `daily_state.json` is not enough because meals, workouts, recovery, and lapse signals belong to a specific local day.

Daily rollover gives each date a clean state file:

```text
agents/fitness/data/users/<user_id>/daily/YYYY-MM-DD.json
```

New days should not inherit meal logs or workout logs from the previous day. They may carry a small summary of the previous day later, but v0.2 keeps rollover deliberately simple.

## Why Weekly Review Should Not Depend Only On Manual Cycle Counters

In v0.1, weekly review could read `cycle/current_week.json`, but that file had to be maintained manually. That is fragile for long-term use.

v0.2 makes weekly review derive its base metrics from daily files:

- Completed workouts.
- Days with meal logs.
- Approximate complete logging days.
- Over-budget days.
- Special contexts.
- Lapse recovery days.
- Recovery success count.
- Training type counts.
- Days with logs.

The cycle file becomes a cached weekly summary, not the only source of truth.

## Data Flow

```text
daily/YYYY-MM-DD.json files
  |
  v
aggregate_week_from_daily(user_id, week_key)
  |
  v
cycle/<week_key>.json
cycle/current_week.json
  |
  v
generate_weekly_review(profile, aggregate)
  |
  v
low-pressure weekly review reply
```

Missing daily files are treated as days with no records. They are not created during aggregation.

## Week Key Design

The week key uses ISO week format:

```text
YYYY-Www
```

Example:

```text
2026-06-20 -> 2026-W25
```

`get_week_date_range("2026-W25")` returns the seven dates from Monday through Sunday.

## Current Limits

v0.2 step 2 does not implement:

- Scheduler-driven rollover.
- Proactive recall.
- Real Weixin/OpenClaw dispatcher binding.
- Cross-timezone user profiles.
- Sophisticated complete-day scoring.
- Long-term trend detection across many weeks.
- Database storage.

`complete_logging_days` currently uses a simple approximation: meal count >= 2.

`recovery_success_count` is currently derived from lapse-recovery signals in daily files. Future versions can make this more nuanced by checking follow-up behavior on the next day.

## Future Scheduler And Recall Expansion

Daily rollover and weekly aggregation are prerequisites for future scheduler/recall work:

- A scheduler can call `ensure_daily_state(...)` in the morning.
- A weekly job can call `aggregate_week_from_daily(...)` before review.
- Recall can inspect recent daily files without mixing dates.
- Recovery prompts can use yesterday's status without carrying over yesterday's logs.

Those features are intentionally not enabled in this step.
