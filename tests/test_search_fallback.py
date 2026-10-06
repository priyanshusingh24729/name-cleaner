"""Tests for SearchManager cascading fallback and query caching."""

import pytest
from unittest.mock import MagicMock
from search.base import SearchResult, SearchEngineUnavailableError
from search.manager import SearchManager


def test_format_software_query():
    """Verify inventory prefixes are removed before searching."""
    cleaned = SearchManager.format_software_query("TS-LogRhythm Web Console 6")
    assert cleaned == "LogRhythm Web Console 6"


def test_searxng_success_skips_fallbacks():
    """When SearXNG succeeds, YaCy and DuckDuckGo must not be called."""
    mock_searx = MagicMock()
    mock_searx.search.return_value = [
        SearchResult("Prion App", "https://prion.org", "Official", "searxng")
    ]

    mock_yacy = MagicMock()
    mock_ddg = MagicMock()

    clients = {
        "searxng": mock_searx,
        "yacy": mock_yacy,
        "duckduckgo": mock_ddg,
    }

    manager = SearchManager(clients=clients)
    results = manager.search("Prion 0.3")

    assert len(results) == 1
    assert results[0].engine == "searxng"
    mock_searx.search.assert_called_once()
    mock_yacy.search.assert_not_called()
    mock_ddg.search.assert_not_called()


def test_searxng_fail_falls_back_to_yacy():
    """When SearXNG fails, YaCy is called, and DuckDuckGo is not called."""
    mock_searx = MagicMock()
    mock_searx.search.side_effect = SearchEngineUnavailableError("SearXNG down")

    mock_yacy = MagicMock()
    mock_yacy.search.return_value = [
        SearchResult("MapToaster NZ", "https://maptoaster.com", "Maps", "yacy")
    ]

    mock_ddg = MagicMock()

    clients = {
        "searxng": mock_searx,
        "yacy": mock_yacy,
        "duckduckgo": mock_ddg,
    }

    manager = SearchManager(clients=clients)
    results = manager.search("MapToaster")

    assert len(results) == 1
    assert results[0].engine == "yacy"
    mock_searx.search.assert_called_once()
    mock_yacy.search.assert_called_once()
    mock_ddg.search.assert_not_called()


def test_searxng_and_yacy_fail_falls_back_to_ddg():
    """When both SearXNG and YaCy fail, DuckDuckGo provides the fallback results."""
    mock_searx = MagicMock()
    mock_searx.search.side_effect = SearchEngineUnavailableError("SearXNG down")

    mock_yacy = MagicMock()
    mock_yacy.search.side_effect = SearchEngineUnavailableError("YaCy down")

    mock_ddg = MagicMock()
    mock_ddg.search.return_value = [
        SearchResult("Autodesk AutoCAD", "https://autodesk.com", "CAD", "duckduckgo")
    ]

    clients = {
        "searxng": mock_searx,
        "yacy": mock_yacy,
        "duckduckgo": mock_ddg,
    }

    manager = SearchManager(clients=clients)
    results = manager.search("AutoCAD")

    assert len(results) == 1
    assert results[0].engine == "duckduckgo"
    mock_searx.search.assert_called_once()
    mock_yacy.search.assert_called_once()
    mock_ddg.search.assert_called_once()


def test_search_results_cached():
    """Identical repeated search queries should hit cache without calling clients again."""
    mock_searx = MagicMock()
    mock_searx.search.return_value = [
        SearchResult("Product X", "https://productx.com", "Snippet", "searxng")
    ]

    clients = {
        "searxng": mock_searx,
        "yacy": MagicMock(),
        "duckduckgo": MagicMock(),
    }

    manager = SearchManager(clients=clients)
    first_call = manager.search("Product X")
    second_call = manager.search("Product X")

    assert first_call == second_call
    # Engine should be called only once
    assert mock_searx.search.call_count == 1
