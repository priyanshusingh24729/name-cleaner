"""Tests for inventory and category prefix detection."""

import pytest


@pytest.mark.parametrize(
    "raw_name, expected_name",
    [
        ("TS-LogRhythm Web Console 6", "LogRhythm Web Console"),
        ("TS_LogRhythm Web Console 6", "LogRhythm Web Console"),
        ("TS - LogRhythm Web Console 6", "LogRhythm Web Console"),
        ("TS-Windows Admin Center 1", "Windows Admin Center"),
        ("Games - Minecraft 1.20", "Minecraft"),
        ("Games: Minecraft", "Minecraft"),
        ("Games_Minecraft 1.20", "Minecraft"),
    ],
)
def test_prefix_removal(normalizer, raw_name, expected_name):
    """Inventory and category prefixes should be cleanly removed."""
    assert normalizer.normalize(raw_name) == expected_name


def test_video_games_manager_preserved(normalizer):
    """'Games' inside a product name must NOT be treated as a prefix."""
    res = normalizer.normalize_structured("Video Games Manager")
    assert res.normalized_name == "Video Games Manager"
    assert "remove_games_prefix" not in res.rules_applied


def test_rule_tracking_for_prefixes(normalizer):
    """Structured result should track prefix removal rule."""
    res = normalizer.normalize_structured("TS-LogRhythm Web Console 6")
    assert "remove_inventory_prefix" in res.rules_applied
    assert "remove_version" in res.rules_applied
