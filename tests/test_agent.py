import unittest
import tempfile
from pathlib import Path
from agent.core.planner import ResearchPlanner
from agent.llm.base import BaseLLMClient
from agent.storage.vault import VaultManager

class DummyLLM(BaseLLMClient):
    def __init__(self):
        super().__init__("dummy")

    @property
    def provider(self) -> str:
        return "dummy"

    async def generate(self, prompt: str, system=None, temperature=0.7, max_tokens=4096):
        return "dummy response"

    async def generate_stream(self, prompt: str, system=None, temperature=0.7, max_tokens=4096):
        yield "dummy"

    async def is_available(self):
        return True

class TestAgentComponents(unittest.TestCase):

    def test_planner_fallback(self):
        planner = ResearchPlanner(DummyLLM())
        plan = planner._build_fallback_plan("Solid State Batteries", "standard")
        self.assertEqual(plan.topic, "Solid State Batteries")
        self.assertTrue(len(plan.sub_questions) >= 3)
        self.assertTrue(len(plan.web_queries) >= 2)

    def test_vault_save_and_retrieve(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = VaultManager(base_dir=Path(tmpdir))
            record = vault.save_report(
                topic="Test Quantum Topic",
                content="# Report on Quantum\n\nContent here.",
                sources=[{"title": "Source 1", "url": "https://example.com"}],
                model="test-model",
            )
            self.assertTrue(Path(record["filepath"]).exists())

            retrieved = vault.get_report(record["id"])
            self.assertIsNotNone(retrieved)
            self.assertIn("Report on Quantum", retrieved["content"])

            html = vault.export_html(record["id"])
            self.assertIsNotNone(html)
            self.assertIn("Test Quantum Topic", html)

if __name__ == "__main__":
    unittest.main()
