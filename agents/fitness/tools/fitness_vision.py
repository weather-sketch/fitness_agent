"""Food photo adapter boundary for Fitness Agent.

This module is an adapter boundary, not a high-precision vision system. The
default provider keeps local demos stable, while manual and vision_api providers
share the same coarse output contract for future replacement.
"""

from __future__ import annotations

from datetime import datetime
import os
from pathlib import Path
from typing import Any

import fitness_logic
import fitness_state


PROVIDERS = {"demo", "manual", "vision_api", "auto"}
CONFIDENCE_RANK = {"low": 1, "medium": 2, "high": 3}


def _now_id(prefix: str) -> str:
    return f"{prefix}-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"


def _number(value: Any, default: float = 0) -> float:
    return float(value) if isinstance(value, (int, float)) else default


def _budget_status(remaining: float | None) -> str:
    if remaining is None:
        return "unknown"
    if remaining < 0:
        return "over"
    if remaining <= 200:
        return "near_limit"
    return "on_track"


def _display_confidence(confidence: str | None) -> str:
    return {"high": "高", "medium": "中", "low": "低"}.get(str(confidence), str(confidence or "低"))


def _normalize_confidence(confidence: str | None, default: str = "low") -> str:
    value = str(confidence or default).lower()
    return value if value in CONFIDENCE_RANK else default


def _split_components(value: str | list[str] | None) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if not value:
        return []
    return [item.strip() for item in str(value).replace("，", ",").split(",") if item.strip()]


def _provider_result(
    *,
    provider: str,
    provider_status: str,
    fallback_used: bool,
    detected_food: str,
    meal_category: str,
    confidence: str,
    estimated_components: list[str] | None = None,
    uncertainties: list[str] | None = None,
    raw_caption: str = "",
    provider_notes: list[str] | None = None,
    image_path: str | Path,
    requested_provider: str | None = None,
    fallback_provider: str | None = None,
) -> dict[str, Any]:
    return {
        "provider": provider,
        "provider_status": provider_status,
        "fallback_used": bool(fallback_used),
        "fallback_provider": fallback_provider,
        "requested_provider": requested_provider or provider,
        "detected_food": detected_food,
        "meal_category": meal_category,
        "confidence": _normalize_confidence(confidence),
        "estimated_components": estimated_components or [],
        "uncertainties": uncertainties or [],
        "raw_caption": raw_caption,
        "provider_notes": provider_notes or [],
        "image_path": str(image_path),
    }


def _provider_unavailable(
    *,
    provider: str,
    image_path: str | Path,
    message: str,
    requested_provider: str | None = None,
) -> dict[str, Any]:
    return _provider_result(
        provider=provider,
        provider_status="unavailable",
        fallback_used=False,
        detected_food="未知餐食",
        meal_category="unknown",
        confidence="low",
        uncertainties=["provider 不可用", "需要用户补充描述"],
        raw_caption="",
        provider_notes=[message],
        image_path=image_path,
        requested_provider=requested_provider or provider,
    )


def _provider_error(
    *,
    provider: str,
    image_path: str | Path,
    message: str,
    requested_provider: str | None = None,
) -> dict[str, Any]:
    return _provider_result(
        provider=provider,
        provider_status="error",
        fallback_used=False,
        detected_food="未知餐食",
        meal_category="unknown",
        confidence="low",
        uncertainties=["provider 出错", "需要用户补充描述"],
        raw_caption="",
        provider_notes=[message],
        image_path=image_path,
        requested_provider=requested_provider or provider,
    )


def _ensure_user_budget(user_id: str, date: str | None = None) -> dict[str, Any]:
    state = fitness_state.get_daily_state(user_id=user_id, date=date)
    nutrition = state.setdefault("nutrition", {})
    if nutrition.get("calorie_budget") is not None and nutrition.get("protein_target_g") is not None:
        return state
    profile = fitness_state.get_profile(user_id=user_id)
    metrics = profile.get("metrics", {})
    calorie_budget = nutrition.get("calorie_budget") or metrics.get("daily_calorie_target") or 1600
    protein_target = nutrition.get("protein_target_g") or metrics.get("protein_target_g") or 80
    return fitness_state.update_daily_state({
        "nutrition": {
            "calorie_budget": calorie_budget,
            "calories_remaining": calorie_budget - _number(nutrition.get("calories_consumed")),
            "protein_target_g": protein_target,
            "protein_gap_g": max(0, protein_target - _number(nutrition.get("protein_consumed_g"))),
        }
    }, user_id=user_id, date=date)


def analyze_food_image_demo(image_path: str | Path, user_text: str | None = None) -> dict[str, Any]:
    """Return a coarse, deterministic demo food image analysis result."""
    path = Path(image_path)
    if not path.exists():
        raise fitness_state.FitnessStateError(f"Image not found: {path}")
    hint = f"{path.stem} {user_text or ''}".lower()

    if any(term in hint for term in ["beef", "noodle", "niurou", "牛肉面", "面"]):
        return _provider_result(
            provider="demo",
            provider_status="ok",
            fallback_used=False,
            detected_food="牛肉面",
            meal_category="noodle",
            confidence="medium",
            estimated_components=["面", "牛肉", "汤"],
            uncertainties=["份量大小", "是否喝完汤", "是否有额外小菜"],
            raw_caption="demo adapter: noodle bowl with beef-like topping",
            image_path=path,
        )
    if any(term in hint for term in ["matcha", "coffee", "drink", "latte", "抹茶", "咖啡", "饮品"]):
        return _provider_result(
            provider="demo",
            provider_status="ok",
            fallback_used=False,
            detected_food="抹茶饮品",
            meal_category="drink",
            confidence="medium",
            estimated_components=["抹茶", "饮品"],
            uncertainties=["是否含糖", "是否有椰子水", "是否加牛奶"],
            raw_caption="demo adapter: green drink / cafe beverage",
            image_path=path,
        )
    if any(term in hint for term in ["buffet", "mixed", "plate", "自助", "拼盘", "混合"]):
        return _provider_result(
            provider="demo",
            provider_status="ok",
            fallback_used=False,
            detected_food="混合餐盘",
            meal_category="mixed_plate",
            confidence="low",
            estimated_components=["主食", "肉类", "配菜"],
            uncertainties=["食物种类较多", "份量差异大", "酱料和油量不确定", "是否有甜品或饮料"],
            raw_caption="demo adapter: mixed plate with multiple components",
            image_path=path,
        )
    return _provider_result(
        provider="demo",
        provider_status="ok",
        fallback_used=False,
        detected_food="未知餐食",
        meal_category="unknown",
        confidence="low",
        estimated_components=[],
        uncertainties=["图片信息不足", "份量不确定", "需要用户补充描述"],
        raw_caption="demo adapter: no confident filename/category match",
        image_path=path,
    )


def analyze_food_image_manual(
    image_path: str | Path,
    user_text: str | None = None,
    manual_food: str | None = None,
    manual_category: str | None = None,
    manual_confidence: str | None = None,
    manual_components: str | list[str] | None = None,
) -> dict[str, Any]:
    """Return a structured result from a user/admin supplied food description."""
    path = Path(image_path)
    if not path.exists():
        raise fitness_state.FitnessStateError(f"Image not found: {path}")
    food = (manual_food or user_text or "未知餐食").strip()
    category = (manual_category or "unknown").strip() or "unknown"
    confidence = _normalize_confidence(manual_confidence, default="low")
    components = _split_components(manual_components)
    if not components and category == "noodle":
        components = ["面", "蛋白质", "汤/酱汁"]
    elif not components and category == "drink":
        components = ["饮品"]
    elif not components and category == "mixed_plate":
        components = ["主食", "蛋白质", "配菜"]
    uncertainties = ["份量大小", "配料细节"]
    if category == "unknown":
        uncertainties.append("食物类别需要确认")
    return _provider_result(
        provider="manual",
        provider_status="ok",
        fallback_used=False,
        detected_food=food,
        meal_category=category,
        confidence=confidence,
        estimated_components=components,
        uncertainties=uncertainties,
        raw_caption=f"manual provider: {food}",
        provider_notes=["manual structured input; no image recognition performed"],
        image_path=path,
    )


def analyze_food_image_vision_api(image_path: str | Path, user_text: str | None = None) -> dict[str, Any]:
    """Placeholder contract for a real vision provider.

    The adapter is intentionally disabled unless a future safe wrapper is added.
    It never performs network calls in this version.
    """
    path = Path(image_path)
    if not path.exists():
        raise fitness_state.FitnessStateError(f"Image not found: {path}")
    api_key = os.environ.get("FITNESS_VISION_API_KEY")
    endpoint = os.environ.get("FITNESS_VISION_API_ENDPOINT")
    if not api_key or not endpoint:
        return _provider_unavailable(
            provider="vision_api",
            image_path=path,
            message="FITNESS_VISION_API_KEY and FITNESS_VISION_API_ENDPOINT are not configured",
        )
    return _provider_unavailable(
        provider="vision_api",
        image_path=path,
        message="vision_api contract is present, but network calls are disabled in this local adapter",
    )


def _vision_api_configured() -> bool:
    return bool(os.environ.get("FITNESS_VISION_API_KEY") and os.environ.get("FITNESS_VISION_API_ENDPOINT"))


def analyze_food_image_with_provider(
    image_path: str | Path,
    user_text: str | None = None,
    provider: str = "demo",
    fallback_provider: str | None = "demo",
    **kwargs: Any,
) -> dict[str, Any]:
    """Analyze a food image through a named provider and safe fallback."""
    requested_provider = provider
    if provider not in PROVIDERS:
        raise fitness_state.FitnessStateError(f"Unsupported vision provider: {provider}")
    selected_provider = "vision_api" if provider == "auto" else provider

    try:
        if selected_provider == "demo":
            result = analyze_food_image_demo(image_path, user_text=user_text)
        elif selected_provider == "manual":
            result = analyze_food_image_manual(
                image_path,
                user_text=user_text,
                manual_food=kwargs.get("manual_food"),
                manual_category=kwargs.get("manual_category"),
                manual_confidence=kwargs.get("manual_confidence"),
                manual_components=kwargs.get("manual_components"),
            )
        elif selected_provider == "vision_api":
            result = analyze_food_image_vision_api(image_path, user_text=user_text)
        else:
            result = _provider_unavailable(
                provider=selected_provider,
                image_path=image_path,
                message=f"Unsupported provider: {selected_provider}",
                requested_provider=requested_provider,
            )
    except fitness_state.FitnessStateError:
        raise
    except Exception as exc:  # Provider failures should not crash the flow.
        result = _provider_error(
            provider=selected_provider,
            image_path=image_path,
            message=str(exc),
            requested_provider=requested_provider,
        )

    result["requested_provider"] = requested_provider
    if result.get("provider_status") in {"ok", "fallback"}:
        return result

    if fallback_provider and fallback_provider != selected_provider:
        fallback = analyze_food_image_with_provider(
            image_path,
            user_text=user_text,
            provider=fallback_provider,
            fallback_provider=None,
            **kwargs,
        )
        notes = list(result.get("provider_notes", [])) + list(fallback.get("provider_notes", []))
        fallback["provider_status"] = "fallback"
        fallback["fallback_used"] = True
        fallback["fallback_provider"] = fallback_provider
        fallback["requested_provider"] = requested_provider
        fallback["provider_notes"] = notes
        return fallback
    return result


def analyze_food_image(
    image_path: str | Path,
    user_text: str | None = None,
    provider: str = "demo",
    fallback_provider: str | None = "demo",
    **kwargs: Any,
) -> dict[str, Any]:
    """Return a coarse food image analysis result with a stable provider schema."""
    return analyze_food_image_with_provider(
        image_path,
        user_text=user_text,
        provider=provider,
        fallback_provider=fallback_provider,
        **kwargs,
    )


def image_result_to_meal_estimate(image_result: dict[str, Any]) -> dict[str, Any]:
    """Map image analysis output to the existing rough meal estimate format."""
    meal_text = image_result.get("detected_food") or "未知餐食"
    meal_category = image_result.get("meal_category")
    if meal_category == "mixed_plate":
        estimate = {
            "estimated_calories_min": 800,
            "estimated_calories_max": 1400,
            "estimated_protein": 35,
            "confidence": "low",
            "uncertainty_factors": ["食物种类较多", "份量差异大", "酱料和油量不确定"],
        }
    elif meal_category == "unknown" or meal_text == "未知餐食":
        estimate = {
            "estimated_calories_min": 350,
            "estimated_calories_max": 750,
            "estimated_protein": 15,
            "confidence": "low",
            "uncertainty_factors": ["食物类型", "份量", "烹饪油量"],
        }
    else:
        estimate = fitness_logic.estimate_calorie_range(meal_text)
    low = int(estimate["estimated_calories_min"])
    high = int(estimate["estimated_calories_max"])
    confidence = image_result.get("confidence") or estimate.get("confidence", "low")
    if meal_category == "unknown":
        confidence = "low"
    return {
        "meal_text": meal_text,
        "calorie_range_kcal": [low, high],
        "protein_estimate_g": int(estimate["estimated_protein"]),
        "confidence": _normalize_confidence(confidence),
        "uncertainties": list(
            image_result.get("uncertainties")
            or estimate.get("uncertainty_factors")
            or estimate.get("uncertain_factors", [])
        ),
        "default_logged_kcal": round((low + high) / 2),
    }


def generate_food_photo_reply(image_result: dict[str, Any], meal_estimate: dict[str, Any]) -> str:
    """Generate a user-facing, low-certainty food photo logging reply."""
    low, high = meal_estimate["calorie_range_kcal"]
    uncertainties = "、".join(meal_estimate.get("uncertainties", [])) or "份量和配料"
    return "\n".join([
        f"我先把这餐按{meal_estimate['meal_text']}粗略记录：",
        f"- 估算热量：{low}-{high} kcal",
        f"- 蛋白质：约 {meal_estimate['protein_estimate_g']}g",
        f"- 置信度：{_display_confidence(meal_estimate['confidence'])}",
        f"不确定因素：{uncertainties}。",
        "",
        f"先按 {meal_estimate['default_logged_kcal']} kcal 记录没问题；如果你愿意，也可以告诉我份量、配料或有没有喝汤/加糖，我再帮你修正。",
    ])


def log_meal_from_image(
    image_path: str | Path,
    user_id: str = "default",
    note: str | None = None,
    date: str | None = None,
    provider: str = "demo",
    fallback_provider: str | None = "demo",
    **kwargs: Any,
) -> dict[str, Any]:
    """Analyze a food image and log the estimate into the existing daily state."""
    image_result = analyze_food_image(
        image_path,
        user_text=note,
        provider=provider,
        fallback_provider=fallback_provider,
        **kwargs,
    )
    meal_estimate = image_result_to_meal_estimate(image_result)
    state = _ensure_user_budget(user_id=user_id, date=date)
    nutrition = state.get("nutrition", {})
    low, high = meal_estimate["calorie_range_kcal"]
    kcal = meal_estimate["default_logged_kcal"]
    protein = meal_estimate["protein_estimate_g"]
    meal_log = {
        "meal_id": _now_id("meal-img"),
        "meal_type": "unknown",
        "time": None,
        "description": meal_estimate["meal_text"] if note is None else f"{meal_estimate['meal_text']}（{note}）",
        "estimated_calories_min": low,
        "estimated_calories_max": high,
        "estimated_protein": protein,
        "confidence": meal_estimate["confidence"],
        "uncertainty_factors": meal_estimate["uncertainties"],
        "logged_calories": kcal,
        "source": "image",
        "image_path": str(image_path),
        "vision_confidence": image_result.get("confidence"),
        "vision_uncertainties": image_result.get("uncertainties", []),
        "vision_provider": image_result.get("provider"),
        "vision_provider_status": image_result.get("provider_status"),
        "vision_fallback_used": image_result.get("fallback_used", False),
    }
    state = fitness_state.append_meal_log(meal_log, user_id=user_id, date=date)
    nutrition = state.get("nutrition", {})
    consumed = _number(nutrition.get("calories_consumed")) + kcal
    protein_consumed = _number(nutrition.get("protein_consumed_g")) + protein
    budget = nutrition.get("calorie_budget")
    protein_target = nutrition.get("protein_target_g")
    remaining = None if budget is None else _number(budget) - consumed
    protein_gap = None if protein_target is None else max(0, _number(protein_target) - protein_consumed)
    state = fitness_state.update_daily_state({
        "nutrition": {
            "calories_consumed": consumed,
            "calories_remaining": remaining,
            "calorie_budget_status": _budget_status(remaining),
            "protein_consumed_g": protein_consumed,
            "protein_gap_g": protein_gap,
        }
    }, user_id=user_id, date=date)
    return {
        "image_result": image_result,
        "meal_estimate": meal_estimate,
        "meal_log": meal_log,
        "daily_state": state,
        "reply": generate_food_photo_reply(image_result, meal_estimate),
    }
