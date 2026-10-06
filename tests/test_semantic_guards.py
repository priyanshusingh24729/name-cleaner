"""Unit tests for anti-hallucination validation and response sanitization."""

import pytest
from semantic.guards import AntiHallucinationGuard


@pytest.fixture
def guard():
    return AntiHallucinationGuard()


def test_sanitize_markdown_and_quotes(guard):
    """Verify markdown code fences, bolding, and quotation marks are stripped."""
    assert guard.sanitize('```\n"AutoCAD 2022"\n```') == "AutoCAD 2022"
    assert guard.sanitize("**Microsoft 365**") == "Microsoft 365"
    assert guard.sanitize('“Liquid XML Studio”') == "Liquid XML Studio"


def test_sanitize_conversational_prefixes(guard):
    """Verify common LLM preamble prefixes are removed."""
    assert guard.sanitize("Canonical Application Name: MapToaster Topo/NZ") == "MapToaster Topo/NZ"
    assert guard.sanitize("Product Name: H2OMAP Water.") == "H2OMAP Water"
    assert guard.sanitize("Answer: LogRhythm Web Console") == "LogRhythm Web Console"


def test_validate_accepts_grounded_canonical(guard):
    """Responses grounded in raw names or evidence must pass validation."""
    raw = "TS-H2OMAP Water 7"
    candidates = ["H2OMAP Water", "H2OMAP Water 7"]
    web_titles = ["H2OMAP Water - Innovyze"]

    assert guard.validate("H2OMAP Water", raw, candidates, web_titles) is True


def test_validate_rejects_hallucination(guard):
    """Unrelated hallucinated text must be rejected."""
    raw = "TS-H2OMAP Water 7"
    candidates = ["H2OMAP Water"]
    web_titles = []

    # Wildly hallucinated product
    assert guard.validate("Adobe Photoshop", raw, candidates, web_titles) is False
    assert guard.validate("Random CRM Database", raw, candidates, web_titles) is False


def test_validate_rejects_conversational_refusal(guard):
    """Conversational AI refusal or apologies must be rejected."""
    raw = "Unknown Tool 1.0"
    candidates = ["Unknown Tool"]

    assert guard.validate("As an AI model, I cannot verify this product.", raw, candidates) is False
    assert guard.validate("I am sorry, but I do not know.", raw, candidates) is False


def test_validate_rejects_excessive_length_expansion(guard):
    """Responses far longer than raw input are rejected as conversational."""
    raw = "NX 2206"
    long_response = "Siemens NX formerly known as Unigraphics is an advanced high-end CAD software suite"

    assert guard.validate(long_response, raw, ["NX"]) is False
