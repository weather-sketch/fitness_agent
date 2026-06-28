# Active Memory Application

## Candidate Memory vs Active Memory

Memory candidates are review items. They live in:

```text
agents/fitness/data/users/<user_id>/memory_candidates.json
```

They are useful for audit and review, but they should not affect recommendations until approved.

Active preferences are behavior-changing rules stored in the user's profile:

```text
agents/fitness/data/users/<user_id>/profile.json
```

v0.3 uses profile preferences as the active memory store to avoid adding another state file.

## Why Approval Comes First

Fitness guidance can affect repeated advice. A single message should not permanently change behavior unless it is clearly durable and reviewed. v0.3 keeps this sequence:

```text
user text
  -> memory candidate
  -> evidence dedupe/merge
  -> admin approve
  -> active preference
  -> recommendation behavior change
```

Rejected or archived candidates do not write active preferences.

## Active Preference Schema

Food avoidance example:

```json
{
  "category": "food_avoidance",
  "key": "avoid_yogurt_pre_workout",
  "avoid_items": ["酸奶", "yogurt"],
  "context": "pre_workout",
  "reason": "user_discomfort",
  "source_candidate_id": "..."
}
```

The profile keeps active preferences under:

```json
{
  "preferences": {
    "food_avoidance": [],
    "food_preference": [],
    "workout_preference": [],
    "feedback_style_rules": {},
    "routine": [],
    "safety_boundaries": []
  }
}
```

Sensitive details are intentionally reduced. For example, active memory stores `reason=user_discomfort` rather than a long free-text medical note.

## avoid_yogurt_pre_workout Example

User:

```text
以后练前别推荐酸奶，我会胃不舒服。
```

Candidate:

```text
type=safety_boundary
key=avoid_yogurt_pre_workout
status=candidate
```

After approval:

```bash
python3 agents/fitness/tools/fitness_memory_cli.py approve --user default --candidate-id <id>
python3 agents/fitness/tools/fitness_memory_cli.py active --user default
```

Active preferences include `avoid_yogurt_pre_workout`. Later, when the user asks:

```text
今天晚上练臀，怎么吃？
```

The daily plan avoids yogurt and suggests options such as banana, rice ball, toast, egg, tofu, soy milk, fish/shrimp, and staple carbs.

## Recommendation Integration

The following recommendation functions read active preferences from `profile["preferences"]`:

- `generate_daily_plan(...)`
- `recommend_pre_workout_meal(...)`
- `recommend_post_workout_meal(...)`

They use candidate option lists and filter avoided foods instead of doing broad string replacement. Handler debug may include:

```json
{
  "active_preferences_applied": ["avoid_yogurt_pre_workout"]
}
```

User-visible replies do not expose debug JSON or raw memory state.

## Demo

```bash
python3 agents/fitness/run_memory_demo.py
```

The demo uses isolated `agents/fitness/demo_data/` and shows the full flow from candidate creation to approved active preference to changed recommendation.

## Current Limits

- Only a small set of candidate types is converted to active preferences.
- `feedback_style` and `routine` are stored, but v0.3 does not globally rewrite every reply or schedule reminders.
- No scheduler, proactive push, OpenClaw channel binding, external API, image recognition, or database is added.
- Active preference matching is exact and rule-based.

## Future Extensions

- Apply approved feedback style more consistently across reply generation.
- Let approved routines inform opt-in recall suggestions.
- Add richer food preference categories after more real examples.
- Add explicit admin undo or deactivate operations for active preferences.
