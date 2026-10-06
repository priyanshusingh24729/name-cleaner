"""YaCy peer-to-peer search client."""

from typing import List, Optional
import httpx

from search.base import (
    BaseSearchClient,
    SearchResult,
    SearchTimeoutError,
    SearchEngineUnavailableError,
    SearchError,
)


class YaCyClient(BaseSearchClient):
    """Client for querying local or networked YaCy search peer."""

    def __init__(
        self,
        base_url: str = "http://localhost:8090",
        timeout: float = 10.0,
        user_agent: str = "",
        verify_ssl: bool = False,
        client: Optional[httpx.Client] = None,
    ):
        super().__init__(name="yacy", timeout=timeout, user_agent=user_agent)
        self.base_url = base_url.rstrip("/")
        self.verify_ssl = verify_ssl
        self._client = client

    def _get_client(self) -> httpx.Client:
        if self._client is not None:
            return self._client
        headers = {}
        if self.user_agent:
            headers["User-Agent"] = self.user_agent
        return httpx.Client(timeout=self.timeout, headers=headers, verify=self.verify_ssl)

    def search(self, query: str, max_results: int = 5) -> List[SearchResult]:
        """Query YaCy JSON API and return parsed SearchResult objects."""
        if not query or not query.strip():
            return []

        url = f"{self.base_url}/yacysearch.json"
        params = {
            "query": query.strip(),
            "maximumRecords": max_results,
            "resource": "global",
        }

        client = self._get_client()
        try:
            resp = client.get(url, params=params)
            if resp.status_code != 200:
                raise SearchEngineUnavailableError(
                    f"YaCy returned HTTP status {resp.status_code}: {resp.text[:150]}"
                )

            data = resp.json()
            channels = data.get("channels", [])
            items = channels[0].get("items", []) if channels else data.get("items", [])
            results: List[SearchResult] = []

            for item in items[:max_results]:
                title = item.get("title", "").strip()
                res_url = item.get("link", "").strip()
                snippet = item.get("description", "").strip()

                if res_url and title:
                    results.append(
                        SearchResult(
                            title=title,
                            url=res_url,
                            snippet=snippet,
                            engine=self.name,
                            score=1.0,
                        )
                    )

            return results

        except httpx.TimeoutException as e:
            raise SearchTimeoutError(f"YaCy search timed out: {e}") from e
        except httpx.RequestError as e:
            raise SearchEngineUnavailableError(f"YaCy connection failed: {e}") from e
        except Exception as e:
            if isinstance(e, (SearchError,)):
                raise
            raise SearchError(f"Unexpected YaCy error: {e}") from e
        finally:
            if self._client is None:
                client.close()
