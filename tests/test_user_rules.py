"""Tests for user-specified normalization rules and examples."""

import pytest
from app.normalizer import NameNormalizer


@pytest.fixture
def clean_normalizer():
    return NameNormalizer(use_cache=False, use_fuzzy=False, enable_semantic=False)


@pytest.mark.parametrize(
    "raw_input, expected_output",
    [
        ("TS-Altova DiffDog 2011 R2 Professional", "Altova DiffDog"),
        ("Veeam Backup & Replication 11 Enterprise", "Veeam Backup & Replication"),
        (
            "IBM InfoSphere Information Server Pack 6.5 for SAP R/3 Non-Production Environment",
            "IBM InfoSphere Information Server Pack for SAP R/3",
        ),
        ("Solver SDK Platform 11", "Solver SDK Platform"),
        ("ClaimMaster 2018 QA (reg)", "ClaimMaster"),
        ("Citrix ADC MPX 14500 NEBS Enterprise", "Citrix ADC MPX 14500"),
    ],
)
def test_user_examples_deterministic(clean_normalizer, raw_input, expected_output):
    """Verify that all user-specified examples resolve to their exact canonical names."""
    result = clean_normalizer.normalize(raw_input)
    assert result == expected_output


def test_last_bracket_removal(clean_normalizer):
    """Verify that trailing brackets are stripped while product identifiers are preserved."""
    assert clean_normalizer.normalize("Product (reg)") == "Product"
    assert clean_normalizer.normalize("Product (Trial)") == "Product"
    assert clean_normalizer.normalize("Product (QA)") == "Product"
    assert clean_normalizer.normalize("Product (Trial) - expired") == "Product"
    assert clean_normalizer.normalize("Product (QA) (reg)") == "Product"
    assert clean_normalizer.normalize("AutoCAD (LT)") == "AutoCAD (LT)"


def test_licensing_and_environment_terms(clean_normalizer):
    """Verify removal of Enterprise, Professional, QA, Non-Production Environment, etc."""
    assert clean_normalizer.normalize("Database Tool Enterprise") == "Database Tool"
    assert clean_normalizer.normalize("Code Editor Professional") == "Code Editor"
    assert clean_normalizer.normalize("Server Suite Non-Production Environment") == "Server Suite"
    assert clean_normalizer.normalize("Network Monitor QA") == "Network Monitor"
    assert clean_normalizer.normalize("App UAT") == "App"
