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

import fitness_scheduler_config  # noqa: E402
import fitness_state  # noqa: E402


class FitnessSchedulerConfigTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.old_data_dir = fitness_state.DATA_DIR
        fitness_state.DATA_DIR = Path(self.tmp.name) / "data"
        self.user_id = "scheduler_config_user"

    def tearDown(self) -> None:
        fitness_state.DATA_DIR = self.old_data_dir
        self.tmp.cleanup()

    def test_default_scheduler_config_does_not_write_file(self) -> None:
        config = fitness_scheduler_config.load_scheduler_config(self.user_id)

        self.assertFalse(config["enabled"])
        self.assertFalse(config["send_enabled"])
        self.assertFalse(config["confirm_send"])
        self.assertEqual(config["schedule"]["preferred_hours"], [9, 18, 21])
        self.assertFalse(fitness_scheduler_config.scheduler_config_path(self.user_id).exists())

    def test_configure_and_disable_scheduler(self) -> None:
        config = fitness_scheduler_config.configure_scheduler(
            user_id=self.user_id,
            enabled=True,
            channel="wechat",
            delivery_mode="openclaw_message",
            preferred_hours=[21, 9],
            timezone="Asia/Shanghai",
            max_runs_per_day=2,
        )

        self.assertTrue(config["enabled"])
        self.assertEqual(config["schedule"]["preferred_hours"], [9, 21])
        self.assertEqual(config["schedule"]["max_runs_per_day"], 2)

        disabled = fitness_scheduler_config.disable_scheduler(self.user_id)
        self.assertFalse(disabled["enabled"])

    def test_enable_real_send_requires_confirm(self) -> None:
        with self.assertRaises(ValueError):
            fitness_scheduler_config.set_real_send(user_id=self.user_id, enabled=True, confirm=False)

        config = fitness_scheduler_config.set_real_send(user_id=self.user_id, enabled=True, confirm=True)
        self.assertTrue(config["send_enabled"])
        self.assertTrue(config["confirm_send"])

    def test_config_does_not_write_default_user(self) -> None:
        fitness_scheduler_config.configure_scheduler(user_id=self.user_id, enabled=True)

        self.assertFalse(fitness_state.get_user_data_dir("default").exists())


if __name__ == "__main__":
    unittest.main()
