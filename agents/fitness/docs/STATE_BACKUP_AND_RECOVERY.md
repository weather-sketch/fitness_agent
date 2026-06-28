# Fitness Agent State Backup And Recovery

## Why This Exists

Fitness Agent is designed for long-running personal use. Once state spans daily files, weekly aggregation, recall state, and memory candidates, accidental JSON corruption or a bad manual edit can break future routing and review flows. v0.2 Step 3 adds a small state safety layer: validation, full user backups, dry-run restore, and conservative writes.

This is not a product feature. It does not add scheduler behavior, proactive recall, external APIs, image recognition, a database, or real OpenClaw dispatcher binding.

## Backup Directory Structure

Real state lives under:

```text
agents/fitness/data/users/<user_id>/
  profile.json
  recall_state.json
  memory_candidates.json
  daily/
    YYYY-MM-DD.json
  cycle/
    current_week.json
    <week_key>.json
```

Backups live separately under:

```text
agents/fitness/data_backups/
  users/
    <user_id>/
      2026-06-20T213000-before-routing/
        backup_manifest.json
        profile.json
        recall_state.json
        memory_candidates.json
        daily/
          2026-06-20.json
        cycle/
          current_week.json
          2026-W25.json
```

The backup code preserves the user's directory structure and does not back up `demo_data` unless the active `DATA_DIR` is explicitly redirected to a demo/test path.

## User State Initialization

`ensure_user_state(user_id="default", date=None)` creates the standard user state set before validation or backup:

```text
profile.json
recall_state.json
memory_candidates.json
daily/<date>.json
cycle/current_week.json
```

`aggregate_week_from_daily(...)` also calls this initializer so a new user does not fail validation just because `memory_candidates.json` has not been touched yet. `validate_user_state(...)` remains strict and still reports missing required files.

## Admin CLI

```bash
python3 agents/fitness/tools/fitness_admin_cli.py validate --user default
python3 agents/fitness/tools/fitness_admin_cli.py backup --user default --label before-routing
python3 agents/fitness/tools/fitness_admin_cli.py list-backups --user default
python3 agents/fitness/tools/fitness_admin_cli.py restore --user default --backup-id <id> --dry-run
python3 agents/fitness/tools/fitness_admin_cli.py restore --user default --backup-id <id> --apply
```

Restore is dry-run by default. `--apply` is required before any files are written.

## Restore Design

`restore_user_backup(...)` validates the selected backup before writing. If the backup contains invalid JSON, restore returns a clear error and does not overwrite current state.

Before an apply restore, the system creates a pre-restore backup of the current user directory. This gives a recovery point if the selected restore was the wrong choice.

Restore copies files from the backup over the active user directory. It does not delete unrelated current files that are absent from the backup.

## JSON Corruption Strategy

`save_json(...)` still uses atomic temp-file replacement. Before replacing an existing JSON file, it now parses the existing file. If the existing target is corrupted or is not a JSON object, it refuses to overwrite silently.

For corrupted JSON, the original file is copied next to itself as:

```text
<name>.json.corrupted-YYYYMMDDTHHMMSS.bak
```

Then a `FitnessStateError` is raised. This keeps the broken file available for manual inspection and avoids hiding data loss behind a successful write.

Full user backups are not created on every normal state write. That would make meal logging and workout logging too noisy and would grow storage quickly. Full backups are manual/admin operations.

## Current Limits

- Backup and restore are local filesystem operations only.
- There is no encryption or remote sync.
- There is no retention policy yet.
- There is no scheduler-triggered backup yet.
- Restore is user-scoped, not a multi-user migration system.
- The admin CLI is for local maintenance, not a normal user-facing chat command.

## Suggested Future Backup Timing

If Fitness Agent is connected to long-term real WeChat use, consider automatic backups only at low-frequency safety points:

- Before first real channel dispatcher binding.
- Before schema changes or migration scripts.
- Before enabling opt-in scheduler/recall.
- Once daily or weekly, if state is changing frequently.
- Before manual restore or repair operations.

Do not create a full backup for every ordinary message.
