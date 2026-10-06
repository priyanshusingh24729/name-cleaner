"""Unit tests for CheckpointManager persistence and recovery."""

import pytest
from pipeline.checkpoint import CheckpointManager


@pytest.fixture
def checkpoint_mgr(tmp_path):
    cp_file = tmp_path / "test_checkpoint.json"
    return CheckpointManager(checkpoint_path=cp_file)


def test_checkpoint_initial_state(checkpoint_mgr):
    """Initially, checkpoint file does not exist."""
    assert checkpoint_mgr.exists() is False
    data = checkpoint_mgr.load()
    assert data["total_unique"] == 0
    assert data["mappings"] == {}


def test_checkpoint_save_and_load(checkpoint_mgr):
    """Verify saving checkpoint data and reloading accurately."""
    mappings = {
        "TS-H2OMAP Water 7": "H2OMAP Water",
        "Prion 0.3 (Android)": "Prion",
    }
    checkpoint_mgr.save(mappings, total_unique=10)

    assert checkpoint_mgr.exists() is True
    loaded = checkpoint_mgr.load()
    assert loaded["total_unique"] == 10
    assert loaded["processed_count"] == 2
    assert loaded["mappings"]["TS-H2OMAP Water 7"] == "H2OMAP Water"
    assert loaded["mappings"]["Prion 0.3 (Android)"] == "Prion"


def test_checkpoint_reset(checkpoint_mgr):
    """Verify reset properly removes checkpoint file."""
    checkpoint_mgr.save({"App 1": "App"}, total_unique=1)
    assert checkpoint_mgr.exists() is True

    checkpoint_mgr.reset()
    assert checkpoint_mgr.exists() is False
