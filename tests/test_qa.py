import unittest
from unittest.mock import AsyncMock, patch
from agent.core.report_qa import ReportQAEngine

class TestReportQA(unittest.IsolatedAsyncioTestCase):

    async def test_ask_stream_mock(self):
        engine = ReportQAEngine(model_id="test-model")
        
        async def mock_stream(*args, **kwargs):
            yield "Based on the report, "
            yield "the key bottleneck is memory bandwidth [1]."

        engine.llm.generate_stream = mock_stream

        chunks = []
        async for chunk in engine.ask_stream(
            report_topic="Solid-State Batteries",
            report_content="Solid-state batteries face ionic conductivity challenges.",
            sources=[{"title": "Battery Advances", "url": "https://example.com/bat", "source": "web", "snippet": "Solid electrolyte"}],
            question="What is the bottleneck?",
        ):
            chunks.append(chunk)

        full_answer = "".join(chunks)
        self.assertIn("bottleneck", full_answer)
        self.assertIn("[1]", full_answer)

if __name__ == "__main__":
    unittest.main()
