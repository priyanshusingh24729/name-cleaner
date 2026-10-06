"""Semantic verification orchestrator combining search, crawler, and LLM reasoning."""

from pathlib import Path
from typing import Optional, List, Dict, Any
import yaml

from app.result import NormalizationResult
from app.candidates import CandidateGenerator
from app.dictionary import CanonicalDictionary
from search.manager import SearchManager
from crawler.crawler import WebCrawler, CrawlEvidence
from semantic.client import BaseLLMClient, create_llm_client
from semantic.prompt import PromptBuilder
from semantic.guards import AntiHallucinationGuard


class SemanticVerifier:
    """Orchestrates search, web crawling, and LLM reasoning to resolve ambiguous application names."""

    def __init__(
        self,
        config_path: Optional[Path] = None,
        llm_client: Optional[BaseLLMClient] = None,
        search_manager: Optional[SearchManager] = None,
        crawler: Optional[WebCrawler] = None,
        dictionary: Optional[CanonicalDictionary] = None,
    ):
        base_dir = Path(__file__).resolve().parent.parent
        self.config_path = config_path or base_dir / "config" / "semantic.yaml"
        self.config: Dict[str, Any] = self._load_config()

        self.llm_client = llm_client or create_llm_client(self.config)
        self.search_manager = search_manager or SearchManager()
        self.crawler = crawler or WebCrawler()
        self.dictionary = dictionary or CanonicalDictionary()
        self.candidate_generator = CandidateGenerator(rule_engine=self.dictionary.rule_engine)
        guard_cfg = self.config.get("guards", {})
        self.guard = AntiHallucinationGuard(
            min_token_overlap=guard_cfg.get("min_token_overlap", 0.3)
        )

    def _load_config(self) -> Dict[str, Any]:
        if not self.config_path.exists():
            return {}
        with open(self.config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    def verify(
        self,
        raw_name: str,
        initial_result: Optional[NormalizationResult] = None,
        candidates: Optional[List[str]] = None,
    ) -> NormalizationResult:
        """Resolve ambiguous or uncertain application name through web evidence and LLM reasoning."""
        # 1. Candidate hypotheses
        initial_norm = initial_result.normalized_name if initial_result else ""
        if not candidates:
            candidates = self.candidate_generator.generate(raw_name, initial_norm)
        if initial_norm and initial_norm not in candidates:
            candidates.insert(0, initial_norm)

        # 2. Gather web evidence (Search -> Crawl)
        search_results = self.search_manager.search(raw_name, max_results=4)
        crawl_evidence: List[CrawlEvidence] = []
        if search_results:
            crawl_evidence = self.crawler.crawl_results(search_results, max_pages=2)

        # 3. Build structured prompt adhering to Section 18
        prompt_msgs = PromptBuilder.build_verification_prompt(
            raw_name=raw_name,
            candidates=candidates,
            search_evidence=search_results,
            crawl_evidence=crawl_evidence,
        )

        # 4. Invoke LLM
        raw_response = self.llm_client.complete(prompt_msgs)

        # 5. Sanitize & Validate output
        sanitized = self.guard.sanitize(raw_response)
        evidence_titles = [ev.clean_title for ev in crawl_evidence if ev.clean_title]
        is_valid = self.guard.validate(
            cleaned_response=sanitized,
            raw_name=raw_name,
            candidates=candidates,
            web_evidence_titles=evidence_titles,
        )

        prev_rules = initial_result.rules_applied if initial_result else []

        # 6. Resolve decision & calculate confidence per Section 12
        if is_valid and sanitized:
            canonical = sanitized
            has_official_source = any(ev.is_official and ev.authority_score >= 0.95 for ev in crawl_evidence)

            conf_cfg = self.config.get("confidence", {})
            if has_official_source:
                confidence = conf_cfg.get("official_vendor_verified", 0.90)
                method = "llm_official_verified"
            elif crawl_evidence or search_results:
                confidence = conf_cfg.get("search_evidence_verified", 0.78)
                method = "llm_search_verified"
            else:
                confidence = 0.75
                method = "llm_heuristic_verified"

            # Cache into persistent local SQLite canonical dictionary (Section 13) and L1 memory cache
            source_url = crawl_evidence[0].url if crawl_evidence else ""
            self.dictionary.cache.set(
                raw_name=raw_name,
                normalized_name=canonical,
                confidence=confidence,
                method=method,
                rule_applied=",".join(prev_rules + [method]),
                source_url=source_url,
                verified=1,
            )

            return NormalizationResult(
                original_name=raw_name,
                normalized_name=canonical,
                confidence=confidence,
                method=method,
                rules_applied=prev_rules + [method],
                changed=(canonical != raw_name),
                needs_verification=False,
            )

        # 7. Safe Fallback Guard (Section 18)
        fallback_canonical = initial_result.normalized_name if initial_result else raw_name
        return NormalizationResult(
            original_name=raw_name,
            normalized_name=fallback_canonical,
            confidence=self.config.get("confidence", {}).get("unverified_fallback", 0.65),
            method="unverified_fallback",
            rules_applied=prev_rules + ["llm_validation_failed"],
            changed=(fallback_canonical != raw_name),
            needs_verification=True,
        )
