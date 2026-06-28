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

import fitness_state  # noqa: E402
import run_showcase_demo  # noqa: E402


class FitnessShowcaseDemoTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.old_data_dir = fitness_state.DATA_DIR
        self.data_root = Path(self.tmp.name) / "showcase"

    def tearDown(self) -> None:
        fitness_state.DATA_DIR = self.old_data_dir
        self.tmp.cleanup()

    def test_all_flows_run(self) -> None:
        results = run_showcase_demo.run_showcase_flow("all", data_root=self.data_root)

        self.assertEqual(
            [item["flow_id"] for item in results],
            ["text", "lapse", "vision", "memory", "recall", "fallback", "channel", "openclaw"],
        )
        self.assertTrue(all(item["agent_reply"] for item in results))

    def test_each_single_flow_runs(self) -> None:
        expected = {
            "text": ["text", "lapse"],
            "vision": ["vision"],
            "memory": ["memory"],
            "recall": ["recall"],
            "fallback": ["fallback"],
            "channel": ["channel"],
            "openclaw": ["openclaw"],
        }
        for flow, flow_ids in expected.items():
            with self.subTest(flow=flow):
                results = run_showcase_demo.run_showcase_flow(flow, data_root=self.data_root)
                self.assertEqual([item["flow_id"] for item in results], flow_ids)

    def test_showcase_uses_demo_state_not_default_real_state(self) -> None:
        results = run_showcase_demo.run_showcase_flow("text", data_root=self.data_root)

        self.assertTrue(results)
        self.assertTrue((self.data_root / "users" / "showcase_text_user").exists())
        self.assertEqual(fitness_state.DATA_DIR, self.data_root)

    def test_vision_flow_writes_demo_nutrition_meals(self) -> None:
        run_showcase_demo.reset_demo_user_state(self.data_root)
        result = run_showcase_demo.run_food_photo_flow(user_id="vision_user", date="2026-06-24")
        state = fitness_state.get_daily_state(user_id="vision_user", date="2026-06-24")
        meals = state["nutrition"]["meals"]

        self.assertEqual(result["flow_id"], "vision")
        self.assertEqual(len(meals), 1)
        self.assertEqual(meals[0]["source"], "image")
        self.assertEqual(meals[0]["logged_calories"], 725)
        self.assertIn("provider: manual", result["summary"])

    def test_memory_flow_applies_preference_and_removes_yogurt(self) -> None:
        run_showcase_demo.reset_demo_user_state(self.data_root)
        result = run_showcase_demo.run_active_memory_flow(user_id="memory_user")

        self.assertIn("active_preferences_applied: ['avoid_yogurt_pre_workout']", result["summary"])
        self.assertIn("reply_contains_yogurt: false", result["summary"])
        self.assertNotIn("酸奶", result["agent_reply"])

    def test_recall_flow_changes_should_send_after_opt_in(self) -> None:
        run_showcase_demo.reset_demo_user_state(self.data_root)
        result = run_showcase_demo.run_recall_flow(user_id="recall_user")

        self.assertIn("before_should_send: false", result["summary"])
        self.assertIn("before_blocked_reason: recall_disabled", result["summary"])
        self.assertIn("after_should_send: true", result["summary"])
        self.assertIn("after_blocked_reason: ready", result["summary"])

    def test_fallback_flow_is_unhandled_and_does_not_create_state(self) -> None:
        run_showcase_demo.reset_demo_user_state(self.data_root)
        result = run_showcase_demo.run_non_fitness_fallback_flow(user_id="fallback_user")

        self.assertIn("handled: false", result["summary"])
        self.assertIn("intent: unknown", result["summary"])
        self.assertFalse((self.data_root / "users" / "fallback_user").exists())


if __name__ == "__main__":
    unittest.main()
