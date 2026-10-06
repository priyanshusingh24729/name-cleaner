"""Edge case tests covering complex combinations and preserving legitimate content."""

import pytest


@pytest.mark.parametrize(
    "raw_name, expected_name",
    [
        # Whitespace and unicode dash edge cases
        ("   \t  Adobe   Acrobat   11.0   \n ", "Adobe Acrobat"),
        ("Tool \u2013 1.0", "Tool"),  # En-dash with version removed and trailing dash stripped
        # Multiple parenthetical metadata values
        ("Software 2.0 (Mac) (x64) (reg)", "Software"),
        ("App (Windows) (trial)", "App"),
        # Combined prefix + version + OS + registration
        ("TS-Inventory System 4.5.1 (Linux) (reg)", "Inventory System"),
        ("Games - Counter-Strike 1.6", "Counter-Strike"),
        # Legitimate words containing 'Games', 'Windows', 'Mac', 'Linux', 'License'
        ("Hunger Games Companion", "Hunger Games Companion"),
        ("Windows PowerShell", "Windows PowerShell"),
        ("Macromedia Flash 8", "Macromedia Flash"),
        ("Linux Kernel Headers", "Linux Kernel Headers"),
        ("Driver License Scanner", "Driver License Scanner"),
        ("Creative Commons License Viewer", "Creative Commons License Viewer"),
        # Legitimate numbers and models
        ("GeForce RTX 3080 Control Panel", "GeForce RTX 3080 Control Panel"),
        ("Cisco AnyConnect 4.10", "Cisco AnyConnect"),
        ("7-Zip 19.00", "7-Zip"),
        ("WinRAR 6.0", "WinRAR"),
    ],
)
def test_edge_case_combinations(normalizer, raw_name, expected_name):
    """Test complex edge cases, ensuring legitimate words and numbers are preserved."""
    assert normalizer.normalize(raw_name) == expected_name


def test_driver_license_scanner_preserves_license(normalizer):
    """The word 'License' in 'Driver License Scanner' must NOT be removed."""
    res = normalizer.normalize_structured("Driver License Scanner")
    assert res.normalized_name == "Driver License Scanner"
    assert "remove_license" not in res.rules_applied


def test_hunger_games_preserves_games(normalizer):
    """'Games' inside a product title must NOT be removed."""
    res = normalizer.normalize_structured("Hunger Games Companion")
    assert res.normalized_name == "Hunger Games Companion"
    assert "remove_games_prefix" not in res.rules_applied


def test_seven_zip_preserves_number(normalizer):
    """'7' in 7-Zip must NOT be stripped as a version."""
    res = normalizer.normalize_structured("7-Zip 19.00")
    assert res.normalized_name == "7-Zip"
