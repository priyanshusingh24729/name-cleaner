"""Negative tests to ensure the normalizer avoids over-normalization."""

import pytest


def test_microsoft_365_not_stripped_to_microsoft(normalizer):
    """Microsoft 365 must NOT become Microsoft."""
    result = normalizer.normalize("Microsoft 365")
    assert result == "Microsoft 365"
    assert result != "Microsoft"
    assert result != "Microsoft365"


def test_microsoft_365_apps_not_stripped_to_apps(normalizer):
    """Microsoft 365 Apps must NOT become Microsoft Apps."""
    result = normalizer.normalize("Microsoft 365 Apps")
    assert result == "Microsoft 365 Apps"
    assert result != "Microsoft Apps"


def test_symbolbibliothek_not_stripped(normalizer):
    """Symbolbibliothek Elektrotechnik 2011 must NOT lose 2011."""
    result = normalizer.normalize("Symbolbibliothek Elektrotechnik 2011")
    assert result == "Symbolbibliothek Elektrotechnik 2011"
    assert result != "Symbolbibliothek Elektrotechnik"


def test_windows_admin_center_not_stripped(normalizer):
    """Windows Admin Center must NOT become Admin Center."""
    result = normalizer.normalize("Windows Admin Center")
    assert result == "Windows Admin Center"
    assert result != "Admin Center"


def test_video_games_manager_not_stripped(normalizer):
    """Video Games Manager must NOT become Video Manager."""
    result = normalizer.normalize("Video Games Manager")
    assert result == "Video Games Manager"
    assert result != "Video Manager"


@pytest.mark.parametrize(
    "name",
    [
        "Microsoft 365",
        "Microsoft 365 Apps",
        "Microsoft Office",
        "Symbolbibliothek Elektrotechnik 2011",
        "Windows Admin Center",
        "Video Games Manager",
    ],
)
def test_idempotence_and_preservation(normalizer, name):
    """Normalized names must remain identical if re-normalized."""
    first_pass = normalizer.normalize(name)
    second_pass = normalizer.normalize(first_pass)
    assert first_pass == name
    assert second_pass == name
