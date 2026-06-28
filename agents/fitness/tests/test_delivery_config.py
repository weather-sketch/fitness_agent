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

import fitness_delivery_config  # noqa: E402
import fitness_state  # noqa: E402


class FitnessDeliveryConfigTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.old_data_dir = fitness_state.DATA_DIR
        fitness_state.DATA_DIR = Path(self.tmp.name) / "data"
        self.user_id = "delivery_config_user"

    def tearDown(self) -> None:
        fitness_state.DATA_DIR = self.old_data_dir
        self.tmp.cleanup()

    def test_default_config_does_not_write_file(self) -> None:
        config = fitness_delivery_config.load_delivery_config(self.user_id)

        self.assertEqual(config, {"version": 1, "channels": {}})
        self.assertFalse(fitness_delivery_config.delivery_config_path(self.user_id).exists())

    def test_configure_wechat_delivery_writes_safe_defaults(self) -> None:
        config = fitness_delivery_config.configure_wechat_delivery(
            user_id=self.user_id,
            target="user@im.wechat",
            account_id="account-123",
            enabled=True,
        )
        wechat = config["channels"]["wechat"]

        self.assertEqual(wechat["delivery_mode"], "openclaw_message")
        self.assertEqual(wechat["openclaw_channel"], "openclaw-weixin")
        self.assertEqual(wechat["target"], "user@im.wechat")
        self.assertEqual(wechat["account_id"], "account-123")
        self.assertTrue(wechat["enabled"])
        self.assertFalse(wechat["allow_real_send"])
        self.assertTrue(fitness_delivery_config.delivery_config_path(self.user_id).exists())

    def test_disable_channel_sets_enabled_false(self) -> None:
        fitness_delivery_config.configure_wechat_delivery(
            user_id=self.user_id,
            target="user@im.wechat",
            account_id="account-123",
            enabled=True,
            allow_real_send=True,
        )
        config = fitness_delivery_config.disable_channel(self.user_id, "wechat")

        self.assertFalse(config["channels"]["wechat"]["enabled"])

    def test_configure_wechat_preserves_mixed_case_target(self) -> None:
        mixed_case = "DemoUserAbC123@im.wechat"

        config = fitness_delivery_config.configure_wechat_delivery(
            user_id=self.user_id,
            target=mixed_case,
            account_id="account-123",
            enabled=True,
        )

        self.assertEqual(config["channels"]["wechat"]["target"], mixed_case)
        self.assertNotEqual(config["channels"]["wechat"]["target"], mixed_case.lower())

    def test_config_does_not_write_default_user(self) -> None:
        fitness_delivery_config.configure_wechat_delivery(
            user_id=self.user_id,
            target="user@im.wechat",
            account_id="account-123",
        )

        self.assertFalse(fitness_state.get_user_data_dir("default").exists())


if __name__ == "__main__":
    unittest.main()
