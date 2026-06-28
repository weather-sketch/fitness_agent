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


class FitnessFoodPhotoAdapterTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.old_data_dir = fitness_state.DATA_DIR
        fitness_state.DATA_DIR = Path(self.tmp.name) / "data"
        self.image_dir = Path(self.tmp.name) / "images"
        self.image_dir.mkdir()
        self.beef = self.image_dir / "beef_noodle_demo.jpg"
        self.drink = self.image_dir / "matcha_drink_demo.jpg"
        self.mixed = self.image_dir / "mixed_plate_demo.jpg"
        for path in [self.beef, self.drink, self.mixed]:
            path.write_text("demo image placeholder", encoding="utf-8")

    def tearDown(self) -> None:
        fitness_state.DATA_DIR = self.old_data_dir
        self.tmp.cleanup()

    def test_analyze_food_image_returns_complete_structure(self) -> None:
        result = fitness_vision.analyze_food_image(self.beef)

        self.assertEqual(result["detected_food"], "牛肉面")
        self.assertEqual(result["meal_category"], "noodle")
        self.assertEqual(result["confidence"], "medium")
        self.assertIn("面", result["estimated_components"])
        self.assertIn("是否喝完汤", result["uncertainties"])
        self.assertIn("raw_caption", result)

    def test_image_result_to_meal_estimate_maps_beef_noodle(self) -> None:
        image_result = fitness_vision.analyze_food_image(self.beef)
        estimate = fitness_vision.image_result_to_meal_estimate(image_result)

        self.assertEqual(estimate["meal_text"], "牛肉面")
        self.assertEqual(estimate["calorie_range_kcal"], [600, 850])
        self.assertEqual(estimate["protein_estimate_g"], 25)
        self.assertEqual(estimate["default_logged_kcal"], 725)

    def test_mixed_plate_has_lower_confidence_and_uncertainties(self) -> None:
        image_result = fitness_vision.analyze_food_image(self.mixed)
        estimate = fitness_vision.image_result_to_meal_estimate(image_result)

        self.assertEqual(image_result["meal_category"], "mixed_plate")
        self.assertEqual(estimate["confidence"], "low")
        self.assertGreaterEqual(len(estimate["uncertainties"]), 3)

    def test_log_meal_from_image_writes_daily_state(self) -> None:
        result = fitness_vision.log_meal_from_image(self.beef, user_id="default", note="午餐")
        daily = result["daily_state"]
        meals = daily["nutrition"]["meals"]

        self.assertEqual(len(meals), 1)
        self.assertEqual(meals[0]["source"], "image")
        self.assertEqual(meals[0]["vision_confidence"], "medium")
        self.assertEqual(daily["nutrition"]["calories_consumed"], 725)
        self.assertEqual(daily["nutrition"]["protein_consumed_g"], 25)

    def test_analyze_mode_does_not_write_state(self) -> None:
        fitness_vision.analyze_food_image(self.beef)

        self.assertFalse(fitness_state.get_user_data_dir("default").exists())

    def test_food_photo_does_not_generate_memory_candidate(self) -> None:
        fitness_vision.log_meal_from_image(self.beef, user_id="default")
        candidates = fitness_memory.list_memory_candidates(user_id="default")

        self.assertEqual(candidates, [])

    def test_temp_state_does_not_pollute_demo_data(self) -> None:
        fitness_vision.log_meal_from_image(self.drink, user_id="photo_user")

        self.assertTrue((fitness_state.get_user_data_dir("photo_user") / "daily").exists())
        self.assertFalse((Path(self.tmp.name) / "demo_data").exists())


if __name__ == "__main__":
    unittest.main()
