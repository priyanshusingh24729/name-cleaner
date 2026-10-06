"""Unit tests for WebCrawler using mocked HTTP transport."""

import pytest
import httpx
from search.base import SearchResult
from crawler.crawler import WebCrawler


def test_crawl_page_success():
    """Verify crawler retrieves page and builds structured CrawlEvidence."""
    mock_html = """
    <html>
        <head>
            <title>AutoCAD 2022 | CAD Design Software | Autodesk</title>
            <meta name="description" content="Autodesk AutoCAD official CAD software.">
        </head>
        <body>
            <p>Official download and documentation for AutoCAD.</p>
        </body>
    </html>
    """

    def handler(request: httpx.Request):
        return httpx.Response(
            200,
            text=mock_html,
            headers={"content-type": "text/html; charset=utf-8"},
        )

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)
    crawler = WebCrawler(client=client)

    evidence = crawler.crawl_page("https://www.autodesk.com/products/autocad")
    assert evidence is not None
    assert evidence.status_code == 200
    assert evidence.domain == "autodesk.com"
    assert evidence.is_official is True
    assert evidence.authority_score >= 0.95
    assert evidence.clean_title == "AutoCAD 2022"
    assert "Autodesk AutoCAD official" in evidence.text_summary


def test_crawl_page_handles_404_gracefully():
    """404 response returns evidence with status code 404 without crashing."""
    def handler(request: httpx.Request):
        return httpx.Response(404, text="Not Found")

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)
    crawler = WebCrawler(client=client)

    evidence = crawler.crawl_page("https://example.com/nonexistent")
    assert evidence is not None
    assert evidence.status_code == 404
    assert evidence.clean_title == ""


def test_crawl_page_handles_timeout_gracefully():
    """Timeout returns None gracefully."""
    def handler(request: httpx.Request):
        raise httpx.ReadTimeout("Timeout")

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)
    crawler = WebCrawler(client=client)

    evidence = crawler.crawl_page("https://example.com/timeout")
    assert evidence is None


def test_crawl_results_prioritizes_official_domain():
    """Crawler must prioritize official vendor over third-party blog."""
    crawled_order = []

    def handler(request: httpx.Request):
        url_str = str(request.url)
        crawled_order.append(url_str)
        html = f"<html><head><title>Page on {url_str}</title></head><body><p>Content</p></body></html>"
        return httpx.Response(200, text=html, headers={"content-type": "text/html"})

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)
    crawler = WebCrawler(client=client)

    search_results = [
        SearchResult("Blog Review", "https://randomtechblog.org/cad-review", "Review", "duckduckgo"),
        SearchResult("Autodesk Official", "https://www.autodesk.com/products/autocad", "CAD", "searxng"),
        SearchResult("CNET Download", "https://download.cnet.com/autocad", "Download", "yacy"),
    ]

    evidences = crawler.crawl_results(search_results, max_pages=2)
    assert len(evidences) == 2
    # Autodesk (authority 1.0) must be crawled first
    assert "autodesk.com" in crawled_order[0]
    assert evidences[0].domain == "autodesk.com"
