"""Tests for exceptions, preservation rules, and canonical casing."""

import pytest


@pytest.mark.parametrize(
    "input_name, expected_name",
    [
        ("Microsoft 365", "Microsoft 365"),
        ("microsoft 365", "Microsoft 365"),
        ("MICROSOFT 365", "Microsoft 365"),
        ("Microsoft 365 Apps", "Microsoft 365 Apps"),
        ("microsoft 365 apps", "Microsoft 365 Apps"),
        ("MICROSOFT 365 APPS", "Microsoft 365 Apps"),
        ("Microsoft Office", "Microsoft Office"),
        ("microsoft office", "Microsoft Office"),
        ("Symbolbibliothek Elektrotechnik 2011", "Symbolbibliothek Elektrotechnik 2011"),
        ("Windows Admin Center", "Windows Admin Center"),
        ("Video Games Manager", "Video Games Manager"),
    ],
)
def test_exceptions_and_canonical_casing(normalizer, input_name, expected_name):
    """Preserved entities and their case variants must resolve to canonical form."""
    assert normalizer.normalize(input_name) == expected_name


def test_exception_confidence_is_maximum(normalizer):
    """Preserved canonical names must have maximum confidence score 1.0."""
    res = normalizer.normalize_structured("Microsoft 365")
    assert res.confidence == 1.0
    assert res.needs_verification is False
