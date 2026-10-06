"""Candidate canonical name generation engine."""

from typing import List
import re

from app.text_cleaner import clean_text
from app.rules import RuleEngine
from app.metadata_detector import MetadataDetector


class CandidateGenerator:
    """Generates ordered plausible canonical candidate strings from a raw application name."""

    def __init__(self, rule_engine: RuleEngine):
        self.rule_engine = rule_engine
        self.metadata_detector = MetadataDetector(rule_engine)

    def generate(self, raw_name: str, deterministic_normalized: str = "") -> List[str]:
        """Generate deduplicated list of candidate canonical names.

        Example:
            For 'MapToaster Topo/NZ v11 (reg)':
            Candidates:
            - 'MapToaster Topo/NZ'
            - 'MapToaster Topo/NZ v11'
            - 'MapToaster Topo/NZ 11'
        """
        candidates: List[str] = []
        cleaned_raw = clean_text(raw_name)

        def add_candidate(c: str):
            c_str = clean_text(c)
            if c_str and c_str not in candidates:
                candidates.append(c_str)

        # 1. Primary candidate: Output of deterministic normalizer
        if deterministic_normalized:
            add_candidate(deterministic_normalized)

        # 2. Candidate with prefixes & metadata removed, but preserving version tag
        without_prefix, _ = self.metadata_detector.remove_prefixes(cleaned_raw)
        without_meta, _ = self.metadata_detector.remove_parenthetical_metadata(without_prefix)
        without_lic, _ = self.metadata_detector.remove_license_metadata(without_meta)
        without_os, _ = self.metadata_detector.remove_os_and_platform(without_lic)
        without_arch, _ = self.metadata_detector.remove_architecture_and_extra(without_os)

        partial_norm = without_arch.strip()
        add_candidate(partial_norm)

        # 3. If candidate has 'v<number>' at end, generate alternate with integer ('v11' -> '11')
        v_match = re.search(r"\bv(\d+(?:\.\d+)*)$", partial_norm, re.IGNORECASE)
        if v_match:
            cand_int = re.sub(r"\bv(\d+(?:\.\d+)*)$", r"\1", partial_norm, flags=re.IGNORECASE)
            add_candidate(cand_int)

        # 4. If candidate has integer at end, generate alternate with 'v' ('11' -> 'v11')
        int_match = re.search(r"\s+(\d+(?:\.\d+)*)$", partial_norm)
        if int_match:
            cand_v = re.sub(r"\s+(\d+(?:\.\d+)*)$", r" v\1", partial_norm)
            add_candidate(cand_v)

        # 5. Cleaned raw name itself
        add_candidate(cleaned_raw)

        return candidates
