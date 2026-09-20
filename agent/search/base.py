import urllib.parse
from dataclasses import dataclass
from typing import Optional, List

# Domains or URL patterns that should never be treated as research sources
BLOCKED_DOMAINS = {
    "google.com", "www.google.com", "scholar.google.com", "bing.com", "www.bing.com",
    "duckduckgo.com", "search.yahoo.com", "yahoo.com", "baidu.com", "yandex.com"
}

BLOCKED_URL_SUBSTRINGS = [
    "scholar.google.com",
    "duckduckgo.com",
    "google.com/search",
    "bing.com/search",
    "/Reliability_of_Wikipedia",
    "/German_Wikipedia",
    "/Wikipedia:",
    "/Special:",
    "/Main_Page",
    "localhost",
    "127.0.0.1",
    "%60",
    "`"
]

def is_valid_source_url(url: str, title: str = "") -> bool:
    """Validate that a URL is a real article or paper and not a search engine landing page."""
    if not url or not url.startswith("http"):
        return False

    url_lower = url.lower()
    title_lower = title.lower()

    for pattern in BLOCKED_URL_SUBSTRINGS:
        if pattern.lower() in url_lower:
            return False

    try:
        parsed = urllib.parse.urlparse(url)
        netloc = parsed.netloc.lower()
        if netloc in BLOCKED_DOMAINS:
            return False
        # If path is empty or just "/" on a major portal
        if parsed.path in ("", "/"):
            return False
    except Exception:
        return False

    if title_lower in ("google scholar", "google", "bing", "duckduckgo", "wikipedia"):
        return False

    return True

@dataclass
class SearchResult:
    """Represents a discovered research source."""
    title: str
    url: str
    snippet: str
    source: str  # 'web', 'arxiv', 'wikipedia'
    published_date: Optional[str] = None
    authors: Optional[List[str]] = None
    score: float = 0.0

    def to_dict(self):
        return {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
            "source": self.source,
            "published_date": self.published_date,
            "authors": self.authors,
            "score": self.score,
        }
