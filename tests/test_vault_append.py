import unittest
import shutil
from pathlib import Path
from agent.storage.vault import VaultManager

class TestVaultAppend(unittest.TestCase):

    def setUp(self):
        self.test_dir = Path("./tmp_test_vault")
        self.vault = VaultManager(base_dir=self.test_dir)

    def tearDown(self):
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_save_and_append_addendum(self):
        initial_sources = [
            {"title": "Paper 1", "url": "https://arxiv.org/abs/2101.0001", "source": "arxiv", "authors": ["Alice"], "published_date": "2021-01-01", "snippet": "Initial test paper."}
        ]
        record = self.vault.save_report(
            topic="Test Topic",
            content="# Test Topic\n\nInitial findings.\n\n## References & Annotated Sources\n\n[1] [Paper 1](https://arxiv.org/abs/2101.0001) `[ARXIV]`",
            sources=initial_sources,
            model="test-model",
            report_id="test1234",
        )

        self.assertEqual(record["id"], "test1234")
        self.assertEqual(record["sources_count"], 1)

        # Append addendum
        new_sources = [
            {"title": "Paper 2", "url": "https://arxiv.org/abs/2202.0002", "source": "arxiv", "authors": ["Bob"], "published_date": "2022-02-02", "snippet": "Follow-up paper."}
        ]
        updated = self.vault.append_addendum(
            report_id="test1234",
            subtopic_title="Detailed Limitations",
            addendum_content="Here are the detailed limitations discovered during follow-up.",
            new_sources=new_sources,
        )

        self.assertIsNotNone(updated)
        self.assertEqual(updated["sources_count"], 2)
        self.assertIn("Deep Dive Addendum: Detailed Limitations", updated["content"])
        self.assertIn("Paper 2", updated["content"])
        self.assertIn("[📄 PDF]", updated["content"])

    def test_conversation_persistence(self):
        self.vault.save_conversation("conv123", [
            {"role": "user", "content": "What is X?"},
            {"role": "assistant", "content": "X is Y."},
        ])

        messages = self.vault.get_conversation("conv123")
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0]["content"], "What is X?")
        self.assertEqual(messages[1]["role"], "assistant")

if __name__ == "__main__":
    unittest.main()
