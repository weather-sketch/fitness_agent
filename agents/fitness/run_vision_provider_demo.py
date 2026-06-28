"""Portfolio demo for Fitness Agent vision provider adapter."""

from __future__ import annotations

import copy
import shutil
import sys
from pathlib import Path
from typing import Any


AGENT_ROOT = Path(__file__).resolve().parent
TOOLS_DIR = AGENT_ROOT / "tools"
DEMO_DATA_DIR = AGENT_ROOT / "demo_data" / "vision_provider"
DEMO_DATA_LABEL = "agents/fitness/demo_data/vision_provider"
DEMO_ASSETS_DIR = AGENT_ROOT / "demo_assets" / "vision"

if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import fitness_state  # noqa: E402
import fitness_vision  # noqa: E402


def _print_block(title: str, body: str | list[str]) -> None:
    print(f"{title}:")
    if isinstance(body, list):
        for item in body:
            print(f"- {item}")
    else:
        print(body)
    print()


def _prepare_demo_state() -> None:
    if DEMO_DATA_DIR.exists():
        shutil.rmtree(DEMO_DATA_DIR)
    DEMO_DATA_DIR.mkdir(parents=True, exist_ok=True)
    fitness_state.DATA_DIR = DEMO_DATA_DIR
    for name in ["profile.json", "recall_state.json", "memory_candidates.json"]:
        fitness_state.save_json(
            fitness_state.get_user_data_dir("default") / name,
            copy.deepcopy(fitness_state.DEFAULTS[name]),
        )


def _state_changes(before: dict[str, Any], after: dict[str, Any]) -> list[str]:
    before_meals = before.get("nutrition", {}).get("meals", []) or []
    after_meals = after.get("nutrition", {}).get("meals", []) or []
    return [
        f"meal_count: {len(before_meals)} -> {len(after_meals)}",
        f"logged_date: {after.get('date')}",
        "state field: nutrition.meals",
    ]


def _demo_analyze(
    number: int,
    title: str,
    image_name: str,
    provider: str,
    highlight: str,
    **kwargs: Any,
) -> None:
    image_path = DEMO_ASSETS_DIR / image_name
    image_result = fitness_vision.analyze_food_image(image_path, provider=provider, **kwargs)
    estimate = fitness_vision.image_result_to_meal_estimate(image_result)
    low, high = estimate["calorie_range_kcal"]

    print(f"=== Vision Provider Demo {number}: {title} ===\n")
    _print_block("User input", [
        f"image: {image_path.name}",
        f"provider: {provider}",
    ])
    _print_block("Provider result", [
        f"provider: {image_result['provider']}",
        f"provider_status: {image_result['provider_status']}",
        f"fallback_used: {image_result['fallback_used']}",
        f"food: {image_result['detected_food']}",
        f"category: {image_result['meal_category']}",
        f"confidence: {image_result['confidence']}",
    ])
    _print_block("Meal estimate", [
        f"calories: {low}-{high} kcal",
        f"protein: about {estimate['protein_estimate_g']}g",
        f"default_logged_kcal: {estimate['default_logged_kcal']}",
        f"uncertainties: {'、'.join(estimate['uncertainties'])}",
    ])
    _print_block("Agent reply", fitness_vision.generate_food_photo_reply(image_result, estimate))
    _print_block("What changed", "Analyze-only flow: no state write.")
    _print_block("Product highlight", highlight)


def _demo_log_manual() -> None:
    image_path = DEMO_ASSETS_DIR / "mixed_plate_demo.jpg"
    before = fitness_state.get_daily_state(user_id="default")
    result = fitness_vision.log_meal_from_image(
        image_path,
        user_id="default",
        note="自助餐盘",
        provider="manual",
        manual_food="自助餐盘",
        manual_category="mixed_plate",
        manual_confidence="low",
    )
    after = result["daily_state"]
    image_result = result["image_result"]
    estimate = result["meal_estimate"]
    low, high = estimate["calorie_range_kcal"]

    print("=== Vision Provider Demo 4: Manual uncertain meal log ===\n")
    _print_block("User input", [
        f"image: {image_path.name}",
        "provider: manual",
        "manual_food: 自助餐盘",
        "manual_category: mixed_plate",
        "manual_confidence: low",
    ])
    _print_block("Provider result", [
        f"provider: {image_result['provider']}",
        f"provider_status: {image_result['provider_status']}",
        f"fallback_used: {image_result['fallback_used']}",
        f"food: {image_result['detected_food']}",
        f"category: {image_result['meal_category']}",
        f"confidence: {image_result['confidence']}",
    ])
    _print_block("Meal estimate", [
        f"calories: {low}-{high} kcal",
        f"protein: about {estimate['protein_estimate_g']}g",
        f"default_logged_kcal: {estimate['default_logged_kcal']}",
        f"uncertainties: {'、'.join(estimate['uncertainties'])}",
    ])
    _print_block("Agent reply", result["reply"])
    _print_block("What changed", _state_changes(before, after))
    _print_block("Product highlight", "低置信度图片仍可先记录到 daily meal log，并把不确定性留给用户确认。")


def main() -> None:
    _prepare_demo_state()
    print("Fitness Agent v0.4 Vision Provider Adapter Demo")
    print(f"Demo state directory: {DEMO_DATA_LABEL}")
    print("Real state under agents/fitness/data is not read or modified.")
    print("Vision provider mode: demo/manual/auto fallback contract; no external API calls.\n")

    _demo_analyze(
        1,
        "Demo provider",
        "beef_noodle_demo.jpg",
        "demo",
        "保留稳定本地 demo：文件名 fixture 进入统一 provider schema。",
    )
    _demo_analyze(
        2,
        "Manual provider",
        "beef_noodle_demo.jpg",
        "manual",
        "没有真实 API key 时，手动结构化输入也能走同一条 food photo contract。",
        manual_food="牛肉面",
        manual_category="noodle",
        manual_confidence="medium",
    )
    _demo_analyze(
        3,
        "Auto provider fallback",
        "beef_noodle_demo.jpg",
        "auto",
        "auto 在 vision_api 未配置时 fallback 到 demo，不把 provider 不可用伪装成成功。",
    )
    _demo_log_manual()


if __name__ == "__main__":
    main()
