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


class FitnessStateBackupRestoreTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.old_data_dir = fitness_state.DATA_DIR
        fitness_state.DATA_DIR = Path(self.tmp.name) / "data"

    def tearDown(self) -> None:
        fitness_state.DATA_DIR = self.old_data_dir
        self.tmp.cleanup()

    def _seed_user(self, user_id: str = "default") -> None:
        fitness_state.get_profile(user_id=user_id)
        fitness_state.get_recall_state(user_id=user_id)
        fitness_state.get_memory_candidates(user_id=user_id)
        fitness_state.update_daily_state({
            "day_type": "training_day",
            "training": {"type": "glutes", "status": "completed"},
            "workouts": [{"training_type": "glutes", "status": "completed"}],
        }, user_id=user_id, date="2026-06-20")
        fitness_state.update_cycle_state({"week_key": "2026-W25"}, user_id=user_id, week="current_week")
        fitness_state.update_cycle_state({"week_key": "2026-W25"}, user_id=user_id, week="2026-W25")

    def test_create_backup_creates_directory(self) -> None:
        self._seed_user()
        result = fitness_state.create_user_backup(label="before-routing")
        self.assertTrue(Path(result["path"]).exists())
        self.assertGreaterEqual(result["file_count"], 6)
        self.assertIn("backup_id", result)

    def test_backup_preserves_user_state_structure(self) -> None:
        self._seed_user()
        result = fitness_state.create_user_backup()
        root = Path(result["path"])
        self.assertTrue((root / "profile.json").exists())
        self.assertTrue((root / "recall_state.json").exists())
        self.assertTrue((root / "memory_candidates.json").exists())
        self.assertTrue((root / "daily" / "2026-06-20.json").exists())
        self.assertTrue((root / "cycle" / "current_week.json").exists())
        self.assertTrue((root / "cycle" / "2026-W25.json").exists())

    def test_list_backups_returns_newest_first(self) -> None:
        self._seed_user()
        first = fitness_state.create_user_backup(label="a")
        second = fitness_state.create_user_backup(label="b")
        backups = fitness_state.list_user_backups()
        self.assertEqual(backups[0]["backup_id"], second["backup_id"])
        self.assertEqual(backups[1]["backup_id"], first["backup_id"])

    def test_restore_dry_run_does_not_change_state(self) -> None:
        self._seed_user()
        backup = fitness_state.create_user_backup()
        fitness_state.update_daily_state({"day_type": "rest_day"}, date="2026-06-20")
        result = fitness_state.restore_user_backup(backup_id=backup["backup_id"], dry_run=True)
        state = fitness_state.get_daily_state(date="2026-06-20")
        self.assertTrue(result["ok"])
        self.assertTrue(result["dry_run"])
        self.assertEqual(state["day_type"], "rest_day")

    def test_restore_apply_restores_old_state(self) -> None:
        self._seed_user()
        backup = fitness_state.create_user_backup()
        fitness_state.update_daily_state({"day_type": "rest_day"}, date="2026-06-20")
        result = fitness_state.restore_user_backup(backup_id=backup["backup_id"], dry_run=False)
        state = fitness_state.get_daily_state(date="2026-06-20")
        self.assertTrue(result["ok"])
        self.assertFalse(result["dry_run"])
        self.assertEqual(state["day_type"], "training_day")

    def test_restore_apply_creates_pre_restore_backup(self) -> None:
        self._seed_user()
        backup = fitness_state.create_user_backup(label="old")
        fitness_state.update_daily_state({"day_type": "rest_day"}, date="2026-06-20")
        before = fitness_state.list_user_backups()
        result = fitness_state.restore_user_backup(backup_id=backup["backup_id"], dry_run=False)
        after = fitness_state.list_user_backups()
        self.assertIsNotNone(result["pre_restore_backup"])
        self.assertGreater(len(after), len(before))
        self.assertIn("pre-restore", result["pre_restore_backup"]["backup_id"])

    def test_restore_rejects_corrupted_backup(self) -> None:
        self._seed_user()
        backup = fitness_state.create_user_backup()
        daily = Path(backup["path"]) / "daily" / "2026-06-20.json"
        daily.write_text("{broken", encoding="utf-8")
        result = fitness_state.restore_user_backup(backup_id=backup["backup_id"], dry_run=False)
        self.assertFalse(result["ok"])
        self.assertIn("Invalid JSON", result["errors"][0])

    def test_demo_data_backup_does_not_pollute_real_data_or_backups(self) -> None:
        demo_data = Path(self.tmp.name) / "demo_data"
        real_data = Path(self.tmp.name) / "data"
        fitness_state.DATA_DIR = demo_data
        self._seed_user()
        fitness_state.create_user_backup(label="demo")
        self.assertFalse((real_data / "users").exists())
        self.assertFalse((real_data / "data_backups").exists())


if __name__ == "__main__":
    unittest.main()
