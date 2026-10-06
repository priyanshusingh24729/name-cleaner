"""Core end-to-end normalization tests."""

import pytest


@pytest.mark.parametrize(
    "raw_name, expected_name",
    [
        ("Prion 0.3 (Android)", "Prion"),
        ("Prion 0.3", "Prion"),
        ("MapToaster Topo/NZ v11 (reg)", "MapToaster Topo/NZ"),
        ("MapToaster Topo/NZ v11", "MapToaster Topo/NZ"),
        ("TS-LogRhythm Web Console 6", "LogRhythm Web Console"),
        ("TS-Windows Admin Center 1", "Windows Admin Center"),
        ("Autodesk AutoCAD 2022 Network License", "Autodesk AutoCAD"),
        ("Autodesk SketchBook Pro 2022 Network License", "Autodesk SketchBook Pro"),
        ("Microsoft 365", "Microsoft 365"),
        ("Microsoft 365 Apps", "Microsoft 365 Apps"),
        ("Microsoft Office", "Microsoft Office"),
        ("Symbolbibliothek Elektrotechnik 2011", "Symbolbibliothek Elektrotechnik 2011"),
        ("Windows Admin Center", "Windows Admin Center"),
        ("Video Games Manager", "Video Games Manager"),
    ],
)
def test_core_positive_examples(normalizer, raw_name, expected_name):
    """Test required positive examples from specification."""
    result = normalizer.normalize(raw_name)
    assert result == expected_name


def test_structured_result_fields(normalizer):
    """Test structured result contains expected properties and audit information."""
    res = normalizer.normalize_structured("Prion 0.3 (Android)")
    assert res.original_name == "Prion 0.3 (Android)"
    assert res.normalized_name == "Prion"
    assert res.confidence >= 0.95
    assert "remove_version" in res.rules_applied
    assert "remove_os" in res.rules_applied
    assert res.changed is True
    assert res.needs_verification is False


def test_structured_result_serialization(normalizer):
    """Test to_dict serialization of structured result."""
    res = normalizer.normalize_structured("TS-LogRhythm Web Console 6")
    d = res.to_dict()
    assert d["original_name"] == "TS-LogRhythm Web Console 6"
    assert d["normalized_name"] == "LogRhythm Web Console"
    assert "remove_inventory_prefix" in d["rules_applied"]
    assert "remove_version" in d["rules_applied"]
    assert d["changed"] is True
