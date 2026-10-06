"""Tests for safe text cleaning and unicode normalization."""

import pytest
from app.text_cleaner import clean_text


@pytest.mark.parametrize(
    "raw_input, expected_output",
    [
        ("  Microsoft    365  ", "Microsoft 365"),
        ("MapToaster Topo/NZ", "MapToaster Topo/NZ"),
        ("Software\u00A0App", "Software App"),  # Non-breaking space
        ("Tool \u2013 1.0", "Tool - 1.0"),       # En-dash
        ("Tool \u2014 1.0", "Tool - 1.0"),       # Em-dash
        ("\u201cSoftware\u201d", '"Software"'),  # Smart quotes
        ("App - ", "App"),                       # Trailing dangling dash
    ],
)
def test_clean_text(raw_input, expected_output):
    """Verify safe character handling and whitespace compaction."""
    assert clean_text(raw_input) == expected_output
