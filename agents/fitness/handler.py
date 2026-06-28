"""Unified local message handler for Fitness Agent v0.1."""

from __future__ import annotations

import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Iterator


AGENT_ROOT = Path(__file__).resolve().parent
TOOLS_DIR = AGENT_ROOT / "tools"

for path in (AGENT_ROOT, TOOLS_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from router import detect_fitness_intent  # noqa: E402
import fitness_logic  # noqa: E402
import fitness_memory  # noqa: E402
import fitness_recall  # noqa: E402
import fitness_state  # noqa: E402


HandlerResult = dict[str, Any]


@contextmanager
def _logic_state_context(user_id: str, date: str | None = None) -> Iterator[None]:
    """Bind imported fitness_logic state helpers to one user for this call."""
    originals: dict[str, Callable[..., Any]] = {
        "get_daily_state": fitness_logic.get_daily_state,
        "get_profile": fitness_logic.get_profile,
        "update_daily_state": fitness_logic.update_daily_state,
        "append_meal_log": fitness_logic.append_meal_log,
        "append_workout_log": fitness_logic.append_workout_log,
    }
    fitness_logic.get_daily_state = lambda: fitness_state.get_daily_state(user_id=user_id, date=date)
    fitness_logic.get_profile = lambda: fitness_state.get_profile(user_id=user_id)
    fitness_logic.update_daily_state = lambda patch: fitness_state.update_daily_state(patch, user_id=user_id, date=date)
    fitness_logic.append_meal_log = lambda meal_log: fitness_state.append_meal_log(meal_log, user_id=user_id, date=date)
    fitness_logic.append_workout_log = lambda workout_log: fitness_state.append_workout_log(workout_log, user_id=user_id, date=date)
    try:
        yield
    finally:
        for name, func in originals.items():
            setattr(fitness_logic, name, func)


def _state_summary(user_id: str = "default", date: str | None = None) -> dict[str, Any]:
    daily = fitness_state.get_daily_state(user_id=user_id, date=date)
    nutrition = daily.get("nutrition", {})
    training = daily.get("training", {})
    recovery = daily.get("recovery", {})
    emotion = daily.get("emotion", {})
    return {
        "date": daily.get("date"),
        "day_type": daily.get("day_type"),
        "plan_status": daily.get("plan_status"),
        "training_type": training.get("type"),
        "training_time": training.get("time"),
        "training_status": training.get("status"),
        "training_intensity": training.get("intensity"),
        "actual_intensity": training.get("actual_intensity"),
        "post_workout_meal_status": training.get("post_workout_meal_status"),
        "recovery_need": recovery.get("recovery_need"),
        "calories_consumed": nutrition.get("calories_consumed"),
        "calories_remaining": nutrition.get("calories_remaining"),
        "calorie_budget_status": nutrition.get("calorie_budget_status"),
        "protein_consumed_g": nutrition.get("protein_consumed_g"),
        "protein_gap_g": nutrition.get("protein_gap_g"),
        "meal_count": len(nutrition.get("meals", [])),
        "lapse_risk": emotion.get("lapse_risk"),
        "special_context": daily.get("special_context", []),
        "workout_count": len(daily.get("workouts", [])),
    }


def _state_changes(before: dict[str, Any], after: dict[str, Any]) -> dict[str, dict[str, Any]]:
    changes: dict[str, dict[str, Any]] = {}
    for key, before_value in before.items():
        after_value = after.get(key)
        if before_value != after_value:
            changes[key] = {"before": before_value, "after": after_value}
    return changes


def _handled_response(
    user_text: str,
    user_id: str,
    channel: str,
    route: dict[str, Any],
    reply: str,
    before: dict[str, Any],
    tool_chain: list[str],
    safety_flags: list[str] | None = None,
    memory_candidates_added: list[str] | None = None,
    memory_candidates_merged: list[str] | None = None,
    active_preferences_applied: list[str] | None = None,
    date: str | None = None,
) -> HandlerResult:
    after = _state_summary(user_id=user_id, date=date)
    return {
        "handled": True,
        "intent": route["intent"],
        "reply": reply.strip(),
        "tool_chain": tool_chain,
        "state_changes": _state_changes(before, after),
        "safety_flags": safety_flags or [],
        "debug": {
            "user_id": user_id,
            "channel": channel,
            "input": user_text,
            "route": route,
            "memory_candidates_added": len(memory_candidates_added or []),
            "memory_candidates_merged": len(memory_candidates_merged or []),
            "memory_candidate_ids_added": memory_candidates_added or [],
            "memory_candidate_ids_merged": memory_candidates_merged or [],
            "active_preferences_applied": active_preferences_applied or [],
        },
    }


def _store_memory_candidates(user_text: str, user_id: str, context: dict[str, Any]) -> dict[str, list[str]]:
    candidates = fitness_memory.extract_memory_candidates(user_text, context=context)
    if not candidates:
        return {"added": [], "merged": []}
    fitness_state.ensure_user_state(user_id=user_id)
    added: list[str] = []
    merged: list[str] = []
    for candidate in candidates:
        saved = fitness_state.add_memory_candidate(candidate, user_id=user_id)
        if saved.get("merged"):
            merged.append(str(saved.get("candidate_id")))
        else:
            added.append(str(saved.get("candidate_id")))
    return {"added": added, "merged": merged}


def _memory_candidate_reply(user_text: str) -> str:
    candidates = fitness_memory.extract_memory_candidates(user_text)
    if any(candidate.get("key") == "avoid_yogurt_pre_workout" for candidate in candidates):
        return "好的，之后练前我会避免推荐酸奶；这类偏好会先作为候选记忆保留。"
    if any(candidate.get("type") == "feedback_style" for candidate in candidates):
        return "好的，我会把这个反馈风格先作为候选记忆保留，之后尽量给你更简短的总结。"
    if any(candidate.get("type") == "routine" for candidate in candidates):
        return "好的，这个训练日提醒偏好会先作为候选记忆保留。"
    return "好的，这类长期偏好会先作为候选记忆保留。"


def _detect_recall_command(user_text: str) -> str | None:
    text = user_text.strip().lower()
    opt_out_terms = ["别提醒我", "不要提醒我", "不用提醒我", "不要打扰我", "别打扰我"]
    if any(term in text for term in opt_out_terms):
        return "recall_opt_out"

    suggestion_terms = ["怎么提醒我", "会怎么提醒我", "你会怎么提醒我", "如果开启召回", "召回建议"]
    if any(term in text for term in suggestion_terms):
        return "recall_suggestion"

    opt_in_terms = ["以后可以提醒我", "可以提醒我", "提醒我记录", "叫我记录", "每周提醒我复盘", "提醒我复盘"]
    fitness_context_terms = ["记录", "训练", "饮食", "吃", "练", "复盘", "周报", "fitness", "健身"]
    if any(term in text for term in opt_in_terms):
        if "以后可以提醒我" in text or any(term in text for term in fitness_context_terms):
            return "recall_opt_in"
    return None


def handle_fitness_message(
    user_text: str,
    user_id: str = "default",
    channel: str = "local",
    date: str | None = None,
) -> HandlerResult:
    """Handle one Fitness-domain message and return an IM-ready response."""
    recall_command = _detect_recall_command(user_text)
    if recall_command == "recall_opt_in":
        before_enabled = bool(fitness_state.get_recall_state(user_id=user_id).get("enabled"))
        after_state = fitness_recall.set_recall_opt_in(user_id=user_id, enabled=True)
        return {
            "handled": True,
            "intent": "recall_opt_in",
            "reply": "可以，我会只在你明确开启的情况下生成低压力提醒建议；当前不会主动推送。",
            "tool_chain": ["set_recall_opt_in"],
            "state_changes": {"recall.enabled": {"before": before_enabled, "after": bool(after_state.get("enabled"))}},
            "safety_flags": [],
            "debug": {"user_id": user_id, "channel": channel, "input": user_text},
        }
    if recall_command == "recall_opt_out":
        before_enabled = bool(fitness_state.get_recall_state(user_id=user_id).get("enabled"))
        after_state = fitness_recall.set_recall_opt_in(user_id=user_id, enabled=False)
        return {
            "handled": True,
            "intent": "recall_opt_out",
            "reply": "好的，我会关闭 Fitness 召回建议，不会主动打扰你。",
            "tool_chain": ["set_recall_opt_in"],
            "state_changes": {"recall.enabled": {"before": before_enabled, "after": bool(after_state.get("enabled"))}},
            "safety_flags": [],
            "debug": {"user_id": user_id, "channel": channel, "input": user_text},
        }
    if recall_command == "recall_suggestion":
        suggestion = fitness_recall.detect_recall_opportunity(user_id=user_id)
        reply = suggestion.get("message") or "现在没有特别需要提醒的 Fitness 场景；如果开启召回，我也会优先给低压力、可一句话回复的入口。"
        return {
            "handled": True,
            "intent": "recall_suggestion",
            "reply": reply,
            "tool_chain": ["detect_recall_opportunity", "generate_recall_message"],
            "state_changes": {},
            "safety_flags": [],
            "debug": {
                "user_id": user_id,
                "channel": channel,
                "input": user_text,
                "recall_type": suggestion.get("recall_type"),
                "should_send": suggestion.get("should_send"),
            },
        }

    try:
        route = detect_fitness_intent(user_text)
    except Exception as exc:
        return {
            "handled": False,
            "intent": "unknown",
            "reply": "",
            "tool_chain": [],
            "state_changes": {},
            "safety_flags": [],
            "debug": {
                "user_id": user_id,
                "channel": channel,
                "input": user_text,
                "error": f"{type(exc).__name__}: {exc}",
            },
        }

    if route["intent"] == "unknown":
        memory_candidate_result = _store_memory_candidates(
            user_text,
            user_id,
            {"intent": "unknown", "channel": channel},
        )
        if memory_candidate_result["added"] or memory_candidate_result["merged"]:
            return {
                "handled": True,
                "intent": "memory_candidate_update",
                "reply": _memory_candidate_reply(user_text),
                "tool_chain": ["extract_memory_candidates", "add_memory_candidate"],
                "state_changes": {},
                "safety_flags": [],
                "debug": {
                    "user_id": user_id,
                    "channel": channel,
                    "input": user_text,
                    "route": {**route, "intent": "memory_candidate_update"},
                    "memory_candidates_added": len(memory_candidate_result["added"]),
                    "memory_candidates_merged": len(memory_candidate_result["merged"]),
                    "memory_candidate_ids_added": memory_candidate_result["added"],
                    "memory_candidate_ids_merged": memory_candidate_result["merged"],
                },
            }
        return {
            "handled": False,
            "intent": "unknown",
            "reply": "",
            "tool_chain": [],
            "state_changes": {},
            "safety_flags": [],
            "debug": {
                "user_id": user_id,
                "channel": channel,
                "input": user_text,
                "route": route,
                "memory_candidates_added": 0,
                "memory_candidates_merged": 0,
                "memory_candidate_ids_added": [],
                "memory_candidate_ids_merged": [],
            },
        }

    try:
        before = _state_summary(user_id=user_id, date=date)
        profile = fitness_state.get_profile(user_id=user_id)
        safety_flags: list[str] = []
        tool_chain = list(route["suggested_tool_chain"])
        intent = route["intent"]
        memory_candidates_added: list[str] = []
        memory_candidates_merged: list[str] = []
        active_preferences_applied: list[str] = []

        with _logic_state_context(user_id, date=date):
            if intent == "daily_plan":
                state = fitness_logic.apply_user_context(user_text)
                result = fitness_logic.generate_daily_plan(profile, state)
                fitness_state.update_daily_state({"plan_status": "generated"}, user_id=user_id, date=date)
                reply = result["reply"]
                safety_flags.extend(result.get("safety_notes", []))
                active_preferences_applied.extend(result.get("active_preferences_applied", []))
            elif intent == "log_meal":
                result = fitness_logic.log_meal(user_text)
                reply = result["reply"]
                if result.get("intent") == "lapse_recovery":
                    safety_flags.append("lapse_signal_detected")
            elif intent == "log_workout":
                result = fitness_logic.log_workout(user_text)
                reply = result["reply"]
            elif intent == "pre_workout_meal":
                fitness_logic.apply_user_context(user_text)
                result = fitness_logic.recommend_pre_workout_meal(profile, fitness_state.get_daily_state(user_id=user_id, date=date))
                reply = result["reply"]
                active_preferences_applied.extend(result.get("active_preferences_applied", []))
            elif intent == "post_workout_meal":
                workout = fitness_logic.log_workout(user_text)
                result = fitness_logic.recommend_post_workout_meal(profile, fitness_state.get_daily_state(user_id=user_id, date=date))
                reply = f"{workout['reply']}\n{result['reply']}"
                active_preferences_applied.extend(result.get("active_preferences_applied", []))
            elif intent == "lapse_recovery":
                result = fitness_logic.generate_lapse_recovery_plan(
                    profile,
                    fitness_state.get_daily_state(user_id=user_id, date=date),
                    user_text,
                )
                reply = result["reply"]
                safety_flags.extend(result.get("safety_notes", []))
            elif intent == "weekly_review":
                cycle = fitness_state.aggregate_week_from_daily(user_id=user_id)
                result = fitness_logic.generate_weekly_review(profile, cycle)
                reply = result["reply"]
            else:
                return {
                    "handled": False,
                    "intent": "unknown",
                    "reply": "",
                    "tool_chain": [],
                    "state_changes": {},
                    "safety_flags": [],
                    "debug": {
                        "user_id": user_id,
                        "channel": channel,
                        "input": user_text,
                        "route": route,
                        "error": f"Unsupported routed intent: {intent}",
                    },
                }
        memory_candidate_result = _store_memory_candidates(
            user_text,
            user_id,
            {"intent": intent, "channel": channel},
        )
        memory_candidates_added = memory_candidate_result["added"]
        memory_candidates_merged = memory_candidate_result["merged"]
    except Exception as exc:
        return {
            "handled": False,
            "intent": "unknown",
            "reply": "",
            "tool_chain": [],
            "state_changes": {},
            "safety_flags": [],
            "debug": {
                "user_id": user_id,
                "channel": channel,
                "input": user_text,
                "route": route,
                "error": f"{type(exc).__name__}: {exc}",
            },
        }

    return _handled_response(
        user_text,
        user_id,
        channel,
        route,
        reply,
        before,
        tool_chain,
        safety_flags,
        memory_candidates_added,
        memory_candidates_merged,
        sorted(set(active_preferences_applied)),
        date,
    )
