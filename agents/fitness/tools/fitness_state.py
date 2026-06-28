"""Local JSON state helpers for the Fitness Agent."""

from __future__ import annotations

import copy
import json
import shutil
import tempfile
from datetime import date as date_cls, datetime, timedelta
from pathlib import Path
from typing import Any

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover - Python < 3.9 fallback
    ZoneInfo = None  # type: ignore[assignment]


AGENT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = AGENT_ROOT / "data"
BACKUPS_DIR_NAME = "data_backups"
USERS_DIR_NAME = "users"
DEFAULT_USER_ID = "default"


DEFAULTS: dict[str, dict[str, Any]] = {
    "profile.json": {
        "version": 1,
        "user_id": "local_user",
        "goal": {"primary": "unknown", "strategy": "unknown", "notes": ""},
        "metrics": {
            "height_cm": None,
            "weight_kg": None,
            "daily_calorie_target": None,
            "protein_target_g": None
        },
        "preferences": {
            "food_likes": [],
            "food_dislikes": [],
            "training_focus": [],
            "feedback_style": "gentle",
            "food_avoidance": [],
            "food_preference": [],
            "workout_preference": [],
            "feedback_style_rules": {},
            "routine": [],
            "safety_boundaries": []
        },
        "updated_at": None
    },
    "daily_state.json": {
        "version": 1,
        "date": None,
        "day_type": "unknown",
        "plan_status": "not_generated",
        "training": {
            "planned": False,
            "type": "unknown",
            "time": "unknown",
            "intensity": "unknown",
            "actual_intensity": "unknown",
            "status": "unknown",
            "post_workout_meal_status": "unknown"
        },
        "nutrition": {
            "calorie_budget": None,
            "calories_consumed": 0,
            "calories_remaining": None,
            "calorie_budget_status": "unknown",
            "protein_target_g": None,
            "protein_consumed_g": 0,
            "protein_gap_g": None,
            "last_meal_time": None,
            "meals": []
        },
        "recovery": {
            "sleep_quality": "unknown",
            "fatigue": "unknown",
            "pain_or_soreness": [],
            "recovery_need": "unknown"
        },
        "emotion": {"mood": "unknown", "lapse_risk": "unknown"},
        "special_context": [],
        "workouts": []
    },
    "cycle_state.json": {
        "version": 1,
        "week_start_date": None,
        "workout_completed_count": 0,
        "meal_logging_days": 0,
        "over_budget_days": 0,
        "recovery_success_count": 0,
        "special_context_count": {},
        "possible_patterns": [],
        "weekly_wins": [],
        "next_week_focus": None
    },
    "recall_state.json": {
        "version": 1,
        "enabled": False,
        "last_active_at": None,
        "last_recall_at": None,
        "last_recall_type": None,
        "recall_count_recent": 0,
        "cooldown_until": None,
        "preferred_recall_style": "gentle",
        "last_known_context": None,
        "last_risk_signal": None,
        "last_completed_action": None,
        "user_response_to_last_recall": None
    },
    "memory_candidates.json": {"version": 1, "candidates": []}
}


class FitnessStateError(RuntimeError):
    """Raised when local Fitness state cannot be read or written."""


def _safe_user_id(user_id: str | None = DEFAULT_USER_ID) -> str:
    raw = str(user_id or DEFAULT_USER_ID).strip() or DEFAULT_USER_ID
    safe = "".join(char if char.isalnum() or char in {"-", "_", ".", "@"} else "_" for char in raw)
    return safe or DEFAULT_USER_ID


def _safe_label(label: str | None = None) -> str:
    if not label:
        return ""
    raw = str(label).strip()
    safe = "".join(char if char.isalnum() or char in {"-", "_", "."} else "-" for char in raw)
    return safe.strip("-._")


def _backup_root() -> Path:
    """Return the backup root paired with the active DATA_DIR."""
    if DATA_DIR.name == "data":
        return DATA_DIR.parent / BACKUPS_DIR_NAME
    return DATA_DIR / BACKUPS_DIR_NAME


def _user_backup_root(user_id: str = DEFAULT_USER_ID) -> Path:
    return _backup_root() / USERS_DIR_NAME / _safe_user_id(user_id)


def _normalize_date(value: str | date_cls | None = None) -> str:
    if value is None:
        return get_today_str()
    if isinstance(value, date_cls):
        return value.isoformat()
    return str(value)


def _normalize_week(value: str | None = None) -> str:
    return str(value or "current_week")


def get_today_str(timezone: str | None = None) -> str:
    """Return today's date as YYYY-MM-DD using local time or a standard-library timezone."""
    if timezone and ZoneInfo is not None:
        try:
            return datetime.now(ZoneInfo(timezone)).date().isoformat()
        except Exception:
            pass
    return date_cls.today().isoformat()


def get_week_key(date_str: str | None = None) -> str:
    """Return an ISO week key like 2026-W25 for a YYYY-MM-DD date."""
    target = date_cls.fromisoformat(date_str or get_today_str())
    iso_year, iso_week, _ = target.isocalendar()
    return f"{iso_year}-W{iso_week:02d}"


def get_week_date_range(week_key: str) -> list[str]:
    """Return the seven YYYY-MM-DD dates for an ISO week key."""
    try:
        year_part, week_part = week_key.split("-W", 1)
        start = date_cls.fromisocalendar(int(year_part), int(week_part), 1)
    except (TypeError, ValueError) as exc:
        raise FitnessStateError(f"Invalid week_key {week_key!r}; expected YYYY-Www") from exc
    return [(start + timedelta(days=offset)).isoformat() for offset in range(7)]


def get_user_data_dir(user_id: str = DEFAULT_USER_ID) -> Path:
    """Return the scoped data directory for one Fitness user."""
    return DATA_DIR / USERS_DIR_NAME / _safe_user_id(user_id)


def _user_state_path(kind: str, user_id: str = DEFAULT_USER_ID, date: str | date_cls | None = None, week: str | None = None) -> Path:
    user_dir = get_user_data_dir(user_id)
    if kind == "profile.json":
        return user_dir / "profile.json"
    if kind == "recall_state.json":
        return user_dir / "recall_state.json"
    if kind == "memory_candidates.json":
        return user_dir / "memory_candidates.json"
    if kind == "daily_state.json":
        return user_dir / "daily" / f"{_normalize_date(date)}.json"
    if kind == "cycle_state.json":
        return user_dir / "cycle" / f"{_normalize_week(week)}.json"
    return user_dir / kind


def _resolve_path(path: str | Path) -> Path:
    resolved = Path(path)
    if resolved.is_absolute():
        return resolved
    if resolved.exists():
        return resolved
    return DATA_DIR / resolved


def _default_for(path: str | Path) -> dict[str, Any]:
    name = Path(path).name
    if Path(path).parent.name == "daily":
        name = "daily_state.json"
    elif Path(path).parent.name == "cycle":
        name = "cycle_state.json"
    return copy.deepcopy(DEFAULTS.get(name, {"version": 1}))


def _nested_update(base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _nested_update(base[key], value)
        else:
            base[key] = value
    return base


def _ranked_max(current: Any, incoming: Any, ranking: dict[str, int]) -> Any:
    current_rank = ranking.get(str(current), 0)
    incoming_rank = ranking.get(str(incoming), 0)
    return incoming if incoming_rank > current_rank else current


def _merge_memory_candidate(existing: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    confidence_rank = {"low": 1, "medium": 2, "high": 3}
    sensitivity_rank = {"low": 1, "medium": 2, "high": 3}
    existing["evidence_count"] = int(existing.get("evidence_count") or 0) + 1
    examples = existing.setdefault("evidence_examples", [])
    for example in incoming.get("evidence_examples", []) or []:
        if example not in examples:
            examples.append(example)
    existing["confidence"] = _ranked_max(existing.get("confidence"), incoming.get("confidence"), confidence_rank)
    existing["sensitivity"] = _ranked_max(existing.get("sensitivity"), incoming.get("sensitivity"), sensitivity_rank)
    existing["updated_at"] = incoming.get("updated_at") or datetime.now().isoformat(timespec="seconds")
    return existing


def _load_state_file(target: Path, default_name: str, user_id: str = DEFAULT_USER_ID, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    if not target.exists():
        legacy = DATA_DIR / default_name
        if _safe_user_id(user_id) == DEFAULT_USER_ID and legacy.exists():
            data = load_json(legacy)
        else:
            data = copy.deepcopy(DEFAULTS[default_name])
        if metadata:
            _nested_update(data, metadata)
        save_json(target, data)
        return data
    return load_json(target)


def _normalize_recall_state(state: dict[str, Any]) -> dict[str, Any]:
    """Backfill v0.2 recall fields while preserving existing user choices."""
    changed = False
    for key, value in copy.deepcopy(DEFAULTS["recall_state.json"]).items():
        if key not in state:
            state[key] = value
            changed = True
    if "recall_cooldown_until" in state and not state.get("cooldown_until"):
        state["cooldown_until"] = state.get("recall_cooldown_until")
        changed = True
    if "recall_cooldown_until" in state:
        state.pop("recall_cooldown_until", None)
        changed = True
    if isinstance(state.get("last_known_context"), list):
        contexts = state.get("last_known_context") or []
        state["last_known_context"] = contexts[-1] if contexts else None
        changed = True
    if state.get("last_risk_signal") == "unknown":
        state["last_risk_signal"] = None
        changed = True
    if state.get("user_response_to_last_recall") == "unknown":
        state["user_response_to_last_recall"] = None
        changed = True
    state["__normalized_changed"] = changed
    return state


def _normalize_profile_state(state: dict[str, Any]) -> dict[str, Any]:
    """Backfill active preference containers without overwriting existing preferences."""
    changed = False
    preferences = state.setdefault("preferences", {})
    for key, value in copy.deepcopy(DEFAULTS["profile.json"]["preferences"]).items():
        if key not in preferences:
            preferences[key] = value
            changed = True
    state["__normalized_changed"] = changed
    return state


def load_json(path: str | Path) -> dict[str, Any]:
    """Load a JSON state file, initializing a default if it does not exist."""
    target = _resolve_path(path)
    if not target.exists():
        data = _default_for(target)
        save_json(target, data)
        return data
    try:
        with target.open("r", encoding="utf-8") as handle:
            loaded = json.load(handle)
    except json.JSONDecodeError as exc:
        raise FitnessStateError(f"Invalid JSON in {target}: {exc}") from exc
    except OSError as exc:
        raise FitnessStateError(f"Could not read {target}: {exc}") from exc
    if not isinstance(loaded, dict):
        raise FitnessStateError(f"Expected JSON object in {target}")
    return loaded


def _validate_existing_json_before_write(target: Path) -> None:
    """Refuse to overwrite corrupted JSON without leaving a local copy."""
    if not target.exists():
        return
    try:
        with target.open("r", encoding="utf-8") as handle:
            loaded = json.load(handle)
    except json.JSONDecodeError as exc:
        corrupted_backup = target.with_name(
            f"{target.name}.corrupted-{datetime.now().strftime('%Y%m%dT%H%M%S')}.bak"
        )
        shutil.copy2(target, corrupted_backup)
        raise FitnessStateError(
            f"Refusing to overwrite corrupted JSON in {target}; copied original to {corrupted_backup}: {exc}"
        ) from exc
    except OSError as exc:
        raise FitnessStateError(f"Could not inspect existing JSON before writing {target}: {exc}") from exc
    if not isinstance(loaded, dict):
        raise FitnessStateError(f"Refusing to overwrite non-object JSON in {target}")


def save_json(path: str | Path, data: dict[str, Any]) -> None:
    """Save a JSON state file with a clear error on failure."""
    target = _resolve_path(path)
    if not isinstance(data, dict):
        raise FitnessStateError(f"Data for {target} must be a JSON object")
    tmp_name: str | None = None
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        _validate_existing_json_before_write(target)
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=target.parent,
            delete=False,
            prefix=f".{target.name}.",
            suffix=".tmp"
        ) as handle:
            tmp_name = handle.name
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        Path(tmp_name).replace(target)
    except TypeError as exc:
        if tmp_name:
            Path(tmp_name).unlink(missing_ok=True)
        raise FitnessStateError(f"Data for {target} is not JSON serializable: {exc}") from exc
    except OSError as exc:
        if tmp_name:
            Path(tmp_name).unlink(missing_ok=True)
        raise FitnessStateError(f"Could not write {target}: {exc}") from exc


def _count_files(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for item in path.rglob("*") if item.is_file())


def _new_backup_id(label: str | None = None) -> str:
    base = datetime.now().strftime("%Y-%m-%dT%H%M%S")
    safe_label = _safe_label(label)
    return f"{base}-{safe_label}" if safe_label else base


def _copy_tree_contents(source: Path, target: Path) -> int:
    copied = 0
    for item in source.rglob("*"):
        relative = item.relative_to(source)
        destination = target / relative
        if item.is_dir():
            destination.mkdir(parents=True, exist_ok=True)
        elif item.is_file():
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, destination)
            copied += 1
    return copied


def _validate_json_tree(root: Path) -> list[str]:
    errors: list[str] = []
    if not root.exists():
        errors.append(f"Missing directory: {root}")
        return errors
    for path in sorted(root.rglob("*.json")):
        try:
            with path.open("r", encoding="utf-8") as handle:
                loaded = json.load(handle)
        except json.JSONDecodeError as exc:
            errors.append(f"Invalid JSON in {path}: {exc}")
            continue
        except OSError as exc:
            errors.append(f"Could not read {path}: {exc}")
            continue
        if not isinstance(loaded, dict):
            errors.append(f"Expected JSON object in {path}")
    return errors


def create_user_backup(user_id: str = DEFAULT_USER_ID, label: str | None = None) -> dict[str, Any]:
    """Create a full backup for one user's Fitness state directory."""
    user_safe = _safe_user_id(user_id)
    user_dir = get_user_data_dir(user_safe)
    if not user_dir.exists():
        raise FitnessStateError(f"Cannot back up missing user state directory: {user_dir}")

    root = _user_backup_root(user_safe)
    root.mkdir(parents=True, exist_ok=True)
    backup_id = _new_backup_id(label)
    target = root / backup_id
    suffix = 1
    while target.exists():
        target = root / f"{backup_id}-{suffix:02d}"
        suffix += 1
    target.mkdir(parents=True)
    file_count = _copy_tree_contents(user_dir, target)
    metadata = {
        "backup_id": target.name,
        "user_id": user_safe,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "label": label,
        "source": str(user_dir),
        "path": str(target),
        "file_count": file_count,
    }
    save_json(target / "backup_manifest.json", metadata)
    return metadata


def list_user_backups(user_id: str = DEFAULT_USER_ID) -> list[dict[str, Any]]:
    """List one user's backups with newest first."""
    root = _user_backup_root(user_id)
    if not root.exists():
        return []
    backups: list[dict[str, Any]] = []
    for directory in root.iterdir():
        if not directory.is_dir():
            continue
        manifest_path = directory / "backup_manifest.json"
        manifest: dict[str, Any]
        if manifest_path.exists():
            try:
                manifest = load_json(manifest_path)
            except FitnessStateError:
                manifest = {}
        else:
            manifest = {}
        backups.append({
            "backup_id": directory.name,
            "user_id": _safe_user_id(user_id),
            "path": str(directory),
            "created_at": manifest.get("created_at"),
            "label": manifest.get("label"),
            "file_count": _count_files(directory),
        })
    backups.sort(key=lambda item: (item.get("backup_id") or ""), reverse=True)
    return backups


def _select_backup(user_id: str, backup_id: str | None) -> Path:
    backups = list_user_backups(user_id)
    if not backups:
        raise FitnessStateError(f"No backups found for user {_safe_user_id(user_id)!r}")
    selected_id = backup_id or backups[0]["backup_id"]
    root = _user_backup_root(user_id)
    selected = root / str(selected_id)
    if not selected.exists() or not selected.is_dir():
        raise FitnessStateError(f"Backup not found for user {_safe_user_id(user_id)!r}: {selected_id}")
    return selected


def restore_user_backup(
    user_id: str = DEFAULT_USER_ID,
    backup_id: str | None = None,
    dry_run: bool = True,
) -> dict[str, Any]:
    """Restore one user's backup. Dry-run is the default and makes no changes."""
    user_safe = _safe_user_id(user_id)
    source = _select_backup(user_safe, backup_id)
    validation_errors = _validate_json_tree(source)
    if validation_errors:
        return {
            "ok": False,
            "dry_run": dry_run,
            "user_id": user_safe,
            "backup_id": source.name,
            "errors": validation_errors,
        }

    user_dir = get_user_data_dir(user_safe)
    files_to_restore = [
        str(path.relative_to(source))
        for path in sorted(source.rglob("*"))
        if path.is_file() and path.name != "backup_manifest.json"
    ]
    if dry_run:
        return {
            "ok": True,
            "dry_run": True,
            "user_id": user_safe,
            "backup_id": source.name,
            "target": str(user_dir),
            "files_to_restore": files_to_restore,
            "file_count": len(files_to_restore),
        }

    pre_restore = create_user_backup(user_safe, label=f"pre-restore-{source.name}") if user_dir.exists() else None
    restored_count = 0
    for relative in files_to_restore:
        src = source / relative
        dst = user_dir / relative
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        restored_count += 1
    return {
        "ok": True,
        "dry_run": False,
        "user_id": user_safe,
        "backup_id": source.name,
        "target": str(user_dir),
        "restored_count": restored_count,
        "pre_restore_backup": pre_restore,
    }


def validate_user_state(user_id: str = DEFAULT_USER_ID) -> dict[str, Any]:
    """Validate one user's Fitness state files without modifying them."""
    user_safe = _safe_user_id(user_id)
    user_dir = get_user_data_dir(user_safe)
    errors: list[str] = []
    warnings: list[str] = []
    checked_files = 0

    if not user_dir.exists():
        return {
            "valid": False,
            "user_id": user_safe,
            "path": str(user_dir),
            "checked_files": 0,
            "errors": [f"Missing user state directory: {user_dir}"],
            "warnings": warnings,
        }

    required_files = ["profile.json", "recall_state.json", "memory_candidates.json"]
    for name in required_files:
        path = user_dir / name
        if not path.exists():
            errors.append(f"Missing required file: {path}")

    for dirname in ["daily", "cycle"]:
        directory = user_dir / dirname
        if not directory.exists():
            errors.append(f"Missing required directory: {directory}")
        elif not directory.is_dir():
            errors.append(f"Expected directory: {directory}")

    for path in sorted(user_dir.rglob("*.json")):
        checked_files += 1
        try:
            with path.open("r", encoding="utf-8") as handle:
                loaded = json.load(handle)
        except json.JSONDecodeError as exc:
            errors.append(f"Invalid JSON in {path}: {exc}")
            continue
        except OSError as exc:
            errors.append(f"Could not read {path}: {exc}")
            continue
        if not isinstance(loaded, dict):
            errors.append(f"Expected JSON object in {path}")

    daily_files = list((user_dir / "daily").glob("*.json")) if (user_dir / "daily").is_dir() else []
    cycle_files = list((user_dir / "cycle").glob("*.json")) if (user_dir / "cycle").is_dir() else []
    if not daily_files:
        warnings.append("No daily state files found.")
    if not cycle_files:
        warnings.append("No cycle state files found.")

    return {
        "valid": not errors,
        "user_id": user_safe,
        "path": str(user_dir),
        "checked_files": checked_files,
        "errors": errors,
        "warnings": warnings,
    }


def get_profile(user_id: str = DEFAULT_USER_ID) -> dict[str, Any]:
    user_safe = _safe_user_id(user_id)
    target = _user_state_path("profile.json", user_safe)
    state = _normalize_profile_state(_load_state_file(
        _user_state_path("profile.json", user_safe),
        "profile.json",
        user_safe,
        {"user_id": user_safe},
    ))
    changed = bool(state.pop("__normalized_changed", False))
    if state.get("user_id") != user_safe:
        state["user_id"] = user_safe
        changed = True
    if changed:
        save_json(_user_state_path("profile.json", user_safe), state)
    return state


def get_daily_state(user_id: str = DEFAULT_USER_ID, date: str | date_cls | None = None) -> dict[str, Any]:
    normalized_date = _normalize_date(date)
    target = _user_state_path("daily_state.json", user_id, date=normalized_date)
    return _load_state_file(target, "daily_state.json", user_id, {"date": normalized_date})


def ensure_daily_state(user_id: str = DEFAULT_USER_ID, date: str | date_cls | None = None) -> dict[str, Any]:
    """Ensure a daily state file exists without overwriting an existing one."""
    return get_daily_state(user_id=user_id, date=date)


def ensure_user_state(user_id: str = DEFAULT_USER_ID, date: str | date_cls | None = None) -> dict[str, Any]:
    """Ensure the standard per-user Fitness state files exist."""
    normalized_date = _normalize_date(date)
    profile = get_profile(user_id=user_id)
    recall_state = get_recall_state(user_id=user_id)
    memory_candidates = get_memory_candidates(user_id=user_id)
    daily_state = ensure_daily_state(user_id=user_id, date=normalized_date)
    cycle_state = get_cycle_state(user_id=user_id, week="current_week")
    return {
        "user_id": _safe_user_id(user_id),
        "profile": profile,
        "recall_state": recall_state,
        "memory_candidates": memory_candidates,
        "daily_state": daily_state,
        "cycle_state": cycle_state,
    }


def rollover_daily_state(
    user_id: str = DEFAULT_USER_ID,
    from_date: str | date_cls | None = None,
    to_date: str | date_cls | None = None,
) -> dict[str, Any]:
    """Create the target day's state without carrying over meals or workouts."""
    normalized_to = _normalize_date(to_date)
    target = _user_state_path("daily_state.json", user_id, date=normalized_to)
    if target.exists():
        return load_json(target)

    normalized_from = _normalize_date(from_date) if from_date is not None else (
        date_cls.fromisoformat(normalized_to) - timedelta(days=1)
    ).isoformat()
    previous_path = _user_state_path("daily_state.json", user_id, date=normalized_from)
    previous = load_json(previous_path) if previous_path.exists() else None

    state = copy.deepcopy(DEFAULTS["daily_state.json"])
    state["date"] = normalized_to
    profile = get_profile(user_id=user_id)
    metrics = profile.get("metrics", {})
    calorie_budget = metrics.get("daily_calorie_target")
    protein_target = metrics.get("protein_target_g")
    if calorie_budget is not None or protein_target is not None:
        nutrition = state.setdefault("nutrition", {})
        nutrition["calorie_budget"] = calorie_budget
        nutrition["calories_remaining"] = calorie_budget
        nutrition["protein_target_g"] = protein_target
        nutrition["protein_gap_g"] = protein_target
    if previous:
        state["previous_day_status"] = {
            "date": previous.get("date") or normalized_from,
            "day_type": previous.get("day_type"),
            "calorie_budget_status": previous.get("nutrition", {}).get("calorie_budget_status"),
            "training_status": previous.get("training", {}).get("status"),
            "lapse_risk": previous.get("emotion", {}).get("lapse_risk"),
        }
    save_json(target, state)
    return state


def update_daily_state(patch: dict[str, Any], user_id: str = DEFAULT_USER_ID, date: str | date_cls | None = None) -> dict[str, Any]:
    normalized_date = _normalize_date(date)
    state = get_daily_state(user_id=user_id, date=normalized_date)
    _nested_update(state, patch)
    save_json(_user_state_path("daily_state.json", user_id, date=normalized_date), state)
    return state


def get_cycle_state(user_id: str = DEFAULT_USER_ID, week: str | None = None) -> dict[str, Any]:
    normalized_week = _normalize_week(week)
    target = _user_state_path("cycle_state.json", user_id, week=normalized_week)
    return _load_state_file(target, "cycle_state.json", user_id)


def update_cycle_state(patch: dict[str, Any], user_id: str = DEFAULT_USER_ID, week: str | None = None) -> dict[str, Any]:
    normalized_week = _normalize_week(week)
    state = get_cycle_state(user_id=user_id, week=normalized_week)
    _nested_update(state, patch)
    save_json(_user_state_path("cycle_state.json", user_id, week=normalized_week), state)
    return state


def aggregate_week_from_daily(user_id: str = DEFAULT_USER_ID, week_key: str | None = None) -> dict[str, Any]:
    """Aggregate one user's week from daily state files and persist cycle snapshots."""
    ensure_user_state(user_id=user_id)
    selected_week = week_key or get_week_key()
    week_dates = get_week_date_range(selected_week)
    workout_completed_count = 0
    meal_logging_days = 0
    complete_logging_days = 0
    over_budget_days = 0
    lapse_recovery_count = 0
    recovery_success_count = 0
    special_context_count: dict[str, int] = {}
    training_types: dict[str, int] = {}
    days_with_logs: list[str] = []

    for day in week_dates:
        path = _user_state_path("daily_state.json", user_id, date=day)
        if not path.exists():
            continue
        daily = load_json(path)
        nutrition = daily.get("nutrition", {})
        meals = nutrition.get("meals", []) or []
        workouts = daily.get("workouts", []) or []
        training = daily.get("training", {})
        special_context = daily.get("special_context", []) or []

        if meals or workouts:
            days_with_logs.append(day)
        if meals:
            meal_logging_days += 1
        if len(meals) >= 2:
            complete_logging_days += 1

        remaining = nutrition.get("calories_remaining")
        if nutrition.get("calorie_budget_status") == "over" or (isinstance(remaining, (int, float)) and remaining < 0):
            over_budget_days += 1

        completed_workouts = [item for item in workouts if item.get("status") == "completed"]
        if completed_workouts:
            workout_completed_count += len(completed_workouts)
            for item in completed_workouts:
                training_type = item.get("training_type") or "unknown"
                training_types[training_type] = training_types.get(training_type, 0) + 1
        elif training.get("status") == "completed":
            workout_completed_count += 1
            training_type = training.get("type") or "unknown"
            training_types[training_type] = training_types.get(training_type, 0) + 1

        for context in special_context:
            special_context_count[context] = special_context_count.get(context, 0) + 1
        lapse_signal = "lapse_recovery" in special_context or daily.get("emotion", {}).get("lapse_risk") == "high"
        if lapse_signal:
            lapse_recovery_count += 1
            recovery_success_count += 1

    current_path = _user_state_path("cycle_state.json", user_id, week="current_week")
    existing_current = load_json(current_path) if current_path.exists() else {}
    aggregate = {
        "version": 1,
        "week_key": selected_week,
        "week_start_date": week_dates[0],
        "week_end_date": week_dates[-1],
        "workout_completed_count": workout_completed_count,
        "meal_logging_days": meal_logging_days,
        "complete_logging_days": complete_logging_days,
        "over_budget_days": over_budget_days,
        "special_context_count": special_context_count,
        "lapse_recovery_count": lapse_recovery_count,
        "recovery_success_count": recovery_success_count,
        "training_types": training_types,
        "days_with_logs": days_with_logs,
        "possible_patterns": [],
        "weekly_wins": [],
        "next_week_focus": existing_current.get("next_week_focus"),
        "source": "daily_aggregation",
    }
    save_json(_user_state_path("cycle_state.json", user_id, week=selected_week), aggregate)
    save_json(_user_state_path("cycle_state.json", user_id, week="current_week"), aggregate)
    return aggregate


def get_recall_state(user_id: str = DEFAULT_USER_ID) -> dict[str, Any]:
    target = _user_state_path("recall_state.json", user_id)
    state = _normalize_recall_state(_load_state_file(target, "recall_state.json", user_id))
    changed = bool(state.pop("__normalized_changed", False))
    if changed:
        save_json(target, state)
    return state


def update_recall_state(patch: dict[str, Any], user_id: str = DEFAULT_USER_ID) -> dict[str, Any]:
    state = get_recall_state(user_id=user_id)
    _nested_update(state, patch)
    save_json(_user_state_path("recall_state.json", user_id), state)
    return state


def get_memory_candidates(user_id: str = DEFAULT_USER_ID) -> dict[str, Any]:
    return _load_state_file(_user_state_path("memory_candidates.json", user_id), "memory_candidates.json", user_id)


def append_meal_log(meal_log: dict[str, Any], user_id: str = DEFAULT_USER_ID, date: str | date_cls | None = None) -> dict[str, Any]:
    normalized_date = _normalize_date(date)
    state = get_daily_state(user_id=user_id, date=normalized_date)
    state.setdefault("nutrition", {}).setdefault("meals", []).append(meal_log)
    save_json(_user_state_path("daily_state.json", user_id, date=normalized_date), state)
    return state


def append_workout_log(workout_log: dict[str, Any], user_id: str = DEFAULT_USER_ID, date: str | date_cls | None = None) -> dict[str, Any]:
    normalized_date = _normalize_date(date)
    state = get_daily_state(user_id=user_id, date=normalized_date)
    state.setdefault("workouts", []).append(workout_log)
    save_json(_user_state_path("daily_state.json", user_id, date=normalized_date), state)
    return state


def add_memory_candidate(candidate: dict[str, Any], user_id: str = DEFAULT_USER_ID) -> dict[str, Any]:
    memory = get_memory_candidates(user_id=user_id)
    candidates = memory.setdefault("candidates", [])
    for existing in candidates:
        if (
            existing.get("type") == candidate.get("type")
            and existing.get("key") == candidate.get("key")
            and existing.get("status") in {"candidate", "approved"}
        ):
            merged = _merge_memory_candidate(existing, candidate)
            save_json(_user_state_path("memory_candidates.json", user_id), memory)
            memory.update({
                "candidate": merged,
                "created": False,
                "merged": True,
                "candidate_id": merged.get("candidate_id"),
            })
            return memory

    candidates.append(candidate)
    save_json(_user_state_path("memory_candidates.json", user_id), memory)
    memory.update({
        "candidate": candidate,
        "created": True,
        "merged": False,
        "candidate_id": candidate.get("candidate_id"),
    })
    return memory
