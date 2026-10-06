"""Unit tests for official source detector and domain authority scoring."""

import pytest
from crawler.official_source import OfficialSourceDetector


@pytest.fixture
def detector():
    return OfficialSourceDetector()


def test_extract_domain(detector):
    """Verify clean domain extraction from various URL formats."""
    assert detector.extract_domain("https://www.autodesk.com/products/autocad") == "autodesk.com"
    assert detector.extract_domain("http://download.cnet.com/item") == "download.cnet.com"
    assert detector.extract_domain("https://github.com/microsoft/vscode") == "github.com"
    assert detector.extract_domain("www.adobe.com:443/photoshop") == "adobe.com"


def test_official_vendor_detection(detector):
    """Known vendors in official_domains.yaml must be recognized."""
    assert detector.is_official_vendor("https://www.autodesk.com/products") is True
    assert detector.is_official_vendor("https://subdomain.microsoft.com/en-us") is True
    assert detector.is_official_vendor("https://randomblog123.com/software") is False


def test_vendor_hint_matching(detector):
    """Vendor hint matches vendor name inside domain string."""
    assert detector.is_official_vendor("https://liquid-technologies.com/xml", vendor_hint="Liquid Technologies") is True


def test_package_repositories(detector):
    """Package and code repositories must be recognized."""
    assert detector.is_package_repository("https://github.com/psf/requests") is True
    assert detector.is_package_repository("https://sourceforge.net/projects/sevenzip/") is True
    assert detector.is_package_repository("https://pypi.org/project/httpx/") is True


def test_authority_scoring(detector):
    """Authority scores must follow the priority hierarchy."""
    vendor_score = detector.get_authority_score("https://www.autodesk.com/products/autocad")
    repo_score = detector.get_authority_score("https://github.com/example/tool")
    aggregator_score = detector.get_authority_score("https://download.cnet.com/tool")
    unknown_score = detector.get_authority_score("https://random-downloads.xyz/item")

    assert vendor_score >= 0.95
    assert repo_score >= 0.90
    assert aggregator_score >= 0.65
    assert unknown_score <= 0.40
    assert vendor_score > unknown_score
