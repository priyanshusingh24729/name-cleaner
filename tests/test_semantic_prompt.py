"""Unit tests for Section 18 structured prompt building."""

import pytest
from semantic.prompt import PromptBuilder
from search.base import SearchResult
from crawler.crawler import CrawlEvidence


def test_prompt_builder_contains_critical_rules():
    """Verify system prompt enforces Section 18 core constraints."""
    msgs = PromptBuilder.build_verification_prompt(
        raw_name="TS-H2OMAP Water 7",
        candidates=["H2OMAP Water", "H2OMAP Water 7"],
    )

    system_prompt = msgs["system"]
    assert "Return ONLY the canonical application name" in system_prompt
    assert "Do not invent a product" in system_prompt
    assert "PRESERVE years" in system_prompt
    assert "PRESERVE product editions" in system_prompt
    assert "Prefer evidence from official vendor domains" in system_prompt


def test_prompt_builder_includes_candidates_and_raw():
    """Verify user prompt presents raw record and candidate hypotheses."""
    raw = "TS-H2OMAP Water 7"
    candidates = ["H2OMAP Water", "H2OMAP Water 7"]

    msgs = PromptBuilder.build_verification_prompt(
        raw_name=raw,
        candidates=candidates,
    )

    user_prompt = msgs["user"]
    assert "RAW APPLICATION NAME: TS-H2OMAP Water 7" in user_prompt
    assert "1. H2OMAP Water" in user_prompt
    assert "2. H2OMAP Water 7" in user_prompt


def test_prompt_builder_includes_crawl_evidence():
    """Verify official crawl evidence is structured into the prompt."""
    evidence = [
        CrawlEvidence(
            url="https://www.autodesk.com/products/autocad",
            domain="autodesk.com",
            is_official=True,
            authority_score=1.0,
            raw_title="AutoCAD 2022 | Autodesk",
            clean_title="AutoCAD 2022",
            application_name="AutoCAD",
            text_summary="Autodesk AutoCAD official CAD software.",
        )
    ]

    msgs = PromptBuilder.build_verification_prompt(
        raw_name="Autodesk AutoCAD 2022 Network License",
        candidates=["Autodesk AutoCAD"],
        crawl_evidence=evidence,
    )

    user_prompt = msgs["user"]
    assert "[OFFICIAL VENDOR] autodesk.com" in user_prompt
    assert "AutoCAD 2022" in user_prompt
    assert "Autodesk AutoCAD official" in user_prompt
