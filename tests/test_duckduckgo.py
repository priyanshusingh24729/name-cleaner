"""Unit tests for DuckDuckGo fallback client using mocked HTTP transport."""

import pytest
import httpx
from search.duckduckgo import DuckDuckGoClient
from search.base import SearchEngineUnavailableError


def test_duckduckgo_successful_search():
    """Verify DuckDuckGo HTML parsing and redirect unwrapping."""
    mock_html = """
    <html>
        <body>
            <div class="result">
                <a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fwww.autodesk.com%2Fautocad">
                    AutoCAD | Computer-Aided Design Software | Autodesk
                </a>
                <a class="result__snippet">
                    Autodesk AutoCAD is computer-aided design CAD software that architects, engineers rely on.
                </a>
            </div>
        </body>
    </html>
    """

    def handler(request: httpx.Request):
        assert request.method == "POST"
        return httpx.Response(200, text=mock_html)

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)
    ddg = DuckDuckGoClient(client=client)

    results = ddg.search("Autodesk AutoCAD", max_results=1)
    assert len(results) == 1
    assert "AutoCAD" in results[0].title
    assert results[0].url == "https://www.autodesk.com/autocad"
    assert "Autodesk AutoCAD is computer-aided design" in results[0].snippet
    assert results[0].engine == "duckduckgo"


def test_duckduckgo_error_handling():
    """Verify non-200 status raises SearchEngineUnavailableError."""
    def handler(request: httpx.Request):
        return httpx.Response(403, text="Forbidden")

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)
    ddg = DuckDuckGoClient(client=client)

    with pytest.raises(SearchEngineUnavailableError):
        ddg.search("Test")
