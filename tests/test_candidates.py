"""Tests for candidate canonical name generator."""

import pytest
from app.candidates import CandidateGenerator
from app.rules import RuleEngine


@pytest.fixture
def candidate_gen():
    return CandidateGenerator(RuleEngine())


def test_maptoaster_candidates(candidate_gen):
    """Section 11 specification test: MapToaster candidate generation."""
    raw = "MapToaster Topo/NZ v11 (reg)"
    norm = "MapToaster Topo/NZ"
    cands = candidate_gen.generate(raw, norm)

    assert "MapToaster Topo/NZ" in cands
    assert "MapToaster Topo/NZ v11" in cands
    assert "MapToaster Topo/NZ 11" in cands


def test_prion_candidates(candidate_gen):
    """Section 11 specification test: Prion candidate generation."""
    raw = "Prion 0.3 (Android)"
    norm = "Prion"
    cands = candidate_gen.generate(raw, norm)

    assert "Prion" in cands
    assert cands[0] == "Prion"


def test_symbolbibliothek_candidates(candidate_gen):
    """Section 11 specification test: Symbolbibliothek candidate generation."""
    raw = "Symbolbibliothek Elektrotechnik 2011"
    norm = "Symbolbibliothek Elektrotechnik 2011"
    cands = candidate_gen.generate(raw, norm)

    assert "Symbolbibliothek Elektrotechnik 2011" in cands
