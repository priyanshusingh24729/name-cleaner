"""Tests for dataset deduplicator (Section 14)."""

import pytest
import pandas as pd
from app.normalizer import NameNormalizer
from app.deduplicator import DatasetDeduplicator


@pytest.fixture
def deduplicator():
    normalizer = NameNormalizer()
    return DatasetDeduplicator(normalizer)


def test_deduplicate_dataframe(deduplicator):
    """Verify deduplicator processes unique names and maps back accurately."""
    df = pd.DataFrame({
        "Name": [
            "Prion 0.3 (Android)",
            "Prion 0.3 (Android)",
            "TS-LogRhythm Web Console 6",
            "Microsoft 365",
            "Prion 0.3 (Android)",
            "TS-LogRhythm Web Console 6",
        ]
    })

    result_df = deduplicator.process_dataframe(df)

    assert len(result_df) == 6
    assert "Normalized_Application" in result_df.columns
    assert result_df["Normalized_Application"].tolist() == [
        "Prion",
        "Prion",
        "LogRhythm Web Console",
        "Microsoft 365",
        "Prion",
        "LogRhythm Web Console",
    ]


def test_deduplicate_name_list(deduplicator):
    """Verify list deduplication preserves ordering."""
    names = [
        "MapToaster Topo/NZ v11 (reg)",
        "MapToaster Topo/NZ v11 (reg)",
        "Adobe Reader 11.0",
    ]
    normalized = deduplicator.process_name_list(names)
    assert normalized == [
        "MapToaster Topo/NZ",
        "MapToaster Topo/NZ",
        "Adobe Reader",
    ]
