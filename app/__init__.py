"""Software Application Name Normalizer - Core Package (Phases 1 & 2)."""

from app.normalizer import NameNormalizer
from app.result import NormalizationResult
from app.text_cleaner import clean_text
from app.rules import RuleEngine
from app.candidates import CandidateGenerator
from app.dictionary import CanonicalDictionary
from app.deduplicator import DatasetDeduplicator

__all__ = [
    "NameNormalizer",
    "NormalizationResult",
    "clean_text",
    "RuleEngine",
    "CandidateGenerator",
    "CanonicalDictionary",
    "DatasetDeduplicator",
]
