"""Tests for hybrid L1/L2 cache operations."""

import pytest
from storage.cache import HybridCache


@pytest.fixture
def cache(tmp_path):
    """Fixture providing a temporary HybridCache."""
    db_path = tmp_path / "test_cache.db"
    return HybridCache(db_path, max_memory_entries=10)


def test_cache_miss_returns_none(cache):
    """Unknown key returns None."""
    assert cache.get("Unknown Software") is None


def test_cache_set_and_l1_hit(cache):
    """Entry is accessible immediately from memory."""
    cache.set(
        raw_name="Prion 0.3 (Android)",
        normalized_name="Prion",
        confidence=0.98,
        method="deterministic",
        rule_applied="remove_os,remove_version",
        verified=1,
    )

    # In-memory retrieval
    res = cache.get("Prion 0.3 (Android)")
    assert res is not None
    assert res["normalized_name"] == "Prion"
    assert res["confidence"] == 0.98


def test_cache_l2_persistence_after_memory_clear(cache):
    """Entry survives L1 cache clearing by reading from SQLite L2 store."""
    cache.set(
        raw_name="Software 1.0",
        normalized_name="Software",
        confidence=0.95,
        method="deterministic",
    )

    # Clear L1 memory
    cache.clear_memory()
    assert len(cache._l1_cache) == 0

    # Retrieval reloads from L2 SQLite and repopulates L1
    res = cache.get("Software 1.0")
    assert res is not None
    assert res["normalized_name"] == "Software"
    assert "Software 1.0" in cache._l1_cache
