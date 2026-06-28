from __future__ import annotations

import copy
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
for path in (ROOT, TOOLS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import fitness_state  # noqa: E402


class FitnessStateValidationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.old_data_dir = fitness_state.DATA_DIR
        fitness_state.DATA_DIR = Path(self.tmp.name) / "data"

    def tearDown(self) -> None:
        fitness_state.DATA_DIR = self.old_data_dir
        self.tmp.cleanup()

    def _seed_minimal_user(self) -> None:
        fitness_state.get_profile()
        fitness_state.get_recall_state()
        fitness_state.get_memory_candidates()
        fitness_state.ensure_daily_state(date="2026-06-20")
        fitness_state.get_cycle_state(week="current_week")

    def test_validate_accepts_valid_state(self) -> None:
        self._seed_minimal_user()
        result = fitness_state.validate_user_state()
        self.assertTrue(result["valid"])
        self.assertEqual(result["errors"], [])

    def test_validate_finds_corrupted_json(self) -> None:
        self._seed_minimal_user()
        path = fitness_state.get_user_data_dir() / "profile.json"
        path.write_text("{broken", encoding="utf-8")
        result = fitness_state.validate_user_state()
        self.assertFalse(result["valid"])
        self.assertTrue(any("Invalid JSON" in error for error in result["errors"]))

    def test_validate_finds_missing_required_file(self) -> None:
        self._seed_minimal_user()
        (fitness_state.get_user_data_dir() / "profile.json").unlink()
        result = fitness_state.validate_user_state()
        self.assertFalse(result["valid"])
        self.assertTrue(any("Missing required file" in error for error in result["errors"]))

    def test_save_json_refuses_to_overwrite_corrupted_file(self) -> None:
        target = fitness_state.DATA_DIR / "users" / "default" / "profile.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("{broken", encoding="utf-8")
        with self.assertRaises(fitness_state.FitnessStateError):
            fitness_state.save_json(target, copy.deepcopy(fitness_state.DEFAULTS["profile.json"]))
        self.assertEqual(target.read_text(encoding="utf-8"), "{broken")
        self.assertTrue(list(target.parent.glob("profile.json.corrupted-*.bak")))

    def test_save_json_atomic_write_does_not_leave_half_written_target(self) -> None:
        target = fitness_state.DATA_DIR / "users" / "default" / "profile.json"
        fitness_state.save_json(target, {"version": 1, "ok": True})
        original = target.read_text(encoding="utf-8")
        with mock.patch("json.dump", side_effect=TypeError("not serializable")):
            with self.assertRaises(fitness_state.FitnessStateError):
                fitness_state.save_json(target, {"version": 2})
        self.assertEqual(target.read_text(encoding="utf-8"), original)
        self.assertEqual(list(target.parent.glob(f".{target.name}.*.tmp")), [])


if __name__ == "__main__":
    unittest.main()
