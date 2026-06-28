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


class FitnessMemoryCandidateReviewTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.old_data_dir = fitness_state.DATA_DIR
        fitness_state.DATA_DIR = Path(self.tmp.name) / "data"
        candidates = fitness_memory.extract_memory_candidates("我更喜欢你给我一句话总结，不要长篇分析。")
        self.candidate = candidates[0]
        fitness_state.add_memory_candidate(self.candidate, user_id="default")

    def tearDown(self) -> None:
        fitness_state.DATA_DIR = self.old_data_dir
        self.tmp.cleanup()

    def test_list_memory_candidates_filters_by_status(self) -> None:
        all_candidates = fitness_memory.list_memory_candidates(user_id="default")
        candidate_only = fitness_memory.list_memory_candidates(user_id="default", status="candidate")

        self.assertEqual(len(all_candidates), 1)
        self.assertEqual(len(candidate_only), 1)
        self.assertEqual(candidate_only[0]["candidate_id"], self.candidate["candidate_id"])

    def test_approve_memory_candidate_updates_status(self) -> None:
        reviewed = fitness_memory.approve_memory_candidate(
            "default",
            self.candidate["candidate_id"],
            review_note="stable preference",
        )

        self.assertEqual(reviewed["status"], "approved")
        self.assertEqual(reviewed["review_note"], "stable preference")
        self.assertEqual(reviewed["applied_to"], "profile.preferences.feedback_style")

    def test_reject_memory_candidate_updates_status(self) -> None:
        reviewed = fitness_memory.reject_memory_candidate(
            "default",
            self.candidate["candidate_id"],
            review_note="not stable",
        )

        self.assertEqual(reviewed["status"], "rejected")
        self.assertEqual(reviewed["review_note"], "not stable")

    def test_archive_memory_candidate_updates_status(self) -> None:
        reviewed = fitness_memory.archive_memory_candidate("default", self.candidate["candidate_id"])

        self.assertEqual(reviewed["status"], "archived")

    def test_invalid_review_action_raises(self) -> None:
        with self.assertRaises(fitness_state.FitnessStateError):
            fitness_memory.review_memory_candidate("default", self.candidate["candidate_id"], "publish")

    def test_missing_candidate_raises(self) -> None:
        with self.assertRaises(fitness_state.FitnessStateError):
            fitness_memory.approve_memory_candidate("default", "missing-id")


if __name__ == "__main__":
    unittest.main()
