from __future__ import annotations

import copy
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


class FitnessMemoryCandidateDedupTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.old_data_dir = fitness_state.DATA_DIR
        fitness_state.DATA_DIR = Path(self.tmp.name) / "data"

    def tearDown(self) -> None:
        fitness_state.DATA_DIR = self.old_data_dir
        self.tmp.cleanup()

    def _yogurt_candidate(self) -> dict:
        return fitness_memory.extract_memory_candidates("以后练前别推荐酸奶，我会胃不舒服。")[0]

    def test_first_add_creates_candidate(self) -> None:
        result = fitness_state.add_memory_candidate(self._yogurt_candidate(), user_id="default")

        self.assertTrue(result["created"])
        self.assertFalse(result["merged"])
        self.assertEqual(len(result["candidates"]), 1)

    def test_second_same_type_and_key_merges_candidate(self) -> None:
        first = fitness_state.add_memory_candidate(self._yogurt_candidate(), user_id="default")
        second = fitness_state.add_memory_candidate(self._yogurt_candidate(), user_id="default")
        candidates = fitness_memory.list_memory_candidates(user_id="default")

        self.assertTrue(first["created"])
        self.assertTrue(second["merged"])
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["candidate_id"], first["candidate_id"])
        self.assertEqual(candidates[0]["evidence_count"], 2)

    def test_duplicate_evidence_text_is_not_appended_twice(self) -> None:
        fitness_state.add_memory_candidate(self._yogurt_candidate(), user_id="default")
        fitness_state.add_memory_candidate(self._yogurt_candidate(), user_id="default")
        candidate = fitness_memory.list_memory_candidates(user_id="default")[0]

        self.assertEqual(candidate["evidence_count"], 2)
        self.assertEqual(candidate["evidence_examples"], ["以后练前别推荐酸奶，我会胃不舒服。"])

    def test_different_key_creates_new_candidate(self) -> None:
        first = self._yogurt_candidate()
        second = copy.deepcopy(first)
        second["candidate_id"] = "manual-different-key"
        second["key"] = "avoid_milk_pre_workout"

        fitness_state.add_memory_candidate(first, user_id="default")
        result = fitness_state.add_memory_candidate(second, user_id="default")

        self.assertTrue(result["created"])
        self.assertEqual(len(fitness_memory.list_memory_candidates(user_id="default")), 2)

    def test_same_key_different_type_creates_new_candidate(self) -> None:
        first = self._yogurt_candidate()
        second = copy.deepcopy(first)
        second["candidate_id"] = "manual-different-type"
        second["type"] = "food_preference"

        fitness_state.add_memory_candidate(first, user_id="default")
        result = fitness_state.add_memory_candidate(second, user_id="default")

        self.assertTrue(result["created"])
        self.assertEqual(len(fitness_memory.list_memory_candidates(user_id="default")), 2)

    def test_rejected_candidate_does_not_merge(self) -> None:
        first = fitness_state.add_memory_candidate(self._yogurt_candidate(), user_id="default")
        fitness_memory.reject_memory_candidate("default", first["candidate_id"], review_note="not stable")

        result = fitness_state.add_memory_candidate(self._yogurt_candidate(), user_id="default")
        candidates = fitness_memory.list_memory_candidates(user_id="default")

        self.assertTrue(result["created"])
        self.assertEqual(len(candidates), 2)
        self.assertEqual([candidate["status"] for candidate in candidates], ["rejected", "candidate"])

    def test_approved_candidate_merges_without_status_downgrade(self) -> None:
        first = fitness_state.add_memory_candidate(self._yogurt_candidate(), user_id="default")
        fitness_memory.approve_memory_candidate("default", first["candidate_id"], review_note="approved")

        result = fitness_state.add_memory_candidate(self._yogurt_candidate(), user_id="default")
        candidate = fitness_memory.list_memory_candidates(user_id="default")[0]

        self.assertTrue(result["merged"])
        self.assertEqual(candidate["status"], "approved")
        self.assertEqual(candidate["evidence_count"], 2)

    def test_confidence_keeps_higher_value(self) -> None:
        first = self._yogurt_candidate()
        first["confidence"] = "low"
        second = self._yogurt_candidate()
        second["confidence"] = "high"

        fitness_state.add_memory_candidate(first, user_id="default")
        fitness_state.add_memory_candidate(second, user_id="default")
        candidate = fitness_memory.list_memory_candidates(user_id="default")[0]

        self.assertEqual(candidate["confidence"], "high")

    def test_sensitivity_keeps_higher_value(self) -> None:
        first = self._yogurt_candidate()
        first["sensitivity"] = "low"
        second = self._yogurt_candidate()
        second["sensitivity"] = "high"

        fitness_state.add_memory_candidate(first, user_id="default")
        fitness_state.add_memory_candidate(second, user_id="default")
        candidate = fitness_memory.list_memory_candidates(user_id="default")[0]

        self.assertEqual(candidate["sensitivity"], "high")

    def test_handler_repeated_preference_merges_candidate(self) -> None:
        first = handle_fitness_message("以后练前别推荐酸奶，我会胃不舒服。", user_id="handler_user")
        second = handle_fitness_message("以后练前别推荐酸奶，我会胃不舒服。", user_id="handler_user")
        candidates = fitness_memory.list_memory_candidates(user_id="handler_user")

        self.assertTrue(first["handled"])
        self.assertTrue(second["handled"])
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["evidence_count"], 2)
        self.assertEqual(first["debug"]["memory_candidates_added"], 1)
        self.assertEqual(first["debug"]["memory_candidates_merged"], 0)
        self.assertEqual(second["debug"]["memory_candidates_added"], 0)
        self.assertEqual(second["debug"]["memory_candidates_merged"], 1)

    def test_plain_meal_log_still_does_not_generate_candidate(self) -> None:
        result = handle_fitness_message("今天吃了一碗牛肉面", user_id="meal_user")
        candidates = fitness_memory.list_memory_candidates(user_id="meal_user")

        self.assertTrue(result["handled"])
        self.assertEqual(candidates, [])

    def test_non_fitness_fallback_does_not_write_candidate(self) -> None:
        result = handle_fitness_message("帮我整理明天的会议", user_id="fallback_user")

        self.assertFalse(result["handled"])
        self.assertFalse(fitness_state.get_user_data_dir("fallback_user").exists())

    def test_temp_state_does_not_pollute_real_data(self) -> None:
        fitness_state.add_memory_candidate(self._yogurt_candidate(), user_id="temp_user")

        self.assertTrue((fitness_state.get_user_data_dir("temp_user") / "memory_candidates.json").exists())
        self.assertFalse((Path(self.tmp.name) / "demo_data").exists())


if __name__ == "__main__":
    unittest.main()
