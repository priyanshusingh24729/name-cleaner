"""Canonical Dictionary and RapidFuzz matching engine."""

from pathlib import Path
from typing import Optional, List, Tuple, Dict, Any
import bisect
import re
from rapidfuzz import fuzz

from storage.sqlite import SQLiteDictionaryStore
from storage.cache import HybridCache
from app.rules import RuleEngine


RE_NUMBERS = re.compile(r"\b\d+(?:\.\d+)*\b")
RE_DASH_UNDERSCORE = re.compile(r"[\-_]+")


class CanonicalDictionary:
    """Manages the canonical dictionary database, memory cache, and fuzzy matching."""

    def __init__(
        self,
        db_path: Optional[Path] = None,
        rule_engine: Optional[RuleEngine] = None,
        fuzzy_threshold: float = 92.0,
    ):
        base_dir = Path(__file__).resolve().parent.parent
        self.db_path = db_path or base_dir / "output" / "canonical_dictionary.db"
        self.store = SQLiteDictionaryStore(self.db_path)
        self.cache = HybridCache(self.store)
        self.rule_engine = rule_engine or RuleEngine()
        self.fuzzy_threshold = fuzzy_threshold
        self._canonical_names_cache: Optional[List[str]] = None
        self._indexed_pool_cache: Optional[List[Tuple[str, str, List[str], str]]] = None
        self._pool_lengths: List[int] = []

        self._seed_preservations()

    def _seed_preservations(self) -> None:
        """Seed SQLite dictionary with explicit preserve items if not already present."""
        if self.store.count()["total"] > 0:
            return

        records = []
        preserves = getattr(self.rule_engine, "preserve_exact_canonical", self.rule_engine.preserve_exact)
        for canonical in preserves:
            display_name = self.rule_engine.get_canonical_casing(canonical) or canonical
            rules = ["preserve_canonical_name"]
            if "2011" in display_name:
                rules.append("preserve_year")
            records.append({
                "raw_name": display_name,
                "normalized_name": display_name,
                "confidence": 1.0,
                "method": "preset_exception",
                "rule_applied": ",".join(rules),
                "source_url": "",
                "verified": 1,
            })
        self.store.bulk_upsert(records)

    def get_canonical_names(self, force_refresh: bool = False) -> List[str]:
        """Get all known verified canonical names."""
        if self._canonical_names_cache is None or force_refresh:
            self._canonical_names_cache = self.store.get_all_canonical_names()
            self._indexed_pool_cache = None
            self._canonical_map = None
        return self._canonical_names_cache

    def get_canonical_map(self, force_refresh: bool = False) -> Dict[str, str]:
        """Get case-insensitive lookup map of known canonical names (O(1))."""
        if getattr(self, "_canonical_map", None) is None or force_refresh:
            names = self.get_canonical_names(force_refresh=force_refresh)
            self._canonical_map = {n.strip().lower(): n.strip() for n in names if n}
        return self._canonical_map

    def lookup_canonical(self, text: str) -> Optional[str]:
        """Fast O(1) exact lookup against known canonical names."""
        if not text:
            return None
        return self.get_canonical_map().get(text.strip().lower())

    def get_indexed_pool(self, force_refresh: bool = False) -> List[Tuple[str, str, List[str], str]]:
        """Get pre-indexed canonical pool sorted by length for high-throughput fuzzy matching."""
        if self._indexed_pool_cache is None or force_refresh:
            names = self.get_canonical_names(force_refresh=force_refresh)
            pool = [
                (
                    canon,
                    canon.strip().lower(),
                    RE_NUMBERS.findall(canon),
                    RE_DASH_UNDERSCORE.sub(" ", canon.strip().lower()),
                )
                for canon in names
            ]
            pool.sort(key=lambda item: len(item[3]))
            self._indexed_pool_cache = pool
            self._pool_lengths = [len(item[3]) for item in pool]
        return self._indexed_pool_cache

    def add_canonical(
        self,
        raw_name: str,
        normalized_name: str,
        confidence: float,
        method: str,
        verified: int = 1,
    ) -> None:
        """Add a verified canonical product mapping."""
        self.cache.set(
            raw_name=raw_name,
            normalized_name=normalized_name,
            confidence=confidence,
            method=method,
            verified=verified,
        )
        self._canonical_names_cache = None  # Invalidate cache
        self._indexed_pool_cache = None
        self._pool_lengths = []

    @staticmethod
    def _extract_numbers(s: str) -> List[str]:
        """Extract all digit sequences from a string."""
        return re.findall(r"\b\d+(?:\.\d+)*\b", s)

    def fuzzy_match(
        self,
        candidate: str,
        threshold: Optional[float] = None,
    ) -> Optional[Tuple[str, float]]:
        """Find best matching canonical product name using conservative RapidFuzz scoring.

        Includes strict numerical consistency validation:
        E.g. 'Windows 10' will never match 'Windows 11'.
        """
        cand_clean = candidate.strip()
        if not cand_clean or len(cand_clean) < 3:
            return None

        # O(1) exact canonical lookup
        exact_match = self.lookup_canonical(cand_clean)
        if exact_match:
            return exact_match, 100.0

        th = threshold if threshold is not None else self.fuzzy_threshold
        indexed_pool = self.get_indexed_pool()
        if not indexed_pool:
            return None

        cand_lower = candidate.strip().lower()
        cand_nums = RE_NUMBERS.findall(candidate)
        cand_norm = RE_DASH_UNDERSCORE.sub(" ", cand_lower)
        cand_len = len(cand_norm)
        max_diff = max(4, int(cand_len * 0.25))

        # Bisect length window for high-throughput candidate pruning
        i_start = bisect.bisect_left(self._pool_lengths, cand_len - max_diff)
        i_end = bisect.bisect_right(self._pool_lengths, cand_len + max_diff)
        search_pool = indexed_pool[i_start:i_end]

        best_name: Optional[str] = None
        best_score: float = 0.0

        for canon, canon_lower, canon_nums, canon_norm in search_pool:
            # Exact case-insensitive match
            if cand_lower == canon_lower:
                return canon, 100.0

            # Strict numerical guard: if candidate has numbers, target must share identical numbers
            if cand_nums != canon_nums:
                # Do not match across distinct numbers/versions
                continue

            # RapidFuzz similarity evaluation
            token_sort = fuzz.token_sort_ratio(cand_norm, canon_norm)
            ratio = fuzz.ratio(cand_norm, canon_norm)
            combined_score = max(token_sort, (token_sort * 0.5) + (ratio * 0.5))

            if combined_score >= th and combined_score > best_score:
                best_score = combined_score
                best_name = canon

        if best_name and best_score >= th:
            return best_name, round(best_score, 2)

        return None
