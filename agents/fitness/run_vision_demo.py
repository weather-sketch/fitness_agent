"""Portfolio demo for Fitness Agent food photo logging adapter."""

from __future__ import annotations

import copy
import shutil
import sys
from pathlib import Path
from typing import Any


AGENT_ROOT = Path(__file__).resolve().parent
TOOLS_DIR = AGENT_ROOT / "tools"
DEMO_DATA_DIR = AGENT_ROOT / "demo_data" / "vision"
DEMO_DATA_LABEL = "agents/fitness/demo_data/vision"
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
    profile = fitness_state.get_profile(user_id="default")
    profile["metrics"]["daily_calorie_target"] = 1600
    profile["metrics"]["protein_target_g"] = 80
    fitness_state.save_json(fitness_state.get_user_data_dir("default") / "profile.json", profile)


def _changes(before: dict[str, Any], after: dict[str, Any]) -> list[str]:
    before_nutrition = before.get("nutrition", {})
    after_nutrition = after.get("nutrition", {})
    return [
        f"meal_count: {len(before_nutrition.get('meals', []) or [])} -> {len(after_nutrition.get('meals', []) or [])}",
        f"calories_consumed: {before_nutrition.get('calories_consumed')} -> {after_nutrition.get('calories_consumed')}",
        f"protein_consumed_g: {before_nutrition.get('protein_consumed_g')} -> {after_nutrition.get('protein_consumed_g')}",
    ]


def _demo_flow(number: int, title: str, image_name: str, note: str | None, highlight: str) -> None:
    image_path = DEMO_ASSETS_DIR / image_name
    before = fitness_state.get_daily_state(user_id="default")
    result = fitness_vision.log_meal_from_image(image_path, user_id="default", note=note)
    after = result["daily_state"]
    image_result = result["image_result"]
    estimate = result["meal_estimate"]
    low, high = estimate["calorie_range_kcal"]

    print(f"=== Vision Demo {number}: {title} ===\n")
    _print_block("User input", f"local image: {image_path.name}" + (f" / note: {note}" if note else ""))
    _print_block("Detected result", [
        f"food: {image_result['detected_food']}",
        f"category: {image_result['meal_category']}",
        f"confidence: {image_result['confidence']}",
        f"components: {'、'.join(image_result['estimated_components'])}",
    ])
    _print_block("Meal estimate", [
        f"calories: {low}-{high} kcal",
        f"protein: about {estimate['protein_estimate_g']}g",
        f"default_logged_kcal: {estimate['default_logged_kcal']}",
        f"uncertainties: {'、'.join(estimate['uncertainties'])}",
    ])
    _print_block("Agent reply", result["reply"])
    _print_block("What changed", _changes(before, after))
    _print_block("Product highlight", highlight)


def main() -> None:
    _prepare_demo_state()
    print("Fitness Agent v0.4 Food Photo Demo Adapter")
    print(f"Demo state directory: {DEMO_DATA_LABEL}")
    print("Real state under agents/fitness/data is not read or modified.")
    print("Vision mode: demo filename adapter, not high-precision image recognition.\n")

    _demo_flow(
        1,
        "Beef Noodle",
        "beef_noodle_demo.jpg",
        "午餐",
        "图片入口降低记录成本：先用牛肉面粗估区间记录，再给用户份量/喝汤纠错入口。",
    )
    _demo_flow(
        2,
        "Matcha Drink",
        "matcha_drink_demo.jpg",
        "下午饮品",
        "饮品类重点提示糖、奶和椰子水不确定，不假装精准。",
    )
    _demo_flow(
        3,
        "Mixed Plate",
        "mixed_plate_demo.jpg",
        "自助餐盘",
        "混合餐盘置信度更低，仍可先低成本记录，并鼓励用户补充描述。",
    )


if __name__ == "__main__":
    main()
