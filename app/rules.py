"""Configurable rule loader and regex pattern engine."""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Set, Optional, Any
import yaml

try:
    import regex as re
except ImportError:
    import re


@dataclass
class Rule:
    """Compiled normalization rule."""
    id: str
    pattern: re.Pattern
    description: str


class RuleEngine:
    """Loads YAML rules and compiles regex patterns with safety checks."""

    def __init__(
        self,
        rules_path: Optional[Path] = None,
        exceptions_path: Optional[Path] = None,
    ):
        base_dir = Path(__file__).resolve().parent.parent
        self.rules_path = rules_path or base_dir / "config" / "normalization_rules.yaml"
        self.exceptions_path = exceptions_path or base_dir / "config" / "exceptions.yaml"

        self.prefix_rules: List[Rule] = []
        self.suffix_rules: List[Rule] = []
        self.registration_rules: List[Rule] = []
        self.os_platform_rules: List[Rule] = []
        self.architecture_rules: List[Rule] = []
        self.version_rules: List[Rule] = []
        self.year_rules: List[Rule] = []

        self.preserve_exact: Set[str] = set()
        self.preserve_tokens: Set[str] = set()
        self.preserve_trailing_numbers: Set[str] = set()
        self.canonical_casing: Dict[str, str] = {}

        self.load_rules()
        self.load_exceptions()

    def _compile_rule_list(self, rule_dicts: List[Dict[str, str]]) -> List[Rule]:
        compiled = []
        for r in rule_dicts:
            rule_id = r.get("id", "")
            raw_pat = r.get("pattern", "")
            desc = r.get("description", "")
            if raw_pat:
                compiled.append(Rule(
                    id=rule_id,
                    pattern=re.compile(raw_pat, re.IGNORECASE),
                    description=desc,
                ))
        return compiled

    def load_rules(self) -> None:
        """Load and compile normalization patterns from YAML."""
        if not self.rules_path.exists():
            return

        with open(self.rules_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        self.prefix_rules = self._compile_rule_list(data.get("prefix_rules", []))
        self.suffix_rules = self._compile_rule_list(data.get("suffix_rules", []))
        self.registration_rules = self._compile_rule_list(data.get("registration_rules", []))
        self.os_platform_rules = self._compile_rule_list(data.get("os_platform_rules", []))
        self.architecture_rules = self._compile_rule_list(data.get("architecture_rules", []))
        self.version_rules = self._compile_rule_list(data.get("version_rules", []))
        self.year_rules = self._compile_rule_list(data.get("year_rules", []))

    def load_exceptions(self) -> None:
        """Load preservation lists and canonical casing from YAML."""
        if not self.exceptions_path.exists():
            return

        with open(self.exceptions_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        # Preserve exact matches (lowercased for case-insensitive check, original for display)
        raw_preserves = [item.strip() for item in data.get("preserve", []) if item]
        self.preserve_exact = {item.lower() for item in raw_preserves}
        self.preserve_exact_canonical = raw_preserves
        self.preserve_tokens = {item.strip().lower() for item in data.get("preserve_tokens", []) if item}
        self.preserve_trailing_numbers = {str(item).strip() for item in data.get("preserve_trailing_numbers", []) if item}

        casing = data.get("canonical_casing", {})
        self.canonical_casing = {k.strip().lower(): v.strip() for k, v in casing.items() if k and v}
        for item in raw_preserves:
            if item.lower() not in self.canonical_casing:
                self.canonical_casing[item.lower()] = item

    def is_preserved_exact(self, text: str) -> bool:
        """Check if cleaned text matches an exact preserved canonical name."""
        return text.strip().lower() in self.preserve_exact

    def get_canonical_casing(self, text: str) -> Optional[str]:
        """Lookup canonical casing for text if configured."""
        return self.canonical_casing.get(text.strip().lower())
