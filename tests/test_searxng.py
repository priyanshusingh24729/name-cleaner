"""Unit tests for SearXNG client using mocked HTTP transport."""

import pytest
import httpx
from search.searxng import SearXNGClient
from search.base import SearchTimeoutError, SearchEngineUnavailableError


def test_searxng_successful_search():
    """Verify SearXNG JSON response parsing."""
    mock_json = {
        "results": [
            {
                "title": "Prion Software Official",
                "url": "https://prionsoftware.org",
                "content": "Official homepage for Prion application.",
                "score": 2.5,
            },
            {
                "title": "Prion on GitHub",
                "url": "https://github.com/example/prion",
                "content": "Open source repository for Prion.",
                "score": 1.8,
            },
        ]
    }

    def handler(request: httpx.Request):
        assert "q=Prion" in str(request.url)
        assert "format=json" in str(request.url)
        return httpx.Response(200, json=mock_json)

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)
    searx = SearXNGClient(base_url="http://localhost:8080", client=client)

    results = searx.search("Prion", max_results=2)
    assert len(results) == 2
    assert results[0].title == "Prion Software Official"
    assert results[0].url == "https://prionsoftware.org"
    assert results[0].engine == "searxng"
    assert results[0].score == 2.5


def test_searxng_http_error():
    """Verify SearXNG raises SearchEngineUnavailableError on non-200 status."""
    def handler(request: httpx.Request):
        return httpx.Response(502, text="Bad Gateway")

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)
    searx = SearXNGClient(client=client)

    with pytest.raises(SearchEngineUnavailableError):
        searx.search("Query")


def test_searxng_timeout():
    """Verify timeout raises SearchTimeoutError."""
    def handler(request: httpx.Request):
        raise httpx.ReadTimeout("Timed out")

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)
    searx = SearXNGClient(client=client)

    with pytest.raises(SearchTimeoutError):
        searx.search("Query")
