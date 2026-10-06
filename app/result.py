"""Normalization result data model."""

from dataclasses import dataclass, field
from typing import List, Dict, Any


@dataclass
class NormalizationResult:
    """Structured result of the software name normalization process."""

    original_name: str
    normalized_name: str
    confidence: float
    rules_applied: List[str] = field(default_factory=list)
    changed: bool = False
    needs_verification: bool = False
    method: str = "deterministic"

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary for serialization / auditing."""
        return {
            "original_name": self.original_name,
            "normalized_name": self.normalized_name,
            "confidence": round(self.confidence, 4),
            "rules_applied": list(self.rules_applied),
            "changed": self.changed,
            "needs_verification": self.needs_verification,
            "method": self.method,
        }

    @property
    def raw(self) -> str:
        """Alias for original_name."""
        return self.original_name

    @property
    def canonical(self) -> str:
        """Alias for normalized_name."""
        return self.normalized_name

    def __str__(self) -> str:
        """String representation returns only the canonical normalized name."""
        return self.normalized_name
