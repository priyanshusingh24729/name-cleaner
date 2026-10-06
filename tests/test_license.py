"""Tests for license and registration metadata detection."""

import pytest


@pytest.mark.parametrize(
    "raw_name, expected_name",
    [
        ("Autodesk AutoCAD 2022 Network License", "Autodesk AutoCAD"),
        ("Autodesk SketchBook Pro 2022 Network License", "Autodesk SketchBook Pro"),
        ("Software Network Licence", "Software"),
        ("CAD Tool Standalone License", "CAD Tool"),
        ("MapToaster Topo/NZ v11 (reg)", "MapToaster Topo/NZ"),
        ("Editor (trial)", "Editor"),
        ("Viewer (demo)", "Viewer"),
        ("Utility (evaluation)", "Utility"),
    ],
)
def test_license_and_registration_removal(normalizer, raw_name, expected_name):
    """Licensing and registration terms should be cleanly stripped."""
    assert normalizer.normalize(raw_name) == expected_name


def test_rules_applied_for_license_and_reg(normalizer):
    """Verify appropriate rules are recorded in structured result."""
    res = normalizer.normalize_structured("MapToaster Topo/NZ v11 (reg)")
    assert res.normalized_name == "MapToaster Topo/NZ"
    assert "remove_registration" in res.rules_applied
    assert "remove_version" in res.rules_applied
