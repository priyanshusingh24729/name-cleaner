"""Base classes and data models for search engine clients."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Any


class SearchError(Exception):
    """Base exception for search operations."""
    pass


class SearchTimeoutError(SearchError):
    """Raised when a search request times out."""
    pass


class SearchEngineUnavailableError(SearchError):
    """Raised when a search engine endpoint cannot be reached or returns an error status."""
    pass


@dataclass
class SearchResult:
    """Represents a single organic search result."""

    title: str
    url: str
    snippet: str
    engine: str
    score: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary for serialization."""
        return {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
            "engine": self.engine,
            "score": round(self.score, 4),
        }

    def __str__(self) -> str:
        return f"[{self.engine.upper()}] {self.title} -> {self.url}"


class BaseSearchClient(ABC):
    """Abstract base class for all search engine clients."""

    def __init__(self, name: str, timeout: float = 10.0, user_agent: str = ""):
        self.name = name
        self.timeout = timeout
        self.user_agent = user_agent

    @abstractmethod
    def search(self, query: str, max_results: int = 5) -> List[SearchResult]:
        """Execute search query and return parsed results."""
        raise NotImplementedError
