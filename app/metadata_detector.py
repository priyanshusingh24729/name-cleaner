"""Metadata detector for prefixes, suffixes, OS/platforms, licenses, and registration."""

import re
from typing import Tuple, List
from app.rules import RuleEngine

# Parenthetical content extractor: extracts "(...)"
PARENTHETICAL = re.compile(r"\(([^)]+)\)")

# Specific categories of removable parenthetical content
PAREN_OS = re.compile(
    r"^(?:Android|iOS|Linux|Ubuntu|Unix|HP-?UX|AIX|Solaris|SunOS|FreeBSD|OpenBSD|Mac|macOS|OS\s*X|Windows(?:\s*(?:10|11|Server|XP|Vista|7|8(?:\.1)?))?|NL)$",
    re.IGNORECASE,
)
PAREN_REG = re.compile(r"^(?:reg|reg\.|registered|registration)$", re.IGNORECASE)
PAREN_ARCH = re.compile(r"^(?:64-?bit|32-?bit|x86_64|x86|x64)$", re.IGNORECASE)
PAREN_LICENSE = re.compile(r"^(?:trial|evaluation|demo|network\s+licen[sc]e|standalone\s+licen[sc]e)$", re.IGNORECASE)
PAREN_PACKAGING = re.compile(r"^(?:exe|installer|setup|portable)$", re.IGNORECASE)
PAREN_VERSION = re.compile(r"^v?\d+(?:\.\d+)*(?:[a-zA-Z\-_]\w*)?$", re.IGNORECASE)

# Standalone 'for <OS>'
FOR_OS = re.compile(
    r"\s+for\s+(?:Android|iOS|Linux|Ubuntu|Unix|HP-?UX|AIX|Solaris|SunOS|FreeBSD|OpenBSD|Mac|macOS|OS\s*X|Windows(?:\s*(?:10|11|Server|XP|Vista|7|8(?:\.1)?))?)\b",
    re.IGNORECASE,
)

# Obvious architecture words: 64-bit, 32-bit, x64, x86
ARCH_WORDS = re.compile(r"\b(?:64-?bit|32-?bit|x86_64|x86|x64)\b", re.IGNORECASE)


class MetadataDetector:
    """Classifies and safely removes confirmed non-product metadata."""

    def __init__(self, rule_engine: RuleEngine):
        self.rule_engine = rule_engine

    def remove_prefixes(self, text: str) -> Tuple[str, List[str]]:
        """Remove inventory or category prefixes like 'TS-' or 'Games -'."""
        rules_applied = []
        current = text

        for rule in self.rule_engine.prefix_rules:
            if rule.pattern.search(current):
                current = rule.pattern.sub("", current).strip()
                rules_applied.append(rule.id)

        return current, rules_applied

    def remove_parenthetical_metadata(self, text: str) -> Tuple[str, List[str]]:
        """Classify and remove parenthetical content confirmed to be metadata,
        and remove everything from the last bracket/parenthesis to the end
        unless it is an official product identifier (e.g. AutoCAD (LT)).
        """
        rules_applied = []
        current = text

        # 1. Check for trailing brackets from the last bracket to the end: e.g. (reg), (Trial), (QA)
        trailing_bracket = re.search(r"[\s\-–—]*[\(\[\{]([^\)\]\}]+)[\)\]\}][^\(\[\{]*$", current)
        while trailing_bracket:
            inner = trailing_bracket.group(1).strip()
            # Check if inner content is an official product identifier
            is_preserved = (
                inner.upper() in ["LT", "SAP", "R/3"]
                or inner in self.rule_engine.preserve_tokens
                or any(inner.lower() == p.lower() for p in self.rule_engine.preserve_tokens)
                or self.rule_engine.is_preserved_exact(current)
            )
            if is_preserved:
                break

            current = current[:trailing_bracket.start()].strip()
            if "remove_bracket_metadata" not in rules_applied:
                rules_applied.append("remove_bracket_metadata")
            trailing_bracket = re.search(r"[\s\-–—]*[\(\[\{]([^\)\]\}]+)[\)\]\}][^\(\[\{]*$", current)

        # 2. Check any remaining parentheticals for metadata types
        matches = list(PARENTHETICAL.finditer(current))
        if matches:
            to_remove = []
            for match in matches:
                inner = match.group(1).strip()
                full_span = match.group(0)

                # Check if this parenthetical matches confirmed metadata types
                if PAREN_OS.match(inner):
                    to_remove.append((full_span, "remove_os"))
                elif PAREN_REG.match(inner):
                    to_remove.append((full_span, "remove_registration"))
                elif PAREN_ARCH.match(inner):
                    to_remove.append((full_span, "remove_architecture"))
                elif PAREN_LICENSE.match(inner):
                    to_remove.append((full_span, "remove_license"))
                elif PAREN_PACKAGING.match(inner):
                    to_remove.append((full_span, "remove_packaging_metadata"))
                elif PAREN_VERSION.match(inner):
                    to_remove.append((full_span, "remove_version"))

            for span_text, rule_id in to_remove:
                current = current.replace(span_text, " ")
                if rule_id not in rules_applied:
                    rules_applied.append(rule_id)

        current = re.sub(r"\s+", " ", current).strip()
        return current, rules_applied

    def remove_license_metadata(self, text: str) -> Tuple[str, List[str]]:
        """Remove license, environment, edition, and release suffixes (multi-pass)."""
        rules_applied = []
        current = text

        # Multi-pass removal for stacked suffixes (e.g. "R2 Professional" -> "R2" -> "")
        changed = True
        passes = 0
        while changed and passes < 5:
            changed = False
            passes += 1
            for rule in self.rule_engine.suffix_rules:
                if rule.pattern.search(current):
                    current = rule.pattern.sub("", current).strip()
                    if rule.id not in rules_applied:
                        rules_applied.append(rule.id)
                    changed = True

        return current, rules_applied

    def remove_os_and_platform(self, text: str) -> Tuple[str, List[str]]:
        """Remove 'for Windows' and other non-parenthetical platform metadata."""
        rules_applied = []
        current = text

        if FOR_OS.search(current):
            current = FOR_OS.sub("", current).strip()
            rules_applied.append("remove_os")

        return current, rules_applied

    def remove_architecture_and_extra(self, text: str) -> Tuple[str, List[str]]:
        """Remove architecture tags and packaging metadata."""
        rules_applied = []
        current = text

        for rule in self.rule_engine.architecture_rules:
            if rule.pattern.search(current):
                current = rule.pattern.sub("", current).strip()
                if "remove_architecture" not in rules_applied:
                    rules_applied.append("remove_architecture")

        return current, rules_applied
