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
from handler import handle_fitness_message  # noqa: E402


class FitnessMemoryCandidatesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.old_data_dir = fitness_state.DATA_DIR
        fitness_state.DATA_DIR = Path(self.tmp.name) / "data"

    def tearDown(self) -> None:
        fitness_state.DATA_DIR = self.old_data_dir
        self.tmp.cleanup()

    def test_new_user_init_creates_memory_candidates_and_valid_state(self) -> None:
        user_id = "new_user"
        fitness_state.ensure_user_state(user_id=user_id, date="2026-06-20")
        result = fitness_state.validate_user_state(user_id=user_id)
        user_dir = fitness_state.get_user_data_dir(user_id)

        self.assertTrue((user_dir / "memory_candidates.json").exists())
        self.assertTrue(result["valid"])

    def test_standard_init_flow_creates_memory_candidates_before_validate(self) -> None:
        user_id = "default"
        today = "2026-06-20"

        fitness_state.get_profile(user_id=user_id)
        fitness_state.get_daily_state(user_id=user_id, date=today)
        fitness_state.get_cycle_state(user_id=user_id)
        fitness_state.get_recall_state(user_id=user_id)
        fitness_state.aggregate_week_from_daily(user_id=user_id, week_key="2026-W25")
        result = fitness_state.validate_user_state(user_id=user_id)

        self.assertTrue((fitness_state.get_user_data_dir(user_id) / "memory_candidates.json").exists())
        self.assertTrue(result["valid"])

    def test_add_memory_candidate_works_for_new_user(self) -> None:
        memory = fitness_state.add_memory_candidate({
            "candidate_id": "manual-1",
            "type": "feedback_style",
            "key": "concise",
            "value": "short replies",
            "status": "candidate",
        }, user_id="memory_user")

        self.assertEqual(len(memory["candidates"]), 1)
        self.assertTrue((fitness_state.get_user_data_dir("memory_user") / "memory_candidates.json").exists())

    def test_preworkout_yogurt_correction_generates_candidate(self) -> None:
        candidates = fitness_memory.extract_memory_candidates("以后练前别推荐酸奶，我会胃不舒服。")

        self.assertEqual(len(candidates), 1)
        self.assertIn(candidates[0]["type"], {"food_preference", "safety_boundary"})
        self.assertEqual(candidates[0]["confidence"], "high")
        self.assertEqual(candidates[0]["status"], "candidate")
        self.assertIn(candidates[0]["sensitivity"], {"medium", "high"})

    def test_single_meal_log_does_not_generate_candidate(self) -> None:
        self.assertEqual(fitness_memory.extract_memory_candidates("今天吃了一碗牛肉面。"), [])
        self.assertEqual(fitness_memory.extract_memory_candidates("今天喝了一杯抹茶。"), [])

    def test_feedback_style_generates_candidate(self) -> None:
        candidates = fitness_memory.extract_memory_candidates("我更喜欢你给我一句话总结，不要长篇分析。")

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["type"], "feedback_style")
        self.assertEqual(candidates[0]["confidence"], "high")
        self.assertEqual(candidates[0]["sensitivity"], "low")

    def test_behavior_pattern_generates_medium_sensitivity_candidate(self) -> None:
        candidates = fitness_memory.extract_memory_candidates("我最近睡眠差的时候更容易想吃甜食。")

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["type"], "behavior_pattern")
        self.assertEqual(candidates[0]["confidence"], "medium")
        self.assertEqual(candidates[0]["sensitivity"], "medium")

    def test_handler_does_not_create_candidate_for_plain_meal_log(self) -> None:
        result = handle_fitness_message("中午吃了一碗牛肉面", user_id="meal_user")
        candidates = fitness_memory.list_memory_candidates(user_id="meal_user")

        self.assertTrue(result["handled"])
        self.assertEqual(candidates, [])

    def test_handler_records_candidate_without_exposing_json_in_reply(self) -> None:
        result = handle_fitness_message("以后练前别推荐酸奶，我会胃不舒服。", user_id="pref_user")
        candidates = fitness_memory.list_memory_candidates(user_id="pref_user")

        self.assertTrue(result["handled"])
        self.assertEqual(result["intent"], "memory_candidate_update")
        self.assertIn("避免推荐酸奶", result["reply"])
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["status"], "candidate")
        self.assertNotIn("debug", result["reply"])
        self.assertNotIn("memory_candidates", result["reply"])
        self.assertNotIn("state_changes", result["reply"])

    def test_non_fitness_unknown_does_not_write_memory_candidate(self) -> None:
        user_id = "non_fitness_user"
        result = handle_fitness_message("帮我整理明天的会议", user_id=user_id)

        self.assertFalse(result["handled"])
        self.assertEqual(result["intent"], "unknown")
        self.assertFalse(fitness_state.get_user_data_dir(user_id).exists())

    def test_memory_candidate_state_does_not_pollute_other_users_or_demo_data(self) -> None:
        fitness_state.ensure_user_state(user_id="user_a", date="2026-06-20")
        fitness_memory.extract_memory_candidates("今天吃了一碗牛肉面。")

        self.assertTrue(fitness_state.get_user_data_dir("user_a").exists())
        self.assertFalse(fitness_state.get_user_data_dir("user_b").exists())
        self.assertFalse((Path(self.tmp.name) / "demo_data").exists())


if __name__ == "__main__":
    unittest.main()
