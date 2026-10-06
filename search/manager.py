"""Search manager orchestrating cascading fallback (SearXNG -> YaCy -> DuckDuckGo)."""

from pathlib import Path
from typing import List, Dict, Optional, Any
import yaml

from search.base import BaseSearchClient, SearchResult, SearchError
from search.searxng import SearXNGClient
from search.yacy import YaCyClient
from search.duckduckgo import DuckDuckGoClient
from app.text_cleaner import clean_text


class SearchManager:
    """Orchestrates cascading search across SearXNG, YaCy, and DuckDuckGo."""

    def __init__(
        self,
        config_path: Optional[Path] = None,
        clients: Optional[Dict[str, BaseSearchClient]] = None,
    ):
        base_dir = Path(__file__).resolve().parent.parent
        self.config_path = config_path or base_dir / "config" / "search.yaml"
        self.config = self._load_config()

        self.fallback_order = self.config.get("fallback_order", ["searxng", "yacy", "duckduckgo"])
        self.max_results = int(self.config.get("max_results", 5))
        self.cache_enabled = bool(self.config.get("cache_results", True))

        # Query cache: query_string -> List[SearchResult]
        self._cache: Dict[str, List[SearchResult]] = {}

        # Initialize clients or use injected clients (for testing)
        if clients is not None:
            self.clients = clients
        else:
            self.clients = self._init_clients()

    def _load_config(self) -> Dict[str, Any]:
        """Load search engine configuration from YAML."""
        if not self.config_path.exists():
            return {}
        with open(self.config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    def _init_clients(self) -> Dict[str, BaseSearchClient]:
        """Initialize search clients according to configuration."""
        timeout = float(self.config.get("request_timeout", 10.0))
        user_agent = self.config.get("user_agent", "")

        searx_cfg = self.config.get("searxng", {})
        yacy_cfg = self.config.get("yacy", {})
        ddg_cfg = self.config.get("duckduckgo", {})

        return {
            "searxng": SearXNGClient(
                base_url=searx_cfg.get("base_url", "http://localhost:8080"),
                timeout=timeout,
                user_agent=user_agent,
                categories=searx_cfg.get("categories", "general"),
                language=searx_cfg.get("language", "en"),
            ),
            "yacy": YaCyClient(
                base_url=yacy_cfg.get("base_url", "http://localhost:8090"),
                timeout=timeout,
                user_agent=user_agent,
                verify_ssl=yacy_cfg.get("verify_ssl", False),
            ),
            "duckduckgo": DuckDuckGoClient(
                endpoint=ddg_cfg.get("endpoint", "https://html.duckduckgo.com/html/"),
                timeout=timeout,
                user_agent=user_agent,
            ),
        }

    @staticmethod
    def format_software_query(raw_name: str) -> str:
        """Format and clean raw application string for optimal search retrieval."""
        cleaned = clean_text(raw_name)
        # Remove inventory prefixes (e.g. "TS-") so search engines receive meaningful product queries
        import re
        query = re.sub(r"^TS[-_ :]+", "", cleaned, flags=re.IGNORECASE).strip()
        return query

    def search(
        self,
        query: str,
        max_results: Optional[int] = None,
    ) -> List[SearchResult]:
        """Execute cascading search across configured engines.

        Order:
            SearXNG -> (if unavailable/empty) -> YaCy -> (if unavailable/empty) -> DuckDuckGo
        Stops immediately as soon as an engine provides results.
        """
        search_query = self.format_software_query(query)
        if not search_query:
            return []

        limit = max_results or self.max_results

        # 1. Check in-memory query cache
        if self.cache_enabled and search_query in self._cache:
            return self._cache[search_query]

        results: List[SearchResult] = []

        # 2. Cascading engine execution
        for engine_name in self.fallback_order:
            client = self.clients.get(engine_name)
            if not client:
                continue

            # Check if this engine is enabled in config
            engine_cfg = self.config.get(engine_name, {})
            if not engine_cfg.get("enabled", True):
                continue

            try:
                engine_results = client.search(search_query, max_results=limit)
                if engine_results:
                    results = engine_results
                    break  # Stop at first successful engine with results
            except SearchError:
                # Log/continue to next fallback engine gracefully
                continue

        # 3. Cache results
        if self.cache_enabled:
            self._cache[search_query] = results

        return results

    def clear_cache(self) -> None:
        """Clear query cache."""
        self._cache.clear()
