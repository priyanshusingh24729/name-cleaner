"""Tests for version detection and cleaning."""

import pytest


@pytest.mark.parametrize(
    "raw_name, expected_name",
    [
        ("Prion 0.3", "Prion"),
        ("Adobe Reader 11.0", "Adobe Reader"),
        ("Software 2.5.1", "Software"),
        ("MapToaster Topo/NZ v11", "MapToaster Topo/NZ"),
        ("MapToaster v4.2", "MapToaster"),
        ("Product v12.5", "Product"),
        ("Tool Version 11", "Tool"),
        ("Tool Version 4.2", "Tool"),
        ("Utility Ver 11", "Utility"),
        ("Utility Ver. 11", "Utility"),
        ("Game Engine Release 4", "Game Engine"),
        ("Compiler Rev 3", "Compiler"),
        ("Kernel Build 123", "Kernel"),
        ("App 1.0.0.124", "App"),
    ],
)
def test_various_version_formats(normalizer, raw_name, expected_name):
    """Test standard version formats are correctly detected and removed."""
    assert normalizer.normalize(raw_name) == expected_name


def test_meaningful_numbers_preserved(normalizer):
    """Numbers that are part of product identity must not be stripped."""
    assert normalizer.normalize("Microsoft 365") == "Microsoft 365"
    assert normalizer.normalize("neuClock 2") == "neuClock"
