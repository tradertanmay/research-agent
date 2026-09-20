import urllib.parse
from typing import List
import httpx
from bs4 import BeautifulSoup
from agent.search.base import SearchResult, is_valid_source_url

class WebSearchEngine:
    """Free web search engine using DuckDuckGo HTML/Lite."""

    USER_AGENT = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    )

    async def search(self, query: str, max_results: int = 5) -> List[SearchResult]:
        """Search the web for a query and return top results."""
        results = []
        try:
            # 1. Try DuckDuckGo Lite first (very fast, minimal HTML)
            results = await self._search_lite(query, max_results)
            if results:
                return results
        except Exception:
            pass

        try:
            # 2. Fallback to DuckDuckGo HTML
            results = await self._search_html(query, max_results)
            if results:
                return results
        except Exception:
            pass

        return results

    async def _search_lite(self, query: str, max_results: int) -> List[SearchResult]:
        results: List[SearchResult] = []
        headers = {
            "User-Agent": self.USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Referer": "https://lite.duckduckgo.com/",
        }
        
        async with httpx.AsyncClient(timeout=12.0, follow_redirects=True) as client:
            resp = await client.post(
                "https://lite.duckduckgo.com/lite/",
                data={"q": query},
                headers=headers,
            )
            resp.raise_for_status()

            soup = BeautifulSoup(resp.text, "html.parser")
            # In DDG lite, results are structured in table rows
            link_tags = soup.find_all("a", class_="result-link")
            snippet_tags = soup.find_all("td", class_="result-snippet")

            for link_el, snippet_el in zip(link_tags[:max_results], snippet_tags[:max_results]):
                raw_href = link_el.get("href", "")
                url = self._extract_clean_url(raw_href)
                title = link_el.get_text(strip=True)
                snippet = snippet_el.get_text(strip=True)

                if url and title and not url.startswith("/") and is_valid_source_url(url, title):
                    results.append(SearchResult(
                        title=title,
                        url=url,
                        snippet=snippet,
                        source="web"
                    ))

        return results

    async def _search_html(self, query: str, max_results: int) -> List[SearchResult]:
        results: List[SearchResult] = []
        headers = {
            "User-Agent": self.USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

        async with httpx.AsyncClient(timeout=12.0, follow_redirects=True) as client:
            resp = await client.post(
                "https://html.duckduckgo.com/html/",
                data={"q": query},
                headers=headers,
            )
            resp.raise_for_status()

            soup = BeautifulSoup(resp.text, "html.parser")
            items = soup.find_all("div", class_="result")

            for item in items:
                title_tag = item.find("a", class_="result__url") or item.find("a", class_="result__a")
                snippet_tag = item.find("a", class_="result__snippet") or item.find("div", class_="result__snippet")

                if not title_tag:
                    continue

                raw_href = title_tag.get("href", "")
                url = self._extract_clean_url(raw_href)
                title = title_tag.get_text(strip=True)
                snippet = snippet_tag.get_text(strip=True) if snippet_tag else ""

                if url and title and not url.startswith("/") and is_valid_source_url(url, title):
                    results.append(SearchResult(
                        title=title,
                        url=url,
                        snippet=snippet,
                        source="web"
                    ))
                    if len(results) >= max_results:
                        break

        return results

    def _extract_clean_url(self, raw_url: str) -> str:
        """Extract clean target URL from DuckDuckGo redirect link."""
        if not raw_url:
            return ""
        if "uddg=" in raw_url:
            try:
                parsed = urllib.parse.urlparse(raw_url)
                qs = urllib.parse.parse_qs(parsed.query)
                if "uddg" in qs:
                    return qs["uddg"][0]
            except Exception:
                pass
        return raw_url
