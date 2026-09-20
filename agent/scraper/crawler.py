import asyncio
import re
from typing import Optional, List, Dict
import httpx
from bs4 import BeautifulSoup

class CrawledDocument:
    """Represents the scraped and cleaned content of a web page."""
    def __init__(self, url: str, title: str, text: str, success: bool = True, error: Optional[str] = None):
        self.url = url
        self.title = title
        self.text = text
        self.success = success
        self.error = error

    def to_dict(self):
        return {
            "url": self.url,
            "title": self.title,
            "text": self.text,
            "success": self.success,
            "error": self.error,
        }

class WebCrawler:
    """Asynchronous web page reader and clean text extractor."""

    USER_AGENT = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    )

    # Tags to discard
    DISCARD_TAGS = [
        "script", "style", "nav", "footer", "header", "aside", 
        "noscript", "form", "svg", "iframe"
    ]

    def __init__(self, max_concurrent: int = 5, timeout: float = 12.0):
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.timeout = timeout

    async def fetch_page(self, url: str) -> CrawledDocument:
        """Fetch and extract clean readable text from a single webpage."""
        async with self.semaphore:
            headers = {
                "User-Agent": self.USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
            }
            try:
                async with httpx.AsyncClient(
                    timeout=self.timeout,
                    follow_redirects=True,
                    verify=False,  # Allow sites with self-signed or quirky certs
                ) as client:
                    resp = await client.get(url, headers=headers)
                    if resp.status_code != 200:
                        return CrawledDocument(
                            url=url,
                            title="",
                            text="",
                            success=False,
                            error=f"HTTP {resp.status_code}",
                        )

                    # Check content type
                    content_type = resp.headers.get("content-type", "").lower()
                    if "text/html" not in content_type and "application/xhtml" not in content_type:
                        return CrawledDocument(
                            url=url,
                            title="",
                            text="",
                            success=False,
                            error="Non-HTML content type",
                        )

                    title, text = self._extract_clean_text(resp.text)
                    return CrawledDocument(
                        url=url,
                        title=title,
                        text=text,
                        success=True,
                    )
            except Exception as e:
                return CrawledDocument(
                    url=url,
                    title="",
                    text="",
                    success=False,
                    error=str(e),
                )

    async def fetch_all(self, urls: List[str]) -> List[CrawledDocument]:
        """Fetch multiple URLs concurrently with error handling."""
        tasks = [self.fetch_page(url) for url in urls]
        return await asyncio.gather(*tasks, return_exceptions=False)

    def _extract_clean_text(self, html: str, max_chars: int = 5000) -> tuple[str, str]:
        """Strip boilerplate and extract meaningful article text."""
        soup = BeautifulSoup(html, "html.parser")

        # 1. Extract title
        title_el = soup.find("title")
        title = title_el.get_text(strip=True) if title_el else ""
        if not title:
            h1_el = soup.find("h1")
            title = h1_el.get_text(strip=True) if h1_el else "Web Page"

        # 2. Decompose useless tags
        for tag in self.DISCARD_TAGS:
            for el in soup.find_all(tag):
                el.decompose()

        # 3. Target main article container if available
        main_content = (
            soup.find("article")
            or soup.find("main")
            or soup.find(class_=re.compile(r"content|article|body|entry", re.I))
            or soup.body
            or soup
        )

        # 4. Extract headings, paragraphs, and list items
        text_blocks = []
        for element in main_content.find_all(["p", "h1", "h2", "h3", "h4", "li"]):
            block_text = element.get_text(strip=True)
            # Skip very short blocks (nav snippets, copyright bits)
            if len(block_text) > 25:
                text_blocks.append(block_text)

        joined_text = "\n\n".join(text_blocks)
        cleaned = re.sub(r"\n{3,}", "\n\n", joined_text)

        # Truncate if exceeds limit
        if len(cleaned) > max_chars:
            cleaned = cleaned[:max_chars] + "\n\n[Content truncated for analysis...]"

        return title, cleaned
