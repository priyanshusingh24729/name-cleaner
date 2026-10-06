"""Unit tests for YaCy search client using mocked HTTP transport."""

import pytest
import httpx
from search.yacy import YaCyClient
from search.base import SearchEngineUnavailableError, SearchTimeoutError


def test_yacy_successful_search():
    """Verify YaCy channels/items JSON parsing."""
    mock_json = {
        "channels": [
            {
                "items": [
                    {
                        "title": "MapToaster Topo NZ",
                        "link": "https://www.maptoaster.com",
                        "description": "Topographical digital mapping software for New Zealand.",
                    }
                ]
            }
        ]
    }

    def handler(request: httpx.Request):
        assert "yacysearch.json" in str(request.url)
        return httpx.Response(200, json=mock_json)

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)
    yacy = YaCyClient(base_url="http://localhost:8090", client=client)

    results = yacy.search("MapToaster Topo/NZ", max_results=1)
    assert len(results) == 1
    assert results[0].title == "MapToaster Topo NZ"
    assert results[0].url == "https://www.maptoaster.com"
    assert results[0].engine == "yacy"


def test_yacy_connection_failure():
    """Verify connection error raises SearchEngineUnavailableError."""
    def handler(request: httpx.Request):
        raise httpx.ConnectError("Connection refused")

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)
    yacy = YaCyClient(client=client)

    with pytest.raises(SearchEngineUnavailableError):
        yacy.search("Test")
