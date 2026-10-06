try:
    import regex as re
except ImportError:
    import re
from typing import Tuple, List
from app.rules import RuleEngine

# Semantic / dotted versions: 0.3, 1.0, 2.5.1, 11.0, 10.0.19041
DOTTED_VERSION = re.compile(r"(?:\s+|^|\b)v?(\d+(?:\.\d+)+(?:[a-zA-Z\-_]\w*)?)(?=\s|$|\))", re.IGNORECASE)

# v-prefixed versions: v11, v4.2, v12.5
V_PREFIX_VERSION = re.compile(r"(?:\s+|^|\b)v(\d+(?:\.\d+)*)(?=\s|$|\))", re.IGNORECASE)

# Version keywords: Version 11, Ver. 4.2, Release 4, Rev 3, Build 123
KEYWORD_VERSION = re.compile(
    r"\b(?:version|ver\.?|release|rev\.?|build)\s*v?(\d+(?:\.\d+)*)\b",
    re.IGNORECASE,
)

# Year pattern: 1980 to 2040
FOUR_DIGIT_YEAR = re.compile(r"\b(19\d{2}|20[0-4]\d)\b")

# Trailing integer version: 1-3 digits at the end of a string
TRAILING_INT = re.compile(r"\s+(\d{1,3})$")


class VersionDetector:
    """Detects and cleans version numbers, builds, releases, and handles years conservatively."""

    def __init__(self, rule_engine: RuleEngine):
        self.rule_engine = rule_engine

    def remove_versions(self, text: str, metadata_stripped: bool = False) -> Tuple[str, List[str], bool]:
        """Detect and remove version metadata from software name text.

        Returns:
            (cleaned_text, rules_applied, year_uncertainty)
        """
        rules_applied: List[str] = []
        year_uncertainty = False
        current = text

        # 1. Check keyword versions: "Version 11", "Ver. 4.2", "Release 4", "Build 123"
        if KEYWORD_VERSION.search(current):
            match = KEYWORD_VERSION.search(current)
            if match:
                current = KEYWORD_VERSION.sub("", current).strip()
                rules_applied.append("remove_version_keyword")

        # 2. Check dotted versions: "0.3", "1.0", "2.5.1", "11.0"
        dotted_match = DOTTED_VERSION.search(current)
        if dotted_match:
            val = dotted_match.group(1)
            # Avoid stripping if protected
            if val not in self.rule_engine.preserve_trailing_numbers and val not in self.rule_engine.preserve_tokens:
                current = DOTTED_VERSION.sub("", current).strip()
                rules_applied.append("remove_dotted_version")

        # 3. Check v-prefixed versions: "v11", "v4.2"
        v_match = V_PREFIX_VERSION.search(current)
        if v_match:
            current = V_PREFIX_VERSION.sub("", current).strip()
            rules_applied.append("remove_v_prefix")

        # 4. Contextual year removal vs conservative preservation
        # First check contextual year rules from config (e.g. Autodesk products)
        for yr_rule in self.rule_engine.year_rules:
            if yr_rule.pattern.search(current):
                current = yr_rule.pattern.sub("", current).strip()
                rules_applied.append(yr_rule.id)

        # If a four digit year still remains:
        year_match = FOUR_DIGIT_YEAR.search(current)
        if year_match:
            year_val = year_match.group(1)
            # If it is explicitly preserved, do nothing
            if self.rule_engine.is_preserved_exact(current) or year_val in self.rule_engine.preserve_trailing_numbers:
                pass
            elif metadata_stripped or (current.endswith(year_val) and bool(self.rule_engine.get_canonical_casing(current[:-len(year_val)].strip()))):
                # When accompanied by stripped metadata or known canonical name exists without year,
                # the year is a release year and not part of the official product name
                candidate_without_year = re.sub(r"(?:\s+|-)\b" + year_val + r"\b\s*$", "", current).strip()
                if len(candidate_without_year) >= 3 and not self.rule_engine.is_preserved_exact(current):
                    current = candidate_without_year
                    rules_applied.append("remove_year")
            else:
                # If year is standalone without accompanying metadata, mark year_uncertainty
                year_uncertainty = True

        # 5. Trailing integer check (e.g., "LogRhythm Web Console 6" -> "LogRhythm Web Console")
        # Ensure we do NOT remove preserved numbers like 365 or 2011
        trailing_match = TRAILING_INT.search(current)
        if trailing_match:
            num = trailing_match.group(1)
            if num in self.rule_engine.preserve_trailing_numbers:
                pass
            elif self.rule_engine.is_preserved_exact(current):
                pass
            elif len(num) == 4 and (1900 <= int(num) <= 2099):
                # Handled in year detection
                pass
            else:
                candidate = TRAILING_INT.sub("", current).strip()
                if len(candidate) >= 3 and not self.rule_engine.is_preserved_exact(current):
                    current = candidate
                    rules_applied.append("remove_trailing_integer_version")

        # Clean any consecutive whitespace left after version removals
        current = re.sub(r"\s+", " ", current).strip()
        return current, rules_applied, year_uncertainty
