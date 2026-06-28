from __future__ import annotations

import unittest
from pathlib import Path


WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
GUIDE = WORKSPACE_ROOT / "agents" / "fitness" / "docs" / "WECHAT_MANUAL_TEST_GUIDE.md"


class FitnessWeChatManualTestDocsTest(unittest.TestCase):
    def test_wechat_manual_test_guide_exists(self) -> None:
        self.assertTrue(GUIDE.exists())

    def test_guide_contains_required_manual_test_messages(self) -> None:
        text = GUIDE.read_text(encoding="utf-8")

        self.assertIn("今天晚上练臀，怎么吃？", text)
        self.assertIn("我今天吃爆了，不想记了", text)
        self.assertIn("以后练前别推荐酸奶，我会胃不舒服", text)
        self.assertIn("/recall on", text)
        self.assertIn("/recall status", text)
        self.assertIn("帮我把明天的会议整理一下", text)

    def test_guide_contains_fitness_not_triggered_section(self) -> None:
        text = GUIDE.read_text(encoding="utf-8")

        self.assertIn("If Fitness Does Not Trigger", text)
        self.assertIn("如果没有触发 Fitness", text)
        self.assertIn("用户原始输入", text)
        self.assertIn("主 Agent 原始回复", text)

    def test_guide_does_not_claim_real_wechat_sdk_integration(self) -> None:
        text = GUIDE.read_text(encoding="utf-8").lower()

        forbidden_claims = [
            "real wechat sdk integration is complete",
            "completed real wechat sdk integration",
            "已完成真实微信 sdk 接入",
            "已完成真实微信接入",
        ]
        for claim in forbidden_claims:
            self.assertNotIn(claim, text)
        self.assertIn("does not expose a real wechat runtime binding point", text)


if __name__ == "__main__":
    unittest.main()
