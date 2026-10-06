"""Tests for SQLite canonical dictionary storage."""

import pytest
from storage.sqlite import SQLiteDictionaryStore


@pytest.fixture
def store(tmp_path):
    """Fixture providing a fresh SQLite store for each test."""
    db_path = tmp_path / "test_dict.db"
    return SQLiteDictionaryStore(db_path)


def test_sqlite_init_and_empty_count(store):
    """Database initializes properly with 0 rows."""
    counts = store.count()
    assert counts["total"] == 0
    assert counts["verified"] == 0


def test_upsert_and_get(store):
    """Test insertion and retrieval of record."""
    store.upsert(
        raw_name="Prion 0.3 (Android)",
        normalized_name="Prion",
        confidence=0.98,
        method="deterministic",
        rule_applied="remove_os,remove_version",
        verified=1,
    )

    record = store.get("Prion 0.3 (Android)")
    assert record is not None
    assert record["raw_name"] == "Prion 0.3 (Android)"
    assert record["normalized_name"] == "Prion"
    assert record["confidence"] == 0.98
    assert record["method"] == "deterministic"
    assert record["rule_applied"] == "remove_os,remove_version"
    assert record["verified"] == 1


def test_upsert_on_conflict_updates(store):
    """Updating an existing raw_name replaces fields without duplicating."""
    store.upsert("App v1", "App", 0.90, "rule", verified=0)
    assert store.count()["total"] == 1
    assert store.count()["verified"] == 0

    # Upsert with verified=1 and higher confidence
    store.upsert("App v1", "App Canonical", 0.99, "manual", verified=1)
    assert store.count()["total"] == 1
    assert store.count()["verified"] == 1

    updated = store.get("App v1")
    assert updated["normalized_name"] == "App Canonical"
    assert updated["confidence"] == 0.99


def test_bulk_upsert_and_verified_list(store):
    """Bulk upsert creates multiple entries and verifies query."""
    records = [
        {"raw_name": "App A 1.0", "normalized_name": "App A", "confidence": 0.95, "method": "rule", "verified": 1},
        {"raw_name": "App B 2.0", "normalized_name": "App B", "confidence": 0.95, "method": "rule", "verified": 1},
        {"raw_name": "App C 3.0", "normalized_name": "App C", "confidence": 0.80, "method": "rule", "verified": 0},
    ]
    count = store.bulk_upsert(records)
    assert count == 3
    assert store.count()["total"] == 3
    assert store.count()["verified"] == 2

    verified_names = store.get_verified_canonical_names()
    assert "App A" in verified_names
    assert "App B" in verified_names
    assert "App C" not in verified_names
