from __future__ import annotations

import unittest
from pathlib import Path


WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
SKILL_FILE = WORKSPACE_ROOT / "skills" / "fitness-coach" / "SKILL.md"
DISCOVERY_DOC = WORKSPACE_ROOT / "agents" / "fitness" / "docs" / "OPENCLAW_RUNTIME_DISCOVERY.md"


class FitnessSkillBindingDocsTest(unittest.TestCase):
    def test_skill_file_exists(self) -> None:
        self.assertTrue(SKILL_FILE.exists())

    def test_skill_mentions_v04_adapter_entrypoints(self) -> None:
        text = SKILL_FILE.read_text(encoding="utf-8")

        self.assertIn("handle_channel_message", text)
        self.assertIn("handle_openclaw_event", text)
        self.assertIn("handle_fitness_message", text)

    def test_skill_mentions_non_fitness_handoff(self) -> None:
        text = SKILL_FILE.read_text(encoding="utf-8").lower()

        self.assertIn("non-fitness", text)
        self.assertIn("handoff", text)

    def test_skill_does_not_claim_real_wechat_integration(self) -> None:
        text = SKILL_FILE.read_text(encoding="utf-8").lower()

        forbidden_claims = [
            "completed real wechat integration",
            "real wechat integration is complete",
            "已完成真实微信接入",
            "已完成真实 openclaw 接入",
            "已完成真实 openclaw runtime 接入",
        ]
        for claim in forbidden_claims:
            self.assertNotIn(claim, text)
        self.assertIn("do not claim real wechat integration", text)

    def test_discovery_doc_exists_and_states_current_binding_status(self) -> None:
        self.assertTrue(DISCOVERY_DOC.exists())
        text = DISCOVERY_DOC.read_text(encoding="utf-8")

        self.assertIn(
            "No real OpenClaw runtime dispatcher / WeChat SDK callback / plugin manifest was found in the current workspace.",
            text,
        )
        self.assertIn("no real runtime binding point exposed in this workspace", text)
        self.assertIn("channel message adapter", text)
        self.assertIn("OpenClaw-like event scaffold", text)
        self.assertIn("real OpenClaw runtime binding", text)
        self.assertIn("real WeChat SDK callback", text)
        self.assertIn("real message sending", text)
        self.assertIn("proactive push", text)


if __name__ == "__main__":
    unittest.main()
