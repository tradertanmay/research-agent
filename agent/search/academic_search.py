import asyncio
import urllib.parse
import urllib.request
import re
import xml.etree.ElementTree as ET
from typing import List
from agent.search.base import SearchResult

class AcademicSearchEngine:
    """Academic research paper search using the arXiv API via resilient urllib client."""

    ARXIV_API_URL = "https://export.arxiv.org/api/query"
    USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko)"

    async def search(self, query: str, max_results: int = 5) -> List[SearchResult]:
        """Search arXiv for preprints and scientific papers asynchronously."""
        return await asyncio.to_thread(self._sync_search, query, max_results)

    def _sync_search(self, query: str, max_results: int) -> List[SearchResult]:
        results: List[SearchResult] = []
        
        # Clean and extract salient keywords
        words = [
            w for w in re.sub(r"[^a-zA-Z0-9\s]", "", query).split()
            if len(w) > 2 and w.lower() not in {"what", "how", "why", "the", "and", "for", "with", "into"}
        ]
        
        # Prefer the most technical terms (top 2 keywords)
        clean_keyword = urllib.parse.quote(" ".join(words[:2]) if words else query)
        url = f"{self.ARXIV_API_URL}?search_query=all:{clean_keyword}&start=0&max_results={max_results}&sortBy=relevance&sortOrder=descending"

        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": self.USER_AGENT, "Accept": "*/*"}
            )
            with urllib.request.urlopen(req, timeout=12.0) as resp:
                if resp.status != 200:
                    return results

                text = resp.read().decode("utf-8", errors="ignore")
                root = ET.fromstring(text)
                ns = {"atom": "http://www.w3.org/2005/Atom"}
                entries = root.findall("atom:entry", ns)

                for entry in entries:
                    title_el = entry.find("atom:title", ns)
                    summary_el = entry.find("atom:summary", ns)
                    id_el = entry.find("atom:id", ns)
                    published_el = entry.find("atom:published", ns)
                    author_els = entry.findall("atom:author", ns)

                    title = title_el.text.strip().replace("\n", " ") if title_el is not None and title_el.text else "Untitled"
                    summary = summary_el.text.strip().replace("\n", " ") if summary_el is not None and summary_el.text else ""
                    link_url = id_el.text.strip() if id_el is not None and id_el.text else ""
                    if link_url.startswith("http://"):
                        link_url = "https://" + link_url[len("http://"):]
                    published = published_el.text.strip()[:10] if published_el is not None and published_el.text else None
                    
                    authors = []
                    for a in author_els:
                        name_el = a.find("atom:name", ns)
                        if name_el is not None and name_el.text:
                            authors.append(name_el.text.strip())

                    if link_url and title and title != "Untitled":
                        results.append(SearchResult(
                            title=title,
                            url=link_url,
                            snippet=summary[:500] + ("..." if len(summary) > 500 else ""),
                            source="arxiv",
                            published_date=published,
                            authors=authors[:5],
                        ))
        except Exception:
            pass

        return results
