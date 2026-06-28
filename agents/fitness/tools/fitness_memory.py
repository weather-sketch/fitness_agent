"""Memory candidate extraction and review helpers for Fitness Agent."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import fitness_state


VALID_ACTIONS = {"approve": "approved", "reject": "rejected", "archive": "archived"}


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _candidate_id(candidate_type: str, key: str) -> str:
    stamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
    safe_key = "".join(char if char.isalnum() else "-" for char in key.lower()).strip("-")
    return f"mem-{candidate_type}-{safe_key[:32]}-{stamp}"


def _contains_any(text: str, terms: list[str]) -> bool:
    return any(term in text for term in terms)


def _ensure_preference_containers(profile: dict[str, Any]) -> dict[str, Any]:
    preferences = profile.setdefault("preferences", {})
    preferences.setdefault("food_avoidance", [])
    preferences.setdefault("food_preference", [])
    preferences.setdefault("workout_preference", [])
    preferences.setdefault("feedback_style_rules", {})
    preferences.setdefault("routine", [])
    preferences.setdefault("safety_boundaries", [])
    return preferences


def _upsert_by_key(items: list[dict[str, Any]], item: dict[str, Any]) -> dict[str, Any]:
    for existing in items:
        if existing.get("key") == item.get("key"):
            for key, value in item.items():
                current = existing.get(key)
                if key not in existing or current is None or current == "" or current == []:
                    existing[key] = value
            return {"item": existing, "created": False}
    items.append(item)
    return {"item": item, "created": True}


def _active_preference_from_candidate(candidate: dict[str, Any]) -> dict[str, Any] | None:
    candidate_type = candidate.get("type")
    key = candidate.get("key")
    candidate_id = candidate.get("candidate_id")
    if candidate_type == "safety_boundary" and key == "avoid_yogurt_pre_workout":
        return {
            "category": "food_avoidance",
            "key": "avoid_yogurt_pre_workout",
            "avoid_items": ["酸奶", "yogurt"],
            "context": "pre_workout",
            "reason": "user_discomfort",
            "source_candidate_id": candidate_id,
        }
    if candidate_type == "feedback_style" and key == "concise_summary":
        return {
            "category": "feedback_style",
            "key": "concise_summary",
            "style": "concise_summary",
            "source_candidate_id": candidate_id,
        }
    if candidate_type == "routine" and key == "glutes_day_preworkout_carbs":
        return {
            "category": "routine",
            "key": "glutes_day_preworkout_carbs",
            "context": "glutes_day",
            "action": "prepare_light_carbs_preworkout",
            "source_candidate_id": candidate_id,
        }
    return None


def _new_candidate(
    candidate_type: str,
    key: str,
    value: str,
    confidence: str,
    source: str,
    sensitivity: str,
    evidence: str,
) -> dict[str, Any]:
    now = _now()
    return {
        "candidate_id": _candidate_id(candidate_type, key),
        "type": candidate_type,
        "key": key,
        "value": value,
        "confidence": confidence,
        "status": "candidate",
        "evidence_count": 1,
        "evidence_examples": [evidence],
        "source": source,
        "sensitivity": sensitivity,
        "created_at": now,
        "updated_at": now,
        "review_note": "",
        "applied_to": None,
    }


def extract_memory_candidates(user_text: str, context: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Extract durable Fitness memory candidates with conservative rules."""
    text = user_text.strip()
    lowered = text.lower()
    candidates: list[dict[str, Any]] = []

    if not text:
        return candidates

    meal_only_terms = ["今天吃了", "今天喝了", "中午吃了", "晚上吃了", "早上吃了", "喝了一杯", "吃了一碗"]
    durable_terms = ["以后", "别推荐", "不要", "更喜欢", "提醒我", "最近", "容易", "每次"]
    if _contains_any(text, meal_only_terms) and not _contains_any(text, durable_terms):
        return candidates

    if _contains_any(text, ["练前"]) and _contains_any(text, ["酸奶"]) and _contains_any(text, ["别推荐", "不要推荐", "不要", "胃不舒服", "不舒服"]):
        candidate_type = "safety_boundary" if _contains_any(text, ["胃不舒服", "不舒服", "疼", "痛"]) else "food_preference"
        candidates.append(_new_candidate(
            candidate_type,
            "avoid_yogurt_pre_workout",
            "练前不要推荐酸奶；用户提到会胃不舒服。",
            "high",
            "correction",
            "medium",
            text,
        ))

    if _contains_any(text, ["更喜欢", "希望你", "你给我"]) and _contains_any(text, ["一句话", "简短", "不要长篇", "别长篇"]):
        candidates.append(_new_candidate(
            "feedback_style",
            "concise_summary",
            "用户偏好一句话总结和简短反馈，避免长篇分析。",
            "high",
            "user_text",
            "low",
            text,
        ))

    if _contains_any(text, ["练臀"]) and _contains_any(text, ["提醒我", "提前"]) and _contains_any(text, ["碳水", "轻碳水", "吃一点"]):
        candidates.append(_new_candidate(
            "routine",
            "glutes_day_preworkout_carbs",
            "练臀日前提醒用户提前安排一点轻碳水。",
            "high",
            "user_text",
            "low",
            text,
        ))

    if _contains_any(text, ["睡眠差", "睡不好", "没睡好"]) and _contains_any(text, ["甜食", "想吃甜", "嘴馋"]):
        candidates.append(_new_candidate(
            "behavior_pattern",
            "poor_sleep_sweet_craving",
            "用户最近睡眠差时更容易想吃甜食。",
            "medium",
            "user_text",
            "medium",
            text,
        ))

    if _contains_any(text, ["吃爆", "吃多", "超标"]) and _contains_any(text, ["不想记", "容易不想记", "不想记录"]):
        candidates.append(_new_candidate(
            "behavior_pattern",
            "lapse_after_overeating",
            "用户吃多或超标后容易不想继续记录。",
            "medium",
            "user_text",
            "medium",
            text,
        ))

    return candidates


def list_memory_candidates(user_id: str = "default", status: str | None = None) -> list[dict[str, Any]]:
    memory = fitness_state.get_memory_candidates(user_id=user_id)
    candidates = list(memory.get("candidates", []))
    if status is None:
        return candidates
    return [candidate for candidate in candidates if candidate.get("status") == status]


def get_active_preferences(user_id: str = "default") -> dict[str, Any]:
    """Return active preferences stored in the user's profile."""
    profile = fitness_state.get_profile(user_id=user_id)
    preferences = _ensure_preference_containers(profile)
    return {
        "food_avoidance": list(preferences.get("food_avoidance", [])),
        "food_preference": list(preferences.get("food_preference", [])),
        "workout_preference": list(preferences.get("workout_preference", [])),
        "feedback_style": dict(preferences.get("feedback_style_rules", {})),
        "routine": list(preferences.get("routine", [])),
        "safety_boundaries": list(preferences.get("safety_boundaries", [])),
    }


def apply_approved_memory_candidate(user_id: str, candidate: dict[str, Any]) -> dict[str, Any]:
    """Convert an approved candidate into active profile preferences."""
    if candidate.get("status") != "approved":
        return {"applied": False, "reason": "candidate_not_approved", "candidate_id": candidate.get("candidate_id")}
    active = _active_preference_from_candidate(candidate)
    if active is None:
        return {"applied": False, "reason": "unsupported_candidate_type", "candidate_id": candidate.get("candidate_id")}

    profile = fitness_state.get_profile(user_id=user_id)
    preferences = _ensure_preference_containers(profile)
    category = active["category"]
    created = False
    applied_to = f"profile.preferences.{category}"

    if category == "food_avoidance":
        result = _upsert_by_key(preferences["food_avoidance"], active)
        safety = {
            "key": active["key"],
            "context": active["context"],
            "reason": active["reason"],
            "source_candidate_id": active["source_candidate_id"],
        }
        _upsert_by_key(preferences["safety_boundaries"], safety)
        created = bool(result["created"])
    elif category == "feedback_style":
        existing = preferences["feedback_style_rules"].get(active["key"])
        preferences["feedback_style_rules"][active["key"]] = active
        created = existing is None
    elif category == "routine":
        result = _upsert_by_key(preferences["routine"], active)
        created = bool(result["created"])
    else:
        return {"applied": False, "reason": "unsupported_active_category", "candidate_id": candidate.get("candidate_id")}

    fitness_state.save_json(fitness_state.get_user_data_dir(user_id) / "profile.json", profile)
    return {
        "applied": True,
        "created": created,
        "active_preference": active,
        "applied_to": applied_to,
        "candidate_id": candidate.get("candidate_id"),
    }


def _save_candidates(user_id: str, candidates: list[dict[str, Any]]) -> dict[str, Any]:
    memory = fitness_state.get_memory_candidates(user_id=user_id)
    memory["candidates"] = candidates
    fitness_state.save_json(fitness_state.get_user_data_dir(user_id) / "memory_candidates.json", memory)
    return memory


def review_memory_candidate(
    user_id: str,
    candidate_id: str,
    action: str,
    review_note: str | None = None,
) -> dict[str, Any]:
    if action not in VALID_ACTIONS:
        raise fitness_state.FitnessStateError(f"Unsupported memory review action: {action}")

    candidates = list_memory_candidates(user_id=user_id)
    for candidate in candidates:
        if candidate.get("candidate_id") == candidate_id:
            apply_result: dict[str, Any] | None = None
            candidate["status"] = VALID_ACTIONS[action]
            candidate["updated_at"] = _now()
            if review_note is not None:
                candidate["review_note"] = review_note
            if action == "approve":
                apply_result = apply_approved_memory_candidate(user_id, candidate)
                if apply_result.get("applied"):
                    candidate["applied_to"] = apply_result["applied_to"]
            _save_candidates(user_id, candidates)
            if apply_result is not None:
                candidate["active_preference_application"] = apply_result
            return candidate
    raise fitness_state.FitnessStateError(f"Memory candidate not found: {candidate_id}")


def approve_memory_candidate(user_id: str, candidate_id: str, review_note: str | None = None) -> dict[str, Any]:
    return review_memory_candidate(user_id, candidate_id, "approve", review_note)


def reject_memory_candidate(user_id: str, candidate_id: str, review_note: str | None = None) -> dict[str, Any]:
    return review_memory_candidate(user_id, candidate_id, "reject", review_note)


def archive_memory_candidate(user_id: str, candidate_id: str, review_note: str | None = None) -> dict[str, Any]:
    return review_memory_candidate(user_id, candidate_id, "archive", review_note)
