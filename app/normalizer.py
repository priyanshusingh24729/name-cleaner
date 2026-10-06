"""Core Software Application Name Normalizer (Phase 1 & Phase 2)."""

from pathlib import Path
from typing import Optional, List, Any
import re

from app.result import NormalizationResult
from app.text_cleaner import clean_text
from app.rules import RuleEngine
from app.version_detector import VersionDetector, FOUR_DIGIT_YEAR
from app.metadata_detector import MetadataDetector
from app.candidates import CandidateGenerator
from app.dictionary import CanonicalDictionary


class NameNormalizer:
    """Software Application Name Normalizer with deterministic rules, caching, RapidFuzz matching, and semantic verification."""

    def __init__(
        self,
        rules_path: Optional[Path] = None,
        exceptions_path: Optional[Path] = None,
        db_path: Optional[Path] = None,
        use_cache: bool = True,
        use_fuzzy: bool = True,
        fuzzy_threshold: float = 92.0,
        enable_semantic: bool = False,
        semantic_verifier: Optional[Any] = None,
    ):
        self.rule_engine = RuleEngine(rules_path, exceptions_path)
        self.version_detector = VersionDetector(self.rule_engine)
        self.metadata_detector = MetadataDetector(self.rule_engine)
        self.candidate_generator = CandidateGenerator(self.rule_engine)

        self.use_cache = use_cache
        self.use_fuzzy = use_fuzzy
        self.dictionary = CanonicalDictionary(
            db_path=db_path,
            rule_engine=self.rule_engine,
            fuzzy_threshold=fuzzy_threshold,
        )
        self.enable_semantic = enable_semantic
        self._semantic_verifier = semantic_verifier

    def normalize(self, raw_name: str) -> str:
        """User-facing normalization function. Returns ONLY the canonical product name."""
        return self.normalize_structured(raw_name).normalized_name

    def normalize_structured(self, raw_name: str) -> NormalizationResult:
        """Internal normalization function returning structured metadata and confidence."""
        if not raw_name or not str(raw_name).strip():
            return NormalizationResult(
                original_name=str(raw_name or ""),
                normalized_name="",
                confidence=1.0,
                rules_applied=[],
                changed=False,
                needs_verification=False,
                method="empty_input",
            )

        original_str = str(raw_name)
        cleaned = clean_text(original_str)

        # -------------------------------------------------------------
        # Tier 1: Exact Cache Lookup (L1 Memory / L2 SQLite)
        # -------------------------------------------------------------
        if self.use_cache:
            cached = self.dictionary.cache.get(original_str) or self.dictionary.cache.get(cleaned)
            if cached:
                cached_rules = [r.strip() for r in cached.get("rule_applied", "").split(",") if r.strip()]
                return NormalizationResult(
                    original_name=original_str,
                    normalized_name=cached["normalized_name"],
                    confidence=float(cached["confidence"]),
                    rules_applied=cached_rules or ["exact_cache_hit"],
                    changed=(cached["normalized_name"] != original_str),
                    needs_verification=False,
                    method="exact_cache",
                )

        rules_applied: List[str] = []
        needs_verification = False
        method = "deterministic"

        # -------------------------------------------------------------
        # Tier 2: Check if exact raw/cleaned is an exact canonical preservation
        # -------------------------------------------------------------
        if self.rule_engine.is_preserved_exact(cleaned):
            canonical_name = self.rule_engine.get_canonical_casing(cleaned) or cleaned
            rule_id = "preserve_canonical_name"
            if "2011" in canonical_name or FOUR_DIGIT_YEAR.search(canonical_name):
                rules_applied.append("preserve_year")
            if "Games" in canonical_name or "Windows" in canonical_name:
                rules_applied.append("preserve_product_name")
            else:
                rules_applied.append(rule_id)

            res = NormalizationResult(
                original_name=original_str,
                normalized_name=canonical_name,
                confidence=1.0,
                rules_applied=rules_applied,
                changed=(canonical_name != original_str),
                needs_verification=False,
                method="preset_exception",
            )
            if self.use_cache:
                self.dictionary.cache.set(
                    raw_name=original_str,
                    normalized_name=canonical_name,
                    confidence=1.0,
                    method="preset_exception",
                    rule_applied=",".join(rules_applied),
                    verified=1,
                )
            return res

        current = cleaned

        # 1. Prefix removal (e.g. TS-, Games -)
        current, p_rules = self.metadata_detector.remove_prefixes(current)
        for pr in p_rules:
            if pr == "remove_inventory_prefix":
                rules_applied.append("remove_inventory_prefix")
            elif pr == "remove_games_category_prefix":
                rules_applied.append("remove_games_prefix")
            else:
                rules_applied.append(pr)

        # Multi-pass deterministic cleaning loop for stacked metadata
        # (e.g. "TS-Altova DiffDog 2011 R2 Professional" -> Professional -> R2 -> 2011 -> Altova DiffDog)
        prev_pass_text = None
        pass_idx = 0
        while prev_pass_text != current and pass_idx < 5:
            prev_pass_text = current
            pass_idx += 1

            # 2. Parenthetical metadata classification (e.g. (Android), (reg), (x64), (exe), and last bracket)
            current, paren_rules = self.metadata_detector.remove_parenthetical_metadata(current)
            for r in paren_rules:
                if r not in rules_applied:
                    rules_applied.append(r)

            # 3. License, environment, edition, and release metadata removal
            current, lic_rules = self.metadata_detector.remove_license_metadata(current)
            for r in lic_rules:
                if r not in rules_applied:
                    rules_applied.append(r)

            # 4. OS and platform removal (e.g. 'for Windows')
            current, os_rules = self.metadata_detector.remove_os_and_platform(current)
            for r in os_rules:
                if "remove_os" not in rules_applied:
                    rules_applied.append("remove_os")

            # 5. Architecture & extra metadata removal (e.g. 64-bit, x64)
            current, arch_rules = self.metadata_detector.remove_architecture_and_extra(current)
            for r in arch_rules:
                if "remove_architecture" not in rules_applied:
                    rules_applied.append("remove_architecture")

            # 6. Version detection & conservative year handling
            metadata_stripped = bool(rules_applied) or (current != cleaned)
            current, ver_rules, year_uncertainty = self.version_detector.remove_versions(
                current, metadata_stripped=metadata_stripped
            )
            for r in ver_rules:
                if r not in rules_applied:
                    rules_applied.append(r)

            if year_uncertainty and "preserve_year" not in rules_applied:
                rules_applied.append("preserve_year")
                needs_verification = True

            # Clean trailing separators and excess spaces
            current = re.sub(r"[\s\-–—:;,._/|\\]+$", "", current).strip()
            current = re.sub(r"\s+", " ", current).strip()

        # 7. Post-cleaning exception & canonical casing check
        canonical_override = self.rule_engine.get_canonical_casing(current)
        if canonical_override:
            current = canonical_override

        # 8. Safety against over-normalization
        for preserved in self.rule_engine.preserve_exact:
            canonical_item = self.rule_engine.get_canonical_casing(preserved) or preserved
            if re.search(r"\b" + re.escape(preserved) + r"\b", cleaned, re.IGNORECASE):
                if current.lower() != preserved and len(current) < len(canonical_item):
                    current = canonical_item

        # -------------------------------------------------------------
        # Tier 3: RapidFuzz Candidate Matching against Canonical Dictionary
        # -------------------------------------------------------------
        if self.use_fuzzy and needs_verification:
            candidates = self.candidate_generator.generate(raw_name, current)
            for cand in candidates:
                match_res = self.dictionary.fuzzy_match(cand)
                if match_res:
                    matched_canon, score = match_res
                    current = matched_canon
                    method = "fuzzy_match"
                    rules_applied.append("fuzzy_match")
                    needs_verification = False
                    break

        # -------------------------------------------------------------
        # Tier 4: Confidence calculation & Persistence
        # -------------------------------------------------------------
        changed = (current != original_str)
        if self.rule_engine.is_preserved_exact(current):
            confidence = 1.0
        elif needs_verification:
            confidence = 0.80
        elif method == "fuzzy_match":
            confidence = 0.95
        elif not changed:
            confidence = 1.0
        elif any(r in rules_applied for r in ("remove_version", "remove_os", "remove_registration", "remove_license", "remove_inventory_prefix")):
            confidence = 0.98
        else:
            confidence = 0.90

        res = NormalizationResult(
            original_name=original_str,
            normalized_name=current,
            confidence=confidence,
            rules_applied=rules_applied,
            changed=changed,
            needs_verification=needs_verification,
            method=method,
        )

        if self.use_cache and confidence >= 0.90 and not needs_verification:
            self.dictionary.cache.set(
                raw_name=original_str,
                normalized_name=current,
                confidence=confidence,
                method=method,
                rule_applied=",".join(rules_applied),
                verified=1 if confidence >= 0.98 else 0,
            )

        # -------------------------------------------------------------
        # Tier 5: Semantic Reasoning & LLM Verification (Phase 5)
        # -------------------------------------------------------------
        if self.enable_semantic and needs_verification:
            if self._semantic_verifier is None:
                from semantic.verifier import SemanticVerifier
                self._semantic_verifier = SemanticVerifier(dictionary=self.dictionary)
            res = self._semantic_verifier.verify(raw_name=original_str, initial_result=res)

        return res

    def verify_with_llm(self, raw_name: str) -> NormalizationResult:
        """Run normalization and perform semantic verification cascade using web evidence and LLM."""
        initial = self.normalize_structured(raw_name)
        if self._semantic_verifier is None:
            from semantic.verifier import SemanticVerifier
            self._semantic_verifier = SemanticVerifier(dictionary=self.dictionary)
        return self._semantic_verifier.verify(raw_name=raw_name, initial_result=initial)

    def flush(self) -> None:
        """Flush any pending dictionary cache writes to SQLite."""
        if hasattr(self, "dictionary") and hasattr(self.dictionary, "cache"):
            self.dictionary.cache.flush()
