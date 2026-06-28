"""CLI for the Fitness food photo demo adapter."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import fitness_state  # noqa: E402
import fitness_vision  # noqa: E402


def _print_debug(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def _print_analysis(image_result: dict[str, Any], meal_estimate: dict[str, Any]) -> None:
    low, high = meal_estimate["calorie_range_kcal"]
    print(f"Provider: {image_result['provider']}")
    print(f"Provider status: {image_result['provider_status']}")
    print(f"Fallback used: {str(image_result.get('fallback_used', False)).lower()}")
    print(f"Detected food: {image_result['detected_food']}")
    print(f"Category: {image_result['meal_category']}")
    print(f"Calories: {low}-{high} kcal")
    print(f"Protein: about {meal_estimate['protein_estimate_g']}g")
    print(f"Confidence: {meal_estimate['confidence']}")
    print("Uncertainties: " + "、".join(meal_estimate.get("uncertainties", [])))
    print()
    print(fitness_vision.generate_food_photo_reply(image_result, meal_estimate))


def main() -> None:
    parser = argparse.ArgumentParser(description="Fitness food photo demo adapter CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    analyze = subparsers.add_parser("analyze", help="Analyze a local food image without writing state")
    analyze.add_argument("--image", required=True)
    analyze.add_argument("--note", default=None)
    analyze.add_argument("--provider", default="demo", choices=sorted(fitness_vision.PROVIDERS))
    analyze.add_argument("--fallback-provider", default="demo", choices=sorted(fitness_vision.PROVIDERS - {"auto"}))
    analyze.add_argument("--manual-food", default=None)
    analyze.add_argument("--manual-category", default=None)
    analyze.add_argument("--manual-confidence", default=None, choices=["low", "medium", "high"])
    analyze.add_argument("--manual-components", default=None, help="Comma-separated component list for manual provider")
    analyze.add_argument("--debug", action="store_true")

    log = subparsers.add_parser("log", help="Analyze a food image and log it into daily state")
    log.add_argument("--image", required=True)
    log.add_argument("--user", default="default")
    log.add_argument("--note", default=None)
    log.add_argument("--date", default=None, help="Daily state date in YYYY-MM-DD format")
    log.add_argument("--provider", default="demo", choices=sorted(fitness_vision.PROVIDERS))
    log.add_argument("--fallback-provider", default="demo", choices=sorted(fitness_vision.PROVIDERS - {"auto"}))
    log.add_argument("--manual-food", default=None)
    log.add_argument("--manual-category", default=None)
    log.add_argument("--manual-confidence", default=None, choices=["low", "medium", "high"])
    log.add_argument("--manual-components", default=None, help="Comma-separated component list for manual provider")
    log.add_argument("--debug", action="store_true")

    args = parser.parse_args()
    try:
        if args.command == "analyze":
            image_result = fitness_vision.analyze_food_image(
                args.image,
                user_text=args.note,
                provider=args.provider,
                fallback_provider=args.fallback_provider,
                manual_food=args.manual_food,
                manual_category=args.manual_category,
                manual_confidence=args.manual_confidence,
                manual_components=args.manual_components,
            )
            meal_estimate = fitness_vision.image_result_to_meal_estimate(image_result)
            _print_analysis(image_result, meal_estimate)
            if args.debug:
                _print_debug({"image_result": image_result, "meal_estimate": meal_estimate})
            return
        if args.command == "log":
            result = fitness_vision.log_meal_from_image(
                args.image,
                user_id=args.user,
                note=args.note,
                date=args.date,
                provider=args.provider,
                fallback_provider=args.fallback_provider,
                manual_food=args.manual_food,
                manual_category=args.manual_category,
                manual_confidence=args.manual_confidence,
                manual_components=args.manual_components,
            )
            print(result["reply"])
            nutrition = result["daily_state"].get("nutrition", {})
            logged_date = result["daily_state"].get("date")
            daily_path = fitness_state.get_user_data_dir(args.user) / "daily" / f"{logged_date}.json"
            print()
            print(f"Provider: {result['image_result']['provider']}")
            print(f"Provider status: {result['image_result']['provider_status']}")
            print(f"Fallback used: {str(result['image_result'].get('fallback_used', False)).lower()}")
            print(f"Logged date: {logged_date}")
            print(f"Daily state file: {daily_path}")
            print("Meal log field: nutrition.meals")
            print(f"Logged source: {result['meal_log']['source']}")
            print(f"Meal count after: {len(nutrition.get('meals', []) or [])}")
            print(f"Calories consumed today: {round(nutrition.get('calories_consumed') or 0)} kcal")
            if nutrition.get("calories_remaining") is not None:
                print(f"Calories remaining today: {round(nutrition['calories_remaining'])} kcal")
            if args.debug:
                _print_debug(result)
            return
    except fitness_state.FitnessStateError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
