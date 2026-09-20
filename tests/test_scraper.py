import unittest
from agent.scraper.crawler import WebCrawler

class TestWebCrawler(unittest.TestCase):

    def setUp(self):
        self.crawler = WebCrawler()

    def test_extract_clean_text_removes_scripts_and_boilerplate(self):
        sample_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Sample Research Paper</title>
            <script>console.log("tracking script");</script>
            <style>body { color: red; }</style>
        </head>
        <body>
            <header><nav>Home | Contact | Terms</nav></header>
            <main>
                <h1>Breakthroughs in Battery Tech</h1>
                <p>This is a significant research paragraph detailing high-energy density solid-state electrolytes.</p>
                <p>Lithium metal anodes allow substantially higher voltage thresholds and thermal stability.</p>
            </main>
            <footer>Copyright 2026 Corporation. All rights reserved.</footer>
        </body>
        </html>
        """
        title, text = self.crawler._extract_clean_text(sample_html)
        self.assertEqual(title, "Sample Research Paper")
        self.assertIn("solid-state electrolytes", text)
        self.assertIn("Lithium metal anodes", text)
        self.assertNotIn("tracking script", text)
        self.assertNotIn("Home | Contact", text)
        self.assertNotIn("Copyright 2026", text)

if __name__ == "__main__":
    unittest.main()
