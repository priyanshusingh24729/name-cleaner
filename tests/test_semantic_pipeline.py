"""Unit and integration tests for the SemanticVerifier and Normalizer pipeline."""

import pytest
from pathlib import Path

from app.normalizer import NameNormalizer
from app.result import NormalizationResult
from search.base import SearchResult
from search.manager import SearchManager
from crawler.crawler import WebCrawler, CrawlEvidence
from semantic.client import MockLLMClient
from semantic.verifier import SemanticVerifier


class MockSearchManager(SearchManager):
    """Mock search manager returning canned search results."""

    def __init__(self, canned_results=None):
        self.canned_results = canned_results or []

    def search(self, query: str, max_results: int = 5):
        return self.canned_results


class MockCrawler(WebCrawler):
    """Mock web crawler returning canned crawl evidence."""

    def __init__(self, canned_evidence=None):
        self.canned_evidence = canned_evidence or []

    def crawl_results(self, search_results, vendor_hint=None, max_pages=3):
        return self.canned_evidence


@pytest.fixture
def tmp_db_path(tmp_path):
    return tmp_path / "test_semantic_dictionary.db"


def test_verifier_official_evidence_resolution(tmp_db_path):
    """Verify resolution when official vendor evidence is available."""
    canned_evidence = [
        CrawlEvidence(
            url="https://www.autodesk.com/products/autocad",
            domain="autodesk.com",
            is_official=True,
            authority_score=1.0,
            raw_title="AutoCAD 2022 | Autodesk",
            clean_title="AutoCAD 2022",
            application_name="AutoCAD",
            text_summary="Autodesk AutoCAD official CAD design software.",
        )
    ]

    llm = MockLLMClient(canned_responses={"autocad": "AutoCAD"})
    search_mgr = MockSearchManager(canned_results=[
        SearchResult("AutoCAD Official", "https://www.autodesk.com/products/autocad", "CAD", "duckduckgo")
    ])
    crawler = MockCrawler(canned_evidence=canned_evidence)

    normalizer = NameNormalizer(db_path=tmp_db_path)
    verifier = SemanticVerifier(
        llm_client=llm,
        search_manager=search_mgr,
        crawler=crawler,
        dictionary=normalizer.dictionary,
    )

    raw_name = "Autodesk AutoCAD 2022 Network License"
    res = verifier.verify(raw_name)

    assert res.normalized_name == "AutoCAD"
    assert res.method == "llm_official_verified"
    assert res.confidence >= 0.88
    assert res.needs_verification is False

    # Check persistence in SQLite canonical store
    cached = normalizer.dictionary.store.get(raw_name)
    assert cached is not None
    assert cached["normalized_name"] == "AutoCAD"
    assert cached["verified"] == 1


def test_verifier_search_evidence_resolution(tmp_db_path):
    """Verify resolution when general search evidence (non-official) is available."""
    canned_search = [
        SearchResult(
            title="LogRhythm Web Console Overview",
            url="https://some-tech-blog.org/logrhythm",
            snippet="LogRhythm Web Console allows security analysts to monitor events.",
            engine="duckduckgo",
        )
    ]

    llm = MockLLMClient(canned_responses={"logrhythm": "LogRhythm Web Console"})
    search_mgr = MockSearchManager(canned_results=canned_search)
    crawler = MockCrawler(canned_evidence=[])

    normalizer = NameNormalizer(db_path=tmp_db_path)
    verifier = SemanticVerifier(
        llm_client=llm,
        search_manager=search_mgr,
        crawler=crawler,
        dictionary=normalizer.dictionary,
    )

    raw_name = "TS-LogRhythm Web Console 6"
    res = verifier.verify(raw_name)

    assert res.normalized_name == "LogRhythm Web Console"
    assert res.method == "llm_search_verified"
    assert res.confidence >= 0.75
    assert res.needs_verification is False


def test_verifier_safe_fallback_on_hallucination(tmp_db_path):
    """Verify safe fallback when LLM generates hallucinated content."""
    llm = MockLLMClient(canned_responses={"h2omap": "Adobe Premiere Pro Extreme Edition"})
    search_mgr = MockSearchManager()
    crawler = MockCrawler()

    normalizer = NameNormalizer(db_path=tmp_db_path)
    verifier = SemanticVerifier(
        llm_client=llm,
        search_manager=search_mgr,
        crawler=crawler,
        dictionary=normalizer.dictionary,
    )

    raw_name = "TS-H2OMAP Water 7"
    initial_res = NormalizationResult(
        original_name=raw_name,
        normalized_name="H2OMAP Water 7",
        confidence=0.80,
        rules_applied=["remove_inventory_prefix"],
        changed=True,
        needs_verification=True,
        method="deterministic",
    )

    res = verifier.verify(raw_name, initial_result=initial_res)

    # Must reject hallucination and fall back conservatively
    assert res.normalized_name == "H2OMAP Water 7"
    assert res.method == "unverified_fallback"
    assert res.confidence == 0.65
    assert res.needs_verification is True


def test_normalizer_verify_with_llm_and_cache(tmp_db_path):
    """Verify NameNormalizer.verify_with_llm orchestrates end-to-end and subsequent call hits cache."""
    llm = MockLLMClient(canned_responses={"h2omap": "H2OMAP Water"})
    search_mgr = MockSearchManager()
    crawler = MockCrawler()

    normalizer = NameNormalizer(db_path=tmp_db_path)
    verifier = SemanticVerifier(
        llm_client=llm,
        search_manager=search_mgr,
        crawler=crawler,
        dictionary=normalizer.dictionary,
    )
    normalizer._semantic_verifier = verifier

    raw_name = "TS-H2OMAP Water 7"
    verified_res = normalizer.verify_with_llm(raw_name)
    assert verified_res.normalized_name == "H2OMAP Water"

    # Subsequent normalization of the exact same raw name must hit exact_cache immediately!
    subsequent_res = normalizer.normalize_structured(raw_name)
    assert subsequent_res.method == "exact_cache"
    assert subsequent_res.normalized_name == "H2OMAP Water"
