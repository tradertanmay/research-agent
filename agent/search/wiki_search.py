import urllib.parse
from typing import List
import httpx
from bs4 import BeautifulSoup
from agent.search.base import SearchResult, is_valid_source_url

class WikiSearchEngine:
    """Encyclopedic background search using Wikipedia API."""

    SEARCH_API = "https://en.wikipedia.org/w/api.php"
    SUMMARY_API = "https://en.wikipedia.org/api/rest_v1/page/summary/"

    async def search(self, query: str, max_results: int = 3) -> List[SearchResult]:
        """Search Wikipedia articles and fetch executive extracts."""
        results: List[SearchResult] = []
        params = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "format": "json",
            "srlimit": max_results,
        }
        headers = {
            "User-Agent": "ResearchAgent/1.0 (academic-research-bot)"
        }

        try:
            async with httpx.AsyncClient(timeout=10.0, headers=headers) as client:
                resp = await client.get(self.SEARCH_API, params=params)
                if resp.status_code != 200:
                    return results

                data = resp.json()
                search_items = data.get("query", {}).get("search", [])

                for item in search_items:
                    title = item.get("title", "")
                    page_url = f"https://en.wikipedia.org/wiki/{urllib.parse.quote(title.replace(' ', '_'))}"

                    if not is_valid_source_url(page_url, title):
                        continue

                    clean_snippet = BeautifulSoup(item.get("snippet", ""), "html.parser").get_text()

                    # Try fetching full summary extract if possible
                    extract = clean_snippet
                    try:
                        sum_resp = await client.get(f"{self.SUMMARY_API}{urllib.parse.quote(title)}")
                        if sum_resp.status_code == 200:
                            sum_data = sum_resp.json()
                            extract = sum_data.get("extract", clean_snippet)
                    except Exception:
                        pass

                    results.append(SearchResult(
                        title=title,
                        url=page_url,
                        snippet=extract[:500] + ("..." if len(extract) > 500 else ""),
                        source="wikipedia"
                    ))
        except Exception:
            pass

        return results
