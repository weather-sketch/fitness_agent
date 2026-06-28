"""Core local logic for Fitness Agent v0.1."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from fitness_state import (
    append_meal_log,
    append_workout_log,
    get_daily_state,
    get_profile,
    update_daily_state,
)


MealEstimate = dict[str, Any]


def _now_id(prefix: str) -> str:
    return f"{prefix}-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"


def _contains(text: str, terms: list[str]) -> bool:
    return any(term in text for term in terms)


def _number(value: Any, default: float = 0) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    return default


def _training_state(daily_state: dict[str, Any]) -> dict[str, Any]:
    return daily_state.get("training", {})


def _nutrition_state(daily_state: dict[str, Any]) -> dict[str, Any]:
    return daily_state.get("nutrition", {})


def _recovery_state(daily_state: dict[str, Any]) -> dict[str, Any]:
    return daily_state.get("recovery", {})


def _active_food_avoidance(profile: dict[str, Any], context: str | None = None) -> list[dict[str, Any]]:
    preferences = profile.get("preferences", {}) or {}
    avoidances = preferences.get("food_avoidance", []) or []
    result: list[dict[str, Any]] = []
    for item in avoidances:
        if not isinstance(item, dict):
            continue
        item_context = item.get("context")
        if context is None or item_context in {context, "all", None}:
            result.append(item)
    return result


def _avoid_items(profile: dict[str, Any], context: str | None = None) -> set[str]:
    avoided: set[str] = set()
    for item in _active_food_avoidance(profile, context=context):
        for avoid in item.get("avoid_items", []) or []:
            avoided.add(str(avoid).lower())
    return avoided


def _filter_food_options(options: list[str], avoided: set[str]) -> list[str]:
    return [option for option in options if option.lower() not in avoided]


def _applied_preference_keys(profile: dict[str, Any], context: str | None = None) -> list[str]:
    return [item["key"] for item in _active_food_avoidance(profile, context=context) if item.get("key")]


def _join_options(options: list[str], connector: str = "、") -> str:
    return connector.join(options)


def classify_day_type(daily_state: dict[str, Any]) -> dict[str, Any]:
    """Classify today and return day_type, tags, and priority list."""
    training = _training_state(daily_state)
    recovery = _recovery_state(daily_state)
    special_context = daily_state.get("special_context", [])

    tags: list[str] = []
    priorities: list[str] = []

    if training.get("time") == "evening":
        tags.append("evening_workout")
    if training.get("type") in {"glutes", "legs"}:
        tags.append("lower_body_day")
    if training.get("type") in {"shoulders", "back"}:
        tags.append("upper_body_day")
    if special_context:
        tags.extend(f"special:{item}" for item in special_context)

    pain_or_soreness = recovery.get("pain_or_soreness") or []
    sleep_quality = recovery.get("sleep_quality", "unknown")
    fatigue = recovery.get("fatigue", "unknown")
    recovery_need = recovery.get("recovery_need", "unknown")

    if sleep_quality == "poor" or fatigue == "high" or pain_or_soreness:
        day_type = "recovery_day"
        priorities = ["recovery", "health_safety", "stable_energy"]
        tags.append("recovery_needed")
    elif any(item in {"travel", "social_meal", "alcohol", "buffet"} for item in special_context):
        day_type = "special_day"
        priorities = ["restore_rhythm", "hydration", "normal_meals"]
    elif training.get("planned") or training.get("status") in {"planned", "completed"}:
        if training.get("type") == "cardio":
            day_type = "cardio_day"
            priorities = ["steady_energy", "protein", "calorie_control"]
        else:
            day_type = "training_day"
            priorities = ["training_performance", "recovery", "calorie_control"]
    else:
        day_type = "rest_day"
        priorities = ["satiety", "protein", "calorie_control"]

    return {"day_type": day_type, "tags": tags, "plan_priority": priorities}


def generate_daily_plan(profile: dict[str, Any], daily_state: dict[str, Any]) -> dict[str, Any]:
    """Generate a concise daily plan for the current state."""
    classified = classify_day_type(daily_state)
    day_type = classified["day_type"]
    training = _training_state(daily_state)
    safety_notes: list[str] = []
    avoided_pre = _avoid_items(profile, context="pre_workout")
    avoided_general = _avoid_items(profile, context=None)
    applied_preferences = _applied_preference_keys(profile, context="pre_workout")
    light_carbs = _filter_food_options(["香蕉", "小饭团", "半片吐司", "豆浆"], avoided_pre)
    protein_options = _filter_food_options(["酸奶", "鸡蛋", "豆腐", "豆浆", "鱼虾"], avoided_general)
    protein_text = _join_options(protein_options or ["鸡蛋", "豆腐", "鱼虾"])
    avoidance_prefix = "我会避开你不舒服的选项，" if applied_preferences else ""

    if day_type == "recovery_day":
        focus = "今天优先恢复和稳定能量，不追求更大的热量缺口。"
        pre = "如果还要训练，建议降级为轻有氧或拉伸；训练前只需要少量易消化碳水。"
        post = "训练后别空着，补一点蛋白质和水分就好。"
        dinner = "晚餐走清淡高蛋白路线，别用不吃饭补偿。"
        minimum = "今天最小行动：正常吃下一餐，早点休息。"
        safety_notes.append("有明显疼痛或持续不适时，不建议高强度训练。")
    elif day_type == "special_day":
        focus = "今天按特殊场景处理，重点是不断记录、不极端补偿。"
        pre = "如果还要训练，练前选香蕉、小饭团或半片吐司这类轻碳水。"
        post = "练后补水、蛋白质和一点主食，避免高油高糖报复性进食。"
        dinner = "晚餐以正常三餐节奏为主，聚餐/饮酒后第二天也不需要断食。"
        minimum = "今天最小行动：只记录一餐也算接上节奏。"
    elif day_type == "training_day" and training.get("type") in {"glutes", "legs"}:
        focus = "今天是下肢/臀腿训练日，白天不要吃太少，给训练留能量。"
        pre = f"{avoidance_prefix}练前 1-2 小时安排轻碳水：{_join_options(light_carbs)}都可以。"
        post = f"练后补蛋白质 + 适量碳水，比如{protein_text}配一点主食。"
        dinner = "晚餐别太油，保留恢复需要，不用靠饿着控制热量。"
        minimum = "今天最小行动：练前吃一点轻碳水，练后补蛋白。"
    elif day_type == "training_day" and training.get("type") in {"shoulders", "back"}:
        focus = "今天是上肢中等强度训练日，饮食重点是蛋白质和稳定能量。"
        pre = "如果离训练超过 1 小时，可以吃小饭团/香蕉；不饿就不用硬加餐。"
        post = "练后以蛋白质为主，碳水按饥饿程度和剩余热量少量补。"
        dinner = "晚餐高蛋白、正常蔬菜，主食半份到一份都可以。"
        minimum = "今天最小行动：保证一顿高蛋白正餐。"
    elif day_type == "cardio_day":
        focus = "今天是有氧日，重点是别把运动当作惩罚，保持稳定摄入。"
        cardio_options = _filter_food_options(["半根香蕉", "一小杯酸奶"], avoided_pre)
        pre = f"轻有氧前不一定要加餐；如果饿，可以吃{_join_options(cardio_options or ['半根香蕉'], '或')}。"
        post = "有氧后补水，正餐正常吃蛋白质和蔬菜。"
        dinner = "晚餐以饱腹和清淡为主，不需要额外训练碳水。"
        minimum = "今天最小行动：完成轻运动后正常吃饭。"
    else:
        focus = "今天按休息日处理，重点是蛋白质、蔬菜、饱腹感。"
        pre = "休息日没有练前餐需求，想吃零食时先选可控份量。"
        post = "休息日没有练后餐需求，但蛋白质照样要够。"
        dinner = "晚餐正常吃，高蛋白 + 蔬菜 + 适量主食。"
        minimum = "今天最小行动：记录一顿正餐，别让零食替代正餐。"

    reply = "\n".join([
        f"今日类型：{day_type}",
        focus,
        f"练前：{pre}",
        f"练后：{post}",
        f"晚餐：{dinner}",
        minimum
    ])

    return {
        "day_type": day_type,
        "tags": classified["tags"],
        "plan_priority": classified["plan_priority"],
        "food_focus": focus,
        "pre_workout": pre,
        "post_workout": post,
        "dinner_strategy": dinner,
        "minimum_action": minimum,
        "safety_notes": safety_notes,
        "active_preferences_applied": applied_preferences,
        "reply": reply
    }


def estimate_calorie_range(meal_text: str) -> MealEstimate:
    """Return a rough calorie and protein estimate by simple rules."""
    text = meal_text.lower()
    rules: list[tuple[list[str], tuple[int, int, int, str, list[str]]]] = [
        (["牛肉面", "牛肉粉", "拉面"], (600, 850, 25, "medium", ["面量", "油量", "牛肉份量"])),
        (["抹茶椰子水", "椰子水抹茶", "抹茶"], (120, 280, 2, "medium", ["是否加糖", "容量", "奶/椰浆用量"])),
        (["酸奶", "yogurt"], (90, 220, 8, "medium", ["容量", "是否加糖", "是否希腊酸奶"])),
        (["饭团", "饭糰"], (180, 320, 6, "medium", ["大小", "内馅", "酱料"])),
        (["火锅"], (900, 1600, 45, "low", ["锅底", "蘸料", "肉类和主食份量"])),
        (["自助餐", "buffet"], (1200, 2200, 45, "low", ["品类很多", "甜品和酒水", "主食份量"])),
        (["麦当劳", "mcdonald", "汉堡", "薯条"], (650, 1200, 25, "medium", ["套餐大小", "是否含薯条/甜饮"])),
        (["甜品", "蛋糕", "奶茶", "冰淇淋"], (300, 700, 5, "medium", ["大小", "奶油/糖量"])),
        (["鸡尾酒", "啤酒", "喝酒", "酒"], (150, 600, 0, "low", ["杯数", "酒精种类", "是否配下酒菜"]))
    ]
    for terms, values in rules:
        if _contains(text, terms):
            low, high, protein, confidence, factors = values
            return {
                "estimated_calories_min": low,
                "estimated_calories_max": high,
                "estimated_protein": protein,
                "confidence": confidence,
                "uncertain_factors": factors
            }
    return {
        "estimated_calories_min": 350,
        "estimated_calories_max": 750,
        "estimated_protein": 15,
        "confidence": "low",
        "uncertain_factors": ["食物类型", "份量", "烹饪油量"]
    }


def _infer_meal_type(meal_text: str, meal_type: str | None) -> str:
    if meal_type:
        return meal_type
    if _contains(meal_text, ["早饭", "早餐"]):
        return "breakfast"
    if _contains(meal_text, ["中午", "午饭", "午餐"]):
        return "lunch"
    if _contains(meal_text, ["晚上", "晚饭", "晚餐"]):
        return "dinner"
    if _contains(meal_text, ["喝", "饮料", "咖啡", "酒", "奶茶"]):
        return "drink"
    return "snack"


def _budget_status(remaining: float | None) -> str:
    if remaining is None:
        return "unknown"
    if remaining < 0:
        return "over"
    if remaining <= 200:
        return "near_limit"
    return "on_track"


def _ensure_demo_budget(state: dict[str, Any]) -> dict[str, Any]:
    nutrition = _nutrition_state(state)
    if nutrition.get("calorie_budget") is not None and nutrition.get("protein_target_g") is not None:
        return state
    profile = get_profile()
    metrics = profile.get("metrics", {})
    calorie_budget = nutrition.get("calorie_budget") or metrics.get("daily_calorie_target") or 1600
    protein_target = nutrition.get("protein_target_g") or metrics.get("protein_target_g") or 80
    patch = {
        "nutrition": {
            "calorie_budget": calorie_budget,
            "calories_remaining": calorie_budget - _number(nutrition.get("calories_consumed")),
            "protein_target_g": protein_target,
            "protein_gap_g": max(0, protein_target - _number(nutrition.get("protein_consumed_g")))
        }
    }
    return update_daily_state(patch)


def log_meal(meal_text: str, meal_type: str | None = None) -> dict[str, Any]:
    """Estimate and log a meal into local daily_state."""
    state = _ensure_demo_budget(get_daily_state())
    lapse = detect_lapse_risk(meal_text, state)
    if lapse["recovery_needed"]:
        update_daily_state({"emotion": {"lapse_risk": lapse["lapse_risk"], "mood": "guilty"}})

    estimate = estimate_calorie_range(meal_text)
    kcal_mid = round((estimate["estimated_calories_min"] + estimate["estimated_calories_max"]) / 2)
    protein = estimate["estimated_protein"]
    meal_log = {
        "meal_id": _now_id("meal"),
        "meal_type": _infer_meal_type(meal_text, meal_type),
        "time": None,
        "description": meal_text,
        **estimate,
        "logged_calories": kcal_mid,
        "source": "user_text"
    }
    state = append_meal_log(meal_log)
    nutrition = _nutrition_state(state)
    consumed = _number(nutrition.get("calories_consumed")) + kcal_mid
    protein_consumed = _number(nutrition.get("protein_consumed_g")) + protein
    budget = nutrition.get("calorie_budget")
    target_protein = nutrition.get("protein_target_g")
    remaining = None if budget is None else _number(budget) - consumed
    protein_gap = None if target_protein is None else max(0, _number(target_protein) - protein_consumed)

    state = update_daily_state({
        "nutrition": {
            "calories_consumed": consumed,
            "calories_remaining": remaining,
            "calorie_budget_status": _budget_status(remaining),
            "protein_consumed_g": protein_consumed,
            "protein_gap_g": protein_gap
        }
    })
    reply = (
        f"这餐先按 {estimate['estimated_calories_min']}-{estimate['estimated_calories_max']} kcal 记录，"
        f"蛋白质约 {protein}g。"
    )
    if remaining is not None:
        reply += f"\n今天剩余约 {round(remaining)} kcal。"
    if lapse["recovery_needed"]:
        reply += "\n你这句里有超标/不想记的信号，建议切到恢复流程，不用补账，从下一餐接上就行。"

    return {
        "intent": "lapse_recovery" if lapse["recovery_needed"] else "log_meal",
        "meal_log": meal_log,
        "daily_state": state,
        "lapse": lapse,
        "reply": reply
    }


def _parse_workout(workout_text: str) -> dict[str, Any]:
    text = workout_text.lower()
    training_type = "unknown"
    if _contains(text, ["练臀", "臀"]):
        training_type = "glutes"
    elif _contains(text, ["练腿", "腿"]):
        training_type = "legs"
    elif _contains(text, ["练肩", "肩"]):
        training_type = "shoulders"
    elif _contains(text, ["练背", "背"]):
        training_type = "back"
    elif _contains(text, ["有氧", "爬坡", "慢走", "跑步"]):
        training_type = "cardio"

    intensity = "unknown"
    if _contains(text, ["强度很大", "高强度", "力竭", "很累"]):
        intensity = "high"
    elif _contains(text, ["轻", "慢走", "低强度"]):
        intensity = "low"
    elif training_type in {"glutes", "legs"}:
        intensity = "high"
    elif training_type in {"shoulders", "back", "cardio"}:
        intensity = "medium"

    time = "unknown"
    if _contains(text, ["晚上", "今晚"]):
        time = "evening"
    elif _contains(text, ["早上", "上午"]):
        time = "morning"
    elif _contains(text, ["中午"]):
        time = "noon"
    elif _contains(text, ["下午"]):
        time = "afternoon"

    status = "planned"
    if _contains(text, ["练完", "练完了", "完成"]):
        status = "completed"
    if _contains(text, ["取消", "不练", "没练"]):
        status = "skipped"

    pain = []
    if _contains(text, ["膝盖疼", "膝盖痛"]):
        pain.append("膝盖")
    if _contains(text, ["腰疼", "腰痛"]):
        pain.append("腰")
    if _contains(text, ["酸痛", "很酸"]):
        pain.append("酸痛")

    if pain or (status == "completed" and intensity == "high"):
        recovery_need = "high"
    elif intensity in {"medium", "high"}:
        recovery_need = "medium"
    else:
        recovery_need = "unknown"
    return {
        "training_type": training_type,
        "time": time,
        "intensity": intensity,
        "status": status,
        "pain_or_soreness": pain,
        "recovery_need": recovery_need
    }


def log_workout(workout_text: str) -> dict[str, Any]:
    """Record planned or completed workout into local daily_state."""
    existing_state = get_daily_state()
    existing_training = _training_state(existing_state)
    parsed = _parse_workout(workout_text)
    training_type = parsed["training_type"] if parsed["training_type"] != "unknown" else existing_training.get("type", "unknown")
    training_time = parsed["time"] if parsed["time"] != "unknown" else existing_training.get("time", "unknown")
    workout_log = {
        "workout_id": _now_id("workout"),
        "description": workout_text,
        "training_type": training_type,
        "status": parsed["status"],
        "actual_intensity": parsed["intensity"] if parsed["status"] == "completed" else "unknown",
        "estimated_intensity": parsed["intensity"],
        "source": "user_text"
    }
    state = append_workout_log(workout_log)
    existing_recovery = _recovery_state(state).get("pain_or_soreness", [])
    pain = list(dict.fromkeys(existing_recovery + parsed["pain_or_soreness"]))
    patch = {
        "training": {
            "planned": parsed["status"] != "skipped",
            "type": training_type,
            "time": training_time,
            "intensity": parsed["intensity"],
            "actual_intensity": parsed["intensity"] if parsed["status"] == "completed" else "unknown",
            "status": parsed["status"],
            "post_workout_meal_status": "suggested" if parsed["status"] == "completed" else "unknown"
        },
        "recovery": {
            "pain_or_soreness": pain,
            "recovery_need": parsed["recovery_need"]
        }
    }
    classified = classify_day_type({**state, **patch})
    patch["day_type"] = classified["day_type"]
    state = update_daily_state(patch)
    return {
        "intent": "log_workout",
        "workout_log": workout_log,
        "daily_state": state,
        "reply": "训练状态已更新。"
    }


def recommend_pre_workout_meal(profile: dict[str, Any], daily_state: dict[str, Any]) -> dict[str, Any]:
    training = _training_state(daily_state)
    nutrition = _nutrition_state(daily_state)
    remaining = nutrition.get("calories_remaining")
    low_budget = remaining is not None and _number(remaining) < 250
    lower_body = training.get("type") in {"glutes", "legs"}
    avoided = _avoid_items(profile, context="pre_workout")
    applied_preferences = _applied_preference_keys(profile, context="pre_workout")
    light_carbs = _filter_food_options(["香蕉", "小饭团", "半片吐司"], avoided)
    prefix = "我会避开你不舒服的选项，" if applied_preferences else ""

    if lower_body:
        recommendation = f"{prefix}练前别空腹硬练，选轻碳水：{_join_options(light_carbs)}，三选一。"
    elif training.get("type") == "cardio":
        cardio_options = _filter_food_options(["半根香蕉", "一小杯酸奶"], avoided)
        recommendation = f"{prefix}轻有氧不一定要加餐；如果饿，{_join_options(cardio_options or ['半根香蕉'], '或')}就够。"
    else:
        recommendation = "练前可以轻一点：香蕉、半个饭团或一片吐司，不选高油高糖。"
    if low_budget:
        recommendation += " 今天剩余热量不多，就选半份或小份，重点是有力气训练。"

    return {
        "recommendation": recommendation,
        "foods": ["香蕉", "小饭团", "半片吐司"],
        "avoid": ["高油", "高糖", "太撑"],
        "active_preferences_applied": applied_preferences,
        "reply": recommendation
    }


def recommend_post_workout_meal(profile: dict[str, Any], daily_state: dict[str, Any]) -> dict[str, Any]:
    training = _training_state(daily_state)
    nutrition = _nutrition_state(daily_state)
    intensity = training.get("actual_intensity") or training.get("intensity")
    time = training.get("time")
    protein_gap = nutrition.get("protein_gap_g")
    remaining = nutrition.get("calories_remaining")
    avoided = _avoid_items(profile, context=None)
    applied_preferences = _applied_preference_keys(profile, context="pre_workout")
    protein_options = _filter_food_options(["酸奶", "鸡蛋", "豆腐", "豆浆", "鱼虾"], avoided)
    protein_text = _join_options(protein_options or ["鸡蛋", "豆腐", "豆浆", "鱼虾"])

    if intensity == "high":
        recommendation = "今天强度大，练后建议补蛋白质 + 适量碳水，不建议完全不吃。"
        options = f"可以选{protein_text} + 半份主食或小饭团。"
    else:
        recommendation = "练后至少补一点蛋白质和水分，别用饿着惩罚自己。"
        options = f"可以选{protein_text}这类轻一点的蛋白。"
    if time == "evening":
        options += " 如果离睡觉近，就选易消化、小份，不吃高油高糖。"
    if protein_gap is not None:
        options += f" 你今天蛋白缺口约 {round(_number(protein_gap))}g。"
    if remaining is not None and _number(remaining) < 200:
        options += " 剩余热量少也不用空着，选小份高蛋白更稳。"

    reply = f"{recommendation}\n{options}"
    return {
        "recommendation": recommendation,
        "options": options,
        "active_preferences_applied": applied_preferences,
        "reply": reply
    }


def detect_lapse_risk(user_text: str, daily_state: dict[str, Any] | None = None) -> dict[str, Any]:
    text = user_text.lower()
    risk = _contains(text, ["吃爆", "爆了", "不想记", "今天废了", "算了", "超了", "自助餐吃多", "喝酒"])
    self_blame = _contains(text, ["废了", "失败", "算了", "不想记"])
    return {
        "lapse_risk": "high" if risk else "low",
        "self_blame_signal": self_blame,
        "recovery_needed": risk,
        "response_mode": "recovery_support" if risk else "normal"
    }


def generate_lapse_recovery_plan(
    profile: dict[str, Any],
    daily_state: dict[str, Any],
    user_text: str
) -> dict[str, Any]:
    lapse = detect_lapse_risk(user_text, daily_state)
    update_daily_state({
        "emotion": {"lapse_risk": lapse["lapse_risk"], "mood": "guilty" if lapse["self_blame_signal"] else "unknown"},
        "special_context": list(dict.fromkeys(daily_state.get("special_context", []) + ["lapse_recovery"]))
    })
    reply = (
        "先不用补齐所有记录，也不用用不吃饭来补偿。一次吃多不代表整个节奏坏掉。\n"
        "今天剩下的最小行动：正常喝水，下一餐回到高蛋白 + 蔬菜 + 少量主食，不用额外运动来补偿。\n"
        "明天恢复建议：正常吃三餐，先记录一餐就算接上节奏。"
    )
    return {
        "lapse": lapse,
        "minimum_action": "下一餐正常吃并记录一餐",
        "tomorrow_focus": "正常三餐、补水、蛋白质、轻活动",
        "safety_notes": ["不建议极端节食", "不建议惩罚性运动"],
        "reply": reply
    }


def generate_weekly_review(profile: dict[str, Any], cycle_state: dict[str, Any]) -> dict[str, Any]:
    workouts = cycle_state.get("workout_completed_count", 0)
    logging_days = cycle_state.get("meal_logging_days", 0)
    complete_logging_days = cycle_state.get("complete_logging_days", 0)
    over_days = cycle_state.get("over_budget_days", 0)
    recovery_success = cycle_state.get("recovery_success_count", 0)
    special = cycle_state.get("special_context_count", {})
    wins = cycle_state.get("weekly_wins", [])
    patterns = cycle_state.get("possible_patterns", [])
    training_types = cycle_state.get("training_types", {})
    days_with_logs = cycle_state.get("days_with_logs", [])
    next_focus = cycle_state.get("next_week_focus") or "训练日下午提前安排一个轻量加餐"

    special_text = "、".join(f"{name}{count}次" for name, count in special.items()) or "没有明显特殊场景"
    training_text = "、".join(f"{name}{count}次" for name, count in training_types.items()) or "暂无明确训练类型"
    win_text = "；".join(wins) if wins else "有记录就有机会调整，能接回来本身就是进度"
    if patterns:
        pattern_text = "；".join(patterns)
    elif len(days_with_logs) >= 4:
        pattern_text = "本周已有一些记录，但先不强行下结论，继续看下周是否重复出现"
    else:
        pattern_text = "数据还不多，先不判断模式"

    data_note = ""
    if len(days_with_logs) < 3:
        data_note = "这周数据还不多，先当作轻量复盘。"
    elif complete_logging_days < logging_days:
        data_note = "有些天只记录了一部分，也可以先用来观察节奏。"

    lines = [
        f"这周你完成了 {workouts} 次训练（{training_text}），饮食记录 {logging_days} 天，其中较完整记录 {complete_logging_days} 天。",
        f"超预算 {over_days} 天，特殊场景：{special_text}；恢复成功点：{recovery_success} 次。",
        f"值得肯定的是：{win_text}。",
        f"可能的模式：{pattern_text}。",
        f"下周先只抓一个小动作：{next_focus}。整体看，重点不是完美，而是偏离后还能接回来。"
    ]
    if data_note:
        lines.insert(1, data_note)
    reply = "\n".join(lines)
    return {
        "training_count": workouts,
        "meal_logging_days": logging_days,
        "complete_logging_days": complete_logging_days,
        "over_budget_days": over_days,
        "special_context": special,
        "recovery_success_count": recovery_success,
        "training_types": training_types,
        "days_with_logs": days_with_logs,
        "possible_patterns": patterns,
        "weekly_wins": wins,
        "next_week_focus": next_focus,
        "reply": reply
    }


def apply_user_context(user_text: str) -> dict[str, Any]:
    """Small CLI helper to update state from a natural-language demo input."""
    text = user_text.lower()
    patch: dict[str, Any] = {}
    if _contains(text, ["睡得差", "没睡好", "睡眠差"]):
        patch.setdefault("recovery", {})["sleep_quality"] = "poor"
    elif _contains(text, ["睡得一般", "睡眠一般"]):
        patch.setdefault("recovery", {})["sleep_quality"] = "normal"
    if _contains(text, ["出差"]):
        patch["special_context"] = ["travel"]
    if _contains(text, ["聚餐"]):
        patch["special_context"] = ["social_meal"]
    if _contains(text, ["喝酒", "饮酒"]):
        patch["special_context"] = ["alcohol"]
    if _contains(text, ["练", "有氧", "爬坡", "慢走"]):
        log_workout(user_text)
    if patch:
        update_daily_state(patch)
    state = get_daily_state()
    classified = classify_day_type(state)
    return update_daily_state({"day_type": classified["day_type"]})


def reset_demo_state() -> None:
    """Reset local demo state with a moderate default budget.

    Intended for manual CLI demos and tests only.
    """
    profile = get_profile()
    metrics = profile.setdefault("metrics", {})
    metrics.setdefault("daily_calorie_target", 1600)
    metrics.setdefault("protein_target_g", 80)
    update_daily_state({
        "date": datetime.now().strftime("%Y-%m-%d"),
        "day_type": "unknown",
        "plan_status": "not_generated",
        "nutrition": {
            "calorie_budget": metrics.get("daily_calorie_target") or 1600,
            "calories_consumed": 0,
            "calories_remaining": metrics.get("daily_calorie_target") or 1600,
            "calorie_budget_status": "on_track",
            "protein_target_g": metrics.get("protein_target_g") or 80,
            "protein_consumed_g": 0,
            "protein_gap_g": metrics.get("protein_target_g") or 80,
            "meals": []
        },
        "emotion": {"mood": "unknown", "lapse_risk": "unknown"},
        "special_context": [],
        "workouts": []
    })
