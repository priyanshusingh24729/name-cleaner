"""DuckDuckGo fallback search client."""

from typing import List, Optional
import urllib.parse
from bs4 import BeautifulSoup
import httpx

from search.base import (
    BaseSearchClient,
    SearchResult,
    SearchTimeoutError,
    SearchEngineUnavailableError,
    SearchError,
)


class DuckDuckGoClient(BaseSearchClient):
    """Client for DuckDuckGo fallback search via HTTP."""

    def __init__(
        self,
        endpoint: str = "https://html.duckduckgo.com/html/",
        timeout: float = 10.0,
        user_agent: str = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
        client: Optional[httpx.Client] = None,
    ):
        super().__init__(name="duckduckgo", timeout=timeout, user_agent=user_agent)
        self.endpoint = endpoint
        self._client = client

    def _get_client(self) -> httpx.Client:
        if self._client is not None:
            return self._client
        headers = {
            "User-Agent": self.user_agent,
            "Accept-Language": "en-US,en;q=0.9",
        }
        return httpx.Client(timeout=self.timeout, headers=headers, follow_redirects=True)

    @staticmethod
    def _clean_url(raw_url: str) -> str:
        """Extract destination URL if wrapped in DuckDuckGo redirect link."""
        if "uddg=" in raw_url:
            parsed = urllib.parse.urlparse(raw_url)
            query_params = urllib.parse.parse_qs(parsed.query)
            if "uddg" in query_params:
                return query_params["uddg"][0]
        return raw_url

    def search(self, query: str, max_results: int = 5) -> List[SearchResult]:
        """Query DuckDuckGo HTML endpoint and parse organic search results."""
        if not query or not query.strip():
            return []

        client = self._get_client()
        try:
            resp = client.post(
                self.endpoint,
                data={"q": query.strip()},
            )

            if resp.status_code != 200:
                raise SearchEngineUnavailableError(
                    f"DuckDuckGo returned HTTP status {resp.status_code}"
                )

            soup = BeautifulSoup(resp.text, "html.parser")
            results: List[SearchResult] = []

            # Find all organic result containers
            result_elements = soup.find_all("div", class_="result")
            for elem in result_elements:
                title_link = elem.find("a", class_="result__a")
                if not title_link:
                    continue

                raw_href = title_link.get("href", "")
                title = title_link.get_text(strip=True)
                clean_url = self._clean_url(raw_href)

                snippet_elem = elem.find("a", class_="result__snippet")
                snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""

                if clean_url and title:
                    results.append(
                        SearchResult(
                            title=title,
                            url=clean_url,
                            snippet=snippet,
                            engine=self.name,
                            score=1.0,
                        )
                    )

                if len(results) >= max_results:
                    break

            return results

        except httpx.TimeoutException as e:
            raise SearchTimeoutError(f"DuckDuckGo search timed out: {e}") from e
        except httpx.RequestError as e:
            raise SearchEngineUnavailableError(f"DuckDuckGo connection failed: {e}") from e
        except Exception as e:
            if isinstance(e, (SearchError,)):
                raise
            raise SearchError(f"Unexpected DuckDuckGo error: {e}") from e
        finally:
            if self._client is None:
                client.close()
