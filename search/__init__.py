"""Multi-engine search package (SearXNG, YaCy, DuckDuckGo)."""

from search.base import (
    SearchResult,
    BaseSearchClient,
    SearchError,
    SearchTimeoutError,
    SearchEngineUnavailableError,
)
from search.searxng import SearXNGClient
from search.yacy import YaCyClient
from search.duckduckgo import DuckDuckGoClient
from search.manager import SearchManager

__all__ = [
    "SearchResult",
    "BaseSearchClient",
    "SearchError",
    "SearchTimeoutError",
    "SearchEngineUnavailableError",
    "SearXNGClient",
    "YaCyClient",
    "DuckDuckGoClient",
    "SearchManager",
]
