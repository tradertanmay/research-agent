import unittest
import asyncio
from agent.search.web_search import WebSearchEngine
from agent.search.academic_search import AcademicSearchEngine
from agent.search.wiki_search import WikiSearchEngine

class TestSearchEngines(unittest.IsolatedAsyncioTestCase):

    async def test_academic_search_arxiv(self):
        engine = AcademicSearchEngine()
        results = await engine.search("quantum computing", max_results=3)
        self.assertIsInstance(results, list)
        if results:
            first = results[0]
            self.assertIn("quantum", (first.title + first.snippet).lower())
            self.assertTrue(first.url.startswith("http"))
            self.assertEqual(first.source, "arxiv")

    async def test_wiki_search(self):
        engine = WikiSearchEngine()
        results = await engine.search("Artificial Intelligence", max_results=2)
        self.assertIsInstance(results, list)
        if results:
            first = results[0]
            self.assertTrue(len(first.title) > 0)
            self.assertEqual(first.source, "wikipedia")

    async def test_web_search_clean_url(self):
        engine = WebSearchEngine()
        raw_url = "//duckduckgo.com/l/?uddg=https%3A%2F%2Fen.wikipedia.org%2Fwiki%2FPython&rut=..."
        clean = engine._extract_clean_url(raw_url)
        self.assertEqual(clean, "https://en.wikipedia.org/wiki/Python")

if __name__ == "__main__":
    unittest.main()
