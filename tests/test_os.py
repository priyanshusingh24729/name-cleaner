"""Tests for OS and platform metadata detection vs product name preservation."""

import pytest


@pytest.mark.parametrize(
    "raw_name, expected_name",
    [
        ("Prion 0.3 (Android)", "Prion"),
        ("Software 2.1 (Linux)", "Software"),
        ("Software 3.0 (Mac)", "Software"),
        ("Application (macOS)", "Application"),
        ("Tool (iOS)", "Tool"),
        ("Utility (Windows 10)", "Utility"),
        ("Mimecast Security Agent 0.8 (Mac)", "Mimecast Security Agent"),
        ("Backup Tool for Windows", "Backup Tool"),
        ("Editor for Mac", "Editor"),
        ("Utility for Linux", "Utility"),
        ("BMC Performance Manager (HP-UX)", "BMC Performance Manager"),
        ("Database Utility (AIX)", "Database Utility"),
        ("Network Monitor (Solaris)", "Network Monitor"),
        ("Software Suite (NL)", "Software Suite"),
        ("Backup Tool for HP-UX", "Backup Tool"),
        ("Monitoring Agent for Solaris", "Monitoring Agent"),
    ],
)
def test_os_metadata_removal(normalizer, raw_name, expected_name):
    """OS metadata in parentheses or 'for <OS>' should be removed."""
    assert normalizer.normalize(raw_name) == expected_name


def test_legitimate_product_parentheses_preserved(normalizer):
    """Legitimate product-name parentheticals must NOT be removed."""
    # Parenthetical content that is not an OS, license, version, or architecture is preserved
    assert normalizer.normalize("AutoCAD (LT)") == "AutoCAD (LT)"
    assert normalizer.normalize("ProSuite (Developer Edition)") == "ProSuite (Developer Edition)"


def test_windows_admin_center_preserves_os_word(normalizer):
    """The word 'Windows' in Windows Admin Center must NOT be removed."""
    res = normalizer.normalize_structured("Windows Admin Center")
    assert res.normalized_name == "Windows Admin Center"
    assert "remove_os" not in res.rules_applied
