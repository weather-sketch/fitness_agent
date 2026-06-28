from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
for path in (ROOT, TOOLS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import fitness_memory  # noqa: E402
import fitness_state  # noqa: E402
import fitness_vision  # noqa: E402


class FitnessFoodPhotoProviderTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.old_data_dir = fitness_state.DATA_DIR
        fitness_state.DATA_DIR = Path(self.tmp.name) / "data"
        self.image = Path(self.tmp.name) / "beef_noodle_demo.jpg"
        self.image.write_text("demo image placeholder", encoding="utf-8")
        self.unknown_image = Path(self.tmp.name) / "random_food.jpg"
        self.unknown_image.write_text("demo image placeholder", encoding="utf-8")

    def tearDown(self) -> None:
        fitness_state.DATA_DIR = self.old_data_dir
        self.tmp.cleanup()

    def _assert_provider_schema(self, result: dict) -> None:
        for key in [
            "provider",
            "provider_status",
            "fallback_used",
            "detected_food",
            "meal_category",
            "confidence",
            "estimated_components",
            "uncertainties",
            "raw_caption",
            "provider_notes",
            "image_path",
        ]:
            self.assertIn(key, result)

    def test_demo_provider_outputs_complete_schema(self) -> None:
        result = fitness_vision.analyze_food_image(self.image, provider="demo")

        self._assert_provider_schema(result)
        self.assertEqual(result["provider"], "demo")
        self.assertEqual(result["provider_status"], "ok")
        self.assertFalse(result["fallback_used"])
        self.assertEqual(result["detected_food"], "牛肉面")

    def test_manual_provider_outputs_complete_schema(self) -> None:
        result = fitness_vision.analyze_food_image(
            self.image,
            provider="manual",
            manual_food="牛肉面",
            manual_category="noodle",
            manual_confidence="medium",
        )

        self._assert_provider_schema(result)
        self.assertEqual(result["provider"], "manual")
        self.assertEqual(result["provider_status"], "ok")
        self.assertFalse(result["fallback_used"])
        self.assertEqual(result["confidence"], "medium")

    def test_auto_provider_falls_back_when_vision_api_unavailable(self) -> None:
        result = fitness_vision.analyze_food_image(self.image, provider="auto")

        self.assertEqual(result["requested_provider"], "auto")
        self.assertEqual(result["provider"], "demo")
        self.assertEqual(result["provider_status"], "fallback")
        self.assertTrue(result["fallback_used"])
        self.assertIn("FITNESS_VISION_API_KEY", " ".join(result["provider_notes"]))

    def test_provider_error_falls_back_without_crashing(self) -> None:
        original = fitness_vision.analyze_food_image_vision_api

        def broken_provider(*args, **kwargs):
            raise RuntimeError("temporary provider error")

        fitness_vision.analyze_food_image_vision_api = broken_provider
        try:
            result = fitness_vision.analyze_food_image(self.image, provider="vision_api")
        finally:
            fitness_vision.analyze_food_image_vision_api = original

        self.assertEqual(result["provider"], "demo")
        self.assertEqual(result["provider_status"], "fallback")
        self.assertTrue(result["fallback_used"])
        self.assertIn("temporary provider error", " ".join(result["provider_notes"]))

    def test_unknown_food_uses_conservative_low_confidence_estimate(self) -> None:
        image_result = fitness_vision.analyze_food_image(
            self.unknown_image,
            provider="manual",
            manual_food="神秘便当",
            manual_category="unknown",
            manual_confidence="high",
        )
        estimate = fitness_vision.image_result_to_meal_estimate(image_result)

        self.assertEqual(image_result["meal_category"], "unknown")
        self.assertEqual(estimate["confidence"], "low")
        self.assertEqual(estimate["calorie_range_kcal"], [350, 750])
        self.assertIn("食物类别需要确认", estimate["uncertainties"])

    def test_log_manual_provider_writes_nutrition_meals(self) -> None:
        result = fitness_vision.log_meal_from_image(
            self.image,
            user_id="manual_user",
            date="2026-06-24",
            provider="manual",
            manual_food="牛肉面",
            manual_category="noodle",
            manual_confidence="medium",
        )
        meals = result["daily_state"]["nutrition"]["meals"]

        self.assertEqual(len(meals), 1)
        self.assertEqual(meals[0]["source"], "image")
        self.assertEqual(meals[0]["logged_calories"], 725)
        self.assertEqual(meals[0]["vision_provider"], "manual")
        self.assertEqual(result["daily_state"]["date"], "2026-06-24")

    def test_food_photo_does_not_generate_memory_candidate(self) -> None:
        fitness_vision.log_meal_from_image(
            self.image,
            user_id="manual_user",
            provider="manual",
            manual_food="牛肉面",
            manual_category="noodle",
        )

        self.assertEqual(fitness_memory.list_memory_candidates(user_id="manual_user"), [])

    def test_analyze_only_does_not_pollute_default_state(self) -> None:
        fitness_vision.analyze_food_image(
            self.image,
            provider="manual",
            manual_food="牛肉面",
            manual_category="noodle",
        )

        self.assertFalse(fitness_state.get_user_data_dir("default").exists())


if __name__ == "__main__":
    unittest.main()
