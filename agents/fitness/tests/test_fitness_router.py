from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from router import detect_fitness_intent  # noqa: E402


class FitnessRouterTest(unittest.TestCase):
    def test_training_day_message_routes_to_daily_plan(self) -> None:
        result = detect_fitness_intent("今天晚上练臀，怎么吃？")
        self.assertEqual(result["intent"], "daily_plan")
        self.assertIn("generate_daily_plan", result["suggested_tool_chain"])

    def test_meal_message_routes_to_log_meal(self) -> None:
        result = detect_fitness_intent("中午吃了一碗牛肉面")
        self.assertEqual(result["intent"], "log_meal")

    def test_post_workout_message_routes_to_post_workout(self) -> None:
        result = detect_fitness_intent("练完了，今天强度很大，练后吃什么？")
        self.assertEqual(result["intent"], "post_workout_meal")

    def test_lapse_message_routes_to_lapse_recovery(self) -> None:
        result = detect_fitness_intent("我今天吃爆了，不想记了")
        self.assertEqual(result["intent"], "lapse_recovery")

    def test_weekly_review_message_routes_to_weekly_review(self) -> None:
        result = detect_fitness_intent("这周怎么样？")
        self.assertEqual(result["intent"], "weekly_review")

    def test_non_fitness_message_routes_to_unknown(self) -> None:
        result = detect_fitness_intent("帮我把明天的会议整理一下")
        self.assertEqual(result["intent"], "unknown")
        self.assertEqual(result["suggested_tool_chain"], [])


if __name__ == "__main__":
    unittest.main()
