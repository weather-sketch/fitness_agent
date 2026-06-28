# Fitness Agent Memory Candidate Review

## Why Not Write Long-Term Memory Directly

Fitness Agent uses short-term state for daily plans, meal logs, workout logs, weekly aggregation, and recovery context. Long-term memory is different: it can affect future advice repeatedly, so it should not be written just because a single message mentioned food, mood, pain, or a one-off event.

v0.2 Step 4 adds a review layer between raw user messages and durable memory. The agent can collect memory candidates, but candidates stay inactive until reviewed. This keeps the system useful without turning every meal log or temporary situation into a permanent preference.

## Candidate Lifecycle

```text
candidate -> approved
candidate -> rejected
candidate -> archived
```

- `candidate`: extracted by conservative local rules and waiting for review.
- `approved`: accepted as useful long-term information. In v0.3, supported candidate types are also applied to active profile preferences.
- `rejected`: reviewed and considered not stable or not useful.
- `archived`: kept for audit/history but no longer active in the review queue.

## Candidate Schema

Each candidate is stored in:

```text
agents/fitness/data/users/<user_id>/memory_candidates.json
```

Candidate fields:

```json
{
  "candidate_id": "...",
  "type": "food_preference | workout_preference | feedback_style | behavior_pattern | correction | safety_boundary | routine",
  "key": "...",
  "value": "...",
  "confidence": "low | medium | high",
  "status": "candidate | approved | rejected | archived",
  "evidence_count": 1,
  "evidence_examples": [],
  "source": "user_text | weekly_review | correction | repeated_behavior",
  "sensitivity": "low | medium | high",
  "created_at": "...",
  "updated_at": "...",
  "review_note": "",
  "applied_to": null
}
```

## What Can Become A Candidate

Good candidates are durable and useful for future Fitness guidance:

- Explicit food or workout preferences.
- Corrections, especially "do not recommend X in Y context".
- Feedback style preferences, such as wanting shorter replies.
- Repeated behavior patterns, such as overeating leading to logging dropout.
- Safety boundaries, discomfort, pain, or recovery constraints.
- Routine requests, such as reminding the user to prepare carbs before glutes day.

Examples:

```text
以后练前别推荐酸奶，我会胃不舒服。
我更喜欢你给我一句话总结，不要长篇分析。
以后练臀日提醒我提前吃一点碳水。
我最近睡眠差的时候更容易想吃甜食。
我吃爆以后很容易不想记了。
```

## What Should Not Become A Candidate

Do not create a candidate for ordinary single events:

```text
今天吃了一碗牛肉面。
今天喝了一杯抹茶。
```

These belong in daily state or meal logs, not long-term memory.

## Sensitive Information

Signals involving pain, stomach discomfort, sleep, period symptoms, mood, guilt, lapse risk, or body discomfort should be marked at least `medium` sensitivity. High sensitivity information should never be auto-approved.

The current implementation does not auto-approve any candidate. Review is manual/admin-only.

## Review CLI

List candidates:

```bash
python3 agents/fitness/tools/fitness_memory_cli.py list --user default
python3 agents/fitness/tools/fitness_memory_cli.py list --user default --status candidate
```

Review one candidate:

```bash
python3 agents/fitness/tools/fitness_memory_cli.py approve --user default --candidate-id <id>
python3 agents/fitness/tools/fitness_memory_cli.py reject --user default --candidate-id <id> --note "not stable"
python3 agents/fitness/tools/fitness_memory_cli.py archive --user default --candidate-id <id>
```

Show active preferences:

```bash
python3 agents/fitness/tools/fitness_memory_cli.py active --user default
```

The CLI prints readable JSON. It is an admin/development tool, not a chat command for normal users.

## Handler Integration

`handle_fitness_message(...)` extracts candidates conservatively and writes them to `memory_candidates.json`. Candidate IDs are recorded in debug metadata only. User-visible replies use `reply` and do not expose debug JSON, state changes, or raw candidate objects.

When a message is primarily an explicit preference or correction, the handler returns `handled=True` with intent `memory_candidate_update`. Truly unrelated non-fitness messages still return `handled=False` and do not write memory candidates.

Ordinary meal logs, workout logs, and daily plans should not generate candidates unless the message also contains an explicit durable preference, correction, feedback style, or repeated behavior pattern.

## Deduplication And Evidence Merge

When a new candidate has the same `type` and `key` as an existing candidate for the same user, Fitness Agent merges evidence instead of creating a duplicate if the existing candidate is still `candidate` or already `approved`.

Merge behavior:

- `candidate_id` stays the same.
- `evidence_count` increases.
- New `evidence_examples` are appended, but exact duplicate strings are not repeated.
- `updated_at` is refreshed.
- `confidence` keeps the higher value: `high > medium > low`.
- `sensitivity` keeps the higher value: `high > medium > low`.
- `source` and `review_note` are not overwritten.
- `approved` candidates stay approved and are not downgraded.

Candidates with status `rejected` or `archived` are not merged. If the user later repeats a similar preference after rejection/archive, a new candidate may be created for review.

The handler debug metadata distinguishes newly added and merged candidates, but the user-visible reply remains a short natural-language confirmation and does not expose candidate JSON.

## Active Preference Application

Approval is the boundary between candidate memory and behavior-changing memory. When an admin approves a supported candidate, Fitness Agent writes a compact active preference into the user's `profile.json`.

Example:

```text
type=safety_boundary
key=avoid_yogurt_pre_workout
status=approved
```

Active preference:

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

Later daily-plan and workout-meal recommendations read active preferences and avoid recommending yogurt. Rejected or archived candidates do not write active preferences. Repeated approval is idempotent and does not duplicate active preference entries.

## Current Limits

- Extraction is rule-based and intentionally narrow.
- Only supported approved candidates are applied to active preferences.
- No embeddings, external memory service, database, or scheduler is used.
- Candidate review is local/admin-only.
- Deduplication is exact and local to `type + key`; there is no semantic or embedding-based deduplication.

## Future Active Memory

- Apply approved `feedback_style` rules more consistently across replies.
- Let approved `routine` rules inform opt-in recall suggestions.
- Add deactivate/undo operations for active preferences.
- Sensitive candidates should continue to require review before affecting advice.
