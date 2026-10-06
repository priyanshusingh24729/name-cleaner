"""Unit tests for BatchPipeline execution, deduplication, and Section 19/20 output separation."""

import pytest
import pandas as pd
from app.normalizer import NameNormalizer
from pipeline.batch_runner import BatchPipeline


@pytest.fixture
def sample_dataframe():
    return pd.DataFrame({
        "Install_ID": [101, 102, 103, 104, 105, 106],
        "Name": [
            "Prion 0.3 (Android)",
            "Prion 0.3 (Android)",
            "TS-LogRhythm Web Console 6",
            "Microsoft 365",
            "TS-LogRhythm Web Console 6",
            "MapToaster Topo/NZ v11",
        ],
        "User": ["alice", "bob", "carol", "dave", "eve", "frank"],
    })


def test_batch_pipeline_deduplication_and_output(tmp_path, sample_dataframe):
    """Verify BatchPipeline processes unique names and exports Section 19 clean dataset."""
    in_csv = tmp_path / "input.csv"
    out_csv = tmp_path / "output_clean.csv"
    audit_csv = tmp_path / "audit.csv"
    checkpoint_json = tmp_path / "checkpoint.json"

    sample_dataframe.to_csv(in_csv, index=False)

    normalizer = NameNormalizer(db_path=tmp_path / "dict.db")
    pipeline = BatchPipeline(
        normalizer=normalizer,
        checkpoint_path=checkpoint_json,
        audit_path=audit_csv,
        batch_size=2,
    )

    stats = pipeline.process_file(
        input_path=in_csv,
        output_path=out_csv,
        name_col="Name",
    )

    assert stats["total_rows"] == 6
    assert stats["total_unique"] == 4  # 4 unique names from 6 rows

    # 1. Verify Primary Dataset (Section 19 Compliance)
    df_out = pd.read_csv(out_csv)
    assert len(df_out) == 6
    assert "Normalized_Application" in df_out.columns

    # Must preserve original columns
    assert "Install_ID" in df_out.columns
    assert "User" in df_out.columns

    # Must NOT have diagnostic columns
    for forbidden in ["confidence", "method", "rule_applied", "rules_applied", "needs_verification"]:
        assert forbidden not in df_out.columns

    # Verify normalized values
    assert df_out["Normalized_Application"].tolist() == [
        "Prion",
        "Prion",
        "LogRhythm Web Console",
        "Microsoft 365",
        "LogRhythm Web Console",
        "MapToaster Topo/NZ",
    ]

    # 2. Verify Audit Dataset (Section 20 Compliance)
    df_audit = pd.read_csv(audit_csv)
    assert len(df_audit) == 4  # 4 unique names audited
    assert "raw_name" in df_audit.columns
    assert "confidence" in df_audit.columns
    assert "method" in df_audit.columns


def test_batch_pipeline_resume_from_checkpoint(tmp_path, sample_dataframe):
    """Verify BatchPipeline skips already processed names when checkpoint exists."""
    in_csv = tmp_path / "input_resume.csv"
    out_csv = tmp_path / "output_resume.csv"
    audit_csv = tmp_path / "audit_resume.csv"
    checkpoint_json = tmp_path / "checkpoint_resume.json"

    sample_dataframe.to_csv(in_csv, index=False)

    normalizer = NameNormalizer(db_path=tmp_path / "dict.db")
    pipeline = BatchPipeline(
        normalizer=normalizer,
        checkpoint_path=checkpoint_json,
        audit_path=audit_csv,
    )

    # Pre-populate checkpoint with 2 completed names
    pipeline.checkpoint_mgr.save(
        {
            "Prion 0.3 (Android)": "Prion",
            "Microsoft 365": "Microsoft 365",
        },
        total_unique=4,
    )

    stats = pipeline.process_file(
        input_path=in_csv,
        output_path=out_csv,
        name_col="Name",
    )

    df_out = pd.read_csv(out_csv)
    assert len(df_out) == 6
    assert df_out["Normalized_Application"].tolist() == [
        "Prion",
        "Prion",
        "LogRhythm Web Console",
        "Microsoft 365",
        "LogRhythm Web Console",
        "MapToaster Topo/NZ",
    ]
