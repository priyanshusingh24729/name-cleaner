"""Tests for RapidFuzz matching and anti-conflation safeguards."""

import pytest
from app.dictionary import CanonicalDictionary
from app.rules import RuleEngine


@pytest.fixture
def dictionary(tmp_path):
    """Fixture with isolated test database and seeded canonical names."""
    db_path = tmp_path / "test_fuzzy.db"
    dict_obj = CanonicalDictionary(db_path, rule_engine=RuleEngine())
    # Seed specific canonical products for testing
    dict_obj.add_canonical("Windows 10", "Windows 10", 1.0, "preset", verified=1)
    dict_obj.add_canonical("Windows 11", "Windows 11", 1.0, "preset", verified=1)
    dict_obj.add_canonical("Microsoft Office 2016", "Microsoft Office 2016", 1.0, "preset", verified=1)
    dict_obj.add_canonical("Microsoft Office 2019", "Microsoft Office 2019", 1.0, "preset", verified=1)
    return dict_obj


@pytest.mark.parametrize(
    "query",
    [
        "Microsoft 365",
        "Microsoft  365",
        "MICROSOFT 365",
        "Microsoft   365",
        "Microsoft-365",
    ],
)
def test_microsoft_365_fuzzy_resolution(dictionary, query):
    """Section 15 specification: Minor spacing/casing variations must resolve to Microsoft 365."""
    match = dictionary.fuzzy_match(query)
    assert match is not None
    matched_name, score = match
    assert matched_name == "Microsoft 365"
    assert score >= 90.0


def test_no_numerical_conflation_windows(dictionary):
    """Fuzzy matching MUST NOT conflate Windows 10 with Windows 11."""
    match_10 = dictionary.fuzzy_match("Windows 10")
    assert match_10 is not None
    assert match_10[0] == "Windows 10"

    match_11 = dictionary.fuzzy_match("Windows 11")
    assert match_11 is not None
    assert match_11[0] == "Windows 11"

    # Query with version 10 should NEVER match Windows 11
    # Test internal helper logic
    assert dictionary._extract_numbers("Windows 10") != dictionary._extract_numbers("Windows 11")


def test_no_numerical_conflation_office_years(dictionary):
    """Fuzzy matching MUST NOT conflate Office 2016 with Office 2019."""
    match_2016 = dictionary.fuzzy_match("Microsoft Office 2016")
    assert match_2016 is not None
    assert match_2016[0] == "Microsoft Office 2016"

    match_2019 = dictionary.fuzzy_match("Microsoft Office 2019")
    assert match_2019 is not None
    assert match_2019[0] == "Microsoft Office 2019"
