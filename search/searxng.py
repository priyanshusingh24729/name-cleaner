"""SearXNG JSON search client."""

from typing import List, Optional
import httpx

from search.base import (
    BaseSearchClient,
    SearchResult,
    SearchTimeoutError,
    SearchEngineUnavailableError,
    SearchError,
)


class SearXNGClient(BaseSearchClient):
    """Client for querying local or self-hosted SearXNG JSON API."""

    def __init__(
        self,
        base_url: str = "http://localhost:8080",
        timeout: float = 10.0,
        user_agent: str = "",
        categories: str = "general",
        language: str = "en",
        client: Optional[httpx.Client] = None,
    ):
        super().__init__(name="searxng", timeout=timeout, user_agent=user_agent)
        self.base_url = base_url.rstrip("/")
        self.categories = categories
        self.language = language
        self._client = client

    def _get_client(self) -> httpx.Client:
        if self._client is not None:
            return self._client
        headers = {}
        if self.user_agent:
            headers["User-Agent"] = self.user_agent
        return httpx.Client(timeout=self.timeout, headers=headers)

    def search(self, query: str, max_results: int = 5) -> List[SearchResult]:
        """Query SearXNG JSON API and return parsed SearchResult objects."""
        if not query or not query.strip():
            return []

        url = f"{self.base_url}/search"
        params = {
            "q": query.strip(),
            "format": "json",
            "categories": self.categories,
            "language": self.language,
        }

        client = self._get_client()
        try:
            resp = client.get(url, params=params)
            if resp.status_code != 200:
                raise SearchEngineUnavailableError(
                    f"SearXNG returned HTTP status {resp.status_code}: {resp.text[:150]}"
                )

            data = resp.json()
            raw_results = data.get("results", [])
            results: List[SearchResult] = []

            for item in raw_results[:max_results]:
                title = item.get("title", "").strip()
                res_url = item.get("url", "").strip()
                snippet = item.get("content", "").strip()
                score = float(item.get("score", 1.0) or 1.0)

                if res_url and title:
                    results.append(
                        SearchResult(
                            title=title,
                            url=res_url,
                            snippet=snippet,
                            engine=self.name,
                            score=score,
                        )
                    )

            return results

        except httpx.TimeoutException as e:
            raise SearchTimeoutError(f"SearXNG search timed out: {e}") from e
        except httpx.RequestError as e:
            raise SearchEngineUnavailableError(f"SearXNG connection failed: {e}") from e
        except Exception as e:
            if isinstance(e, (SearchError,)):
                raise
            raise SearchError(f"Unexpected SearXNG error: {e}") from e
        finally:
            if self._client is None:
                client.close()
