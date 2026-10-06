"""Tests for intelligent and conservative year handling."""

import pytest


def test_symbolbibliothek_year_preserved(normalizer):
    """The year 2011 in Symbolbibliothek Elektrotechnik 2011 must remain."""
    res = normalizer.normalize_structured("Symbolbibliothek Elektrotechnik 2011")
    assert res.normalized_name == "Symbolbibliothek Elektrotechnik 2011"
    assert "preserve_year" in res.rules_applied


def test_autodesk_contextual_year_removed(normalizer):
    """Autodesk annual release year 2022 should be removed when coupled with license/product."""
    res = normalizer.normalize_structured("Autodesk AutoCAD 2022 Network License")
    assert res.normalized_name == "Autodesk AutoCAD"
    assert "remove_version" in res.rules_applied
    assert "remove_license" in res.rules_applied


def test_autodesk_sketchbook_year_removed(normalizer):
    """Autodesk SketchBook Pro 2022 Network License -> Autodesk SketchBook Pro."""
    res = normalizer.normalize_structured("Autodesk SketchBook Pro 2022 Network License")
    assert res.normalized_name == "Autodesk SketchBook Pro"


def test_ambiguous_year_preserved_with_verification(normalizer):
    """An ambiguous four-digit year must be PRESERVED and flagged for future verification."""
    res = normalizer.normalize_structured("Some Software 2022")
    assert res.normalized_name == "Some Software 2022"
    assert res.needs_verification is True
    assert res.confidence < 0.90
    assert "preserve_year" in res.rules_applied
