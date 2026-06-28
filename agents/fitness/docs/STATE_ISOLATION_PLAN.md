# Fitness Agent v0.2 State Isolation Plan

## Why User And Channel Isolation Matters

Fitness Agent v0.1 proved that the handler can be called from the main Agent and can write local state. That is enough for a prototype, but not enough for long-term personal use.

The next minimum requirement is to prevent all messages from sharing one global `daily_state.json`. Fitness state should be scoped by user and by date:

- Different users should not share meals, workouts, recovery state, or profile values.
- The same user's daily state should roll forward by local date.
- Channel should be preserved as metadata/debug context, but should not decide the storage path.
- Legacy root state files should remain available and untouched.

## New State Directory Structure

The v0.2 state layer prefers this structure:

```text
agents/fitness/data/users/
  default/
    profile.json
    recall_state.json
    memory_candidates.json
    daily/
      2026-06-20.json
    cycle/
      current_week.json
```

For a future Weixin user:

```text
agents/fitness/data/users/
  weixin_user_123/
    profile.json
    recall_state.json
    memory_candidates.json
    daily/
      2026-06-20.json
    cycle/
      current_week.json
```

## Daily State By Date

`get_daily_state(user_id="default", date=None)` resolves `date=None` to the local current date and stores the file at:

```text
agents/fitness/data/users/<user_id>/daily/YYYY-MM-DD.json
```

This keeps yesterday's meals and workouts from leaking into today's plan while still allowing later weekly review logic to inspect multiple dates.

## Compatibility With Old Root JSON Files

The old v0.1 files remain in place:

```text
agents/fitness/data/profile.json
agents/fitness/data/daily_state.json
agents/fitness/data/cycle_state.json
agents/fitness/data/recall_state.json
agents/fitness/data/memory_candidates.json
```

They are not deleted or migrated.

New state APIs prefer `data/users/<user_id>/...`. For the default user only, if a user-scoped file does not exist yet, the state layer may initialize it from the matching old root file. After that, writes go to the user-scoped path.

`ensure_user_state(user_id="default", date=None)` is the standard initializer for a new user. It creates `profile.json`, `recall_state.json`, `memory_candidates.json`, `daily/<date>.json`, and `cycle/current_week.json` without deleting legacy root JSON files.

## Channel Handling

`channel` is passed through `handle_fitness_message(...)` and `routing_adapter.route_fitness_message(...)` for debug and future audit context.

It does not affect the storage path. The storage path is based on `user_id`, not channel. This avoids splitting the same person into multiple states just because they send messages from different surfaces.

## What Is Still Not Implemented

v0.2 step 1 does not implement:

- Real OpenClaw channel dispatcher binding.
- Scheduler or proactive recall.
- Multi-device account linking.
- User profile merge.
- Cross-channel identity resolution.
- Database storage.
- Concurrent write locking beyond atomic JSON replacement.

## Future Weixin User Mapping

When the real Weixin channel is connected, the adapter should map the inbound message object like this:

```python
{
    "text": inbound_text,
    "user_id": weixin_contact_id_or_openid,
    "channel": "weixin",
}
```

Then call:

```python
handle_fitness_message(text, user_id=user_id, channel=channel)
```

If no stable Weixin user id is available, use `"default"` as a fallback and avoid enabling multi-user assumptions.
