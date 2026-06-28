"""Rule-based intent router for Fitness Agent v0.1."""

from __future__ import annotations

from typing import Any


IntentResult = dict[str, Any]


PRIORITY = [
    "lapse_recovery",
    "post_workout_meal",
    "pre_workout_meal",
    "log_workout",
    "log_meal",
    "daily_plan",
    "weekly_review",
]


RULES: dict[str, dict[str, Any]] = {
    "lapse_recovery": {
        "terms": ["吃爆了", "吃爆", "不想记了", "不想记", "今天废了", "算了", "超了", "自助餐", "喝酒了"],
        "tool_chain": ["detect_lapse_risk", "generate_lapse_recovery_plan", "update_daily_state"],
    },
    "post_workout_meal": {
        "terms": ["练完了", "刚练完", "练后吃什么", "练后", "强度很大", "力竭"],
        "tool_chain": ["log_workout", "recommend_post_workout_meal"],
    },
    "pre_workout_meal": {
        "terms": ["练前吃什么", "训练前吃什么", "有点饿还要练", "练前怎么吃", "训练前怎么吃"],
        "tool_chain": ["apply_user_context", "recommend_pre_workout_meal"],
    },
    "log_workout": {
        "terms": ["练了", "训练完", "完成训练", "健身完", "打卡", "做了有氧", "做了训练"],
        "tool_chain": ["log_workout", "update_daily_state"],
    },
    "log_meal": {
        "terms": ["吃了", "喝了", "中午", "晚餐", "早餐", "加餐", "牛肉面", "火锅", "麦当劳", "甜品"],
        "tool_chain": ["estimate_calorie_range", "append_meal_log", "update_daily_state"],
    },
    "daily_plan": {
        "terms": ["练臀", "练腿", "练肩", "练背", "有氧", "爬坡", "训练", "健身", "今晚练"],
        "tool_chain": ["apply_user_context", "classify_day_type", "generate_daily_plan", "update_daily_state"],
    },
    "weekly_review": {
        "terms": ["这周怎么样", "周报", "复盘", "最近怎么样"],
        "tool_chain": ["aggregate_week_from_daily", "generate_weekly_review"],
    },
}


def _contains_any(text: str, terms: list[str]) -> list[str]:
    return [term for term in terms if term in text]


def detect_fitness_intent(user_text: str) -> IntentResult:
    """Detect a v0.1 Fitness intent with deterministic rules."""
    text = user_text.strip().lower()
    matches: dict[str, list[str]] = {}

    for intent, rule in RULES.items():
        hit_terms = _contains_any(text, rule["terms"])
        if hit_terms:
            matches[intent] = hit_terms

    if not matches:
        return {
            "intent": "unknown",
            "confidence": "low",
            "reason": "No v0.1 fitness routing rule matched.",
            "suggested_tool_chain": [],
        }

    selected = next(intent for intent in PRIORITY if intent in matches)
    hit_count = len(matches[selected])
    confidence = "high" if hit_count >= 2 or selected in {"lapse_recovery", "post_workout_meal"} else "medium"
    if len(matches) > 1:
        reason = f"Matched {selected} by priority; hits={matches[selected]}; all_matches={matches}."
    else:
        reason = f"Matched {selected}; hits={matches[selected]}."

    return {
        "intent": selected,
        "confidence": confidence,
        "reason": reason,
        "suggested_tool_chain": RULES[selected]["tool_chain"],
    }
