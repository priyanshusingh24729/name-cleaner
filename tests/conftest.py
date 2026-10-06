"""Pytest fixtures for name normalizer tests."""

import pytest
from app.normalizer import NameNormalizer


@pytest.fixture(scope="session")
def normalizer():
    """Shared NameNormalizer instance."""
    return NameNormalizer()
