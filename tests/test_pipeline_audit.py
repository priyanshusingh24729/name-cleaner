"""Unit tests for Section 20 normalization_audit.csv writer."""

import csv
import pytest
from app.result import NormalizationResult
from pipeline.audit import AuditWriter, AUDIT_COLUMNS


@pytest.fixture
def audit_writer(tmp_path):
    audit_file = tmp_path / "test_audit.csv"
    return AuditWriter(audit_path=audit_file)


def test_audit_file_header(audit_writer):
    """Audit CSV must be initialized with the exact columns required by Section 20."""
    with open(audit_writer.audit_path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
    assert header == AUDIT_COLUMNS
    assert header == [
        "raw_name",
        "normalized_name",
        "confidence",
        "method",
        "rule_applied",
        "search_engine",
        "source_url",
        "verified",
    ]


def test_audit_write_record(audit_writer):
    """Writing a single record formats fields properly."""
    res = NormalizationResult(
        original_name="TS-LogRhythm Web Console 6",
        normalized_name="LogRhythm Web Console",
        confidence=0.98,
        rules_applied=["remove_inventory_prefix", "remove_version"],
        changed=True,
        needs_verification=False,
        method="deterministic",
    )
    audit_writer.write_record(res)

    with open(audit_writer.audit_path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)

    assert len(rows) == 2  # header + 1 row
    assert rows[1][0] == "TS-LogRhythm Web Console 6"
    assert rows[1][1] == "LogRhythm Web Console"
    assert rows[1][2] == "0.9800"
    assert "remove_inventory_prefix" in rows[1][4]
    assert rows[1][7] == "1"


def test_audit_write_batch(audit_writer):
    """Batch write appends multiple records in a single disk operation."""
    records = [
        {
            "raw_name": "App 1",
            "normalized_name": "App",
            "confidence": "1.0000",
            "method": "deterministic",
            "rule_applied": "remove_version",
            "search_engine": "",
            "source_url": "",
            "verified": "1",
        },
        {
            "raw_name": "App 2",
            "normalized_name": "App",
            "confidence": "1.0000",
            "method": "deterministic",
            "rule_applied": "remove_version",
            "search_engine": "",
            "source_url": "",
            "verified": "1",
        },
    ]
    audit_writer.write_batch(records)

    with open(audit_writer.audit_path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)

    assert len(rows) == 3  # header + 2 rows
