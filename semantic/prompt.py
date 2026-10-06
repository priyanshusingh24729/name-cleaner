"""Structured prompt builder for semantic LLM verification adhering to Section 18."""

from typing import List, Optional, Dict, Any
from crawler.crawler import CrawlEvidence
from search.base import SearchResult


SYSTEM_PROMPT = """You are an expert Software Product Canonical Name Resolver.
Your job is to determine the exact, canonical software application name from raw inventory records, candidate names, search results, and official web evidence.

CRITICAL RULES:
1. Return ONLY the canonical application name.
2. Do not explain your answer. Do not include markdown quotes, backticks, or punctuation.
3. Do not invent a product.
4. Do not remove information unless it is clearly metadata.
5. PRESERVE years when they are part of the official product name (e.g. "Symbolbibliothek Elektrotechnik 2011", "Windows Server 2022").
6. PRESERVE product editions (e.g. "Standard", "Enterprise", "Datacenter", "Pro") when they are part of the canonical name.
7. REMOVE version numbers, build numbers, release numbers, OS metadata (e.g. "for Windows", "(Mac)", "(Android)"), license tokens (e.g. "Network License", "(reg)"), and inventory prefixes (e.g. "TS-", "Games -").
8. Prefer evidence from official vendor domains over third-party aggregators or blogs."""


class PromptBuilder:
    """Builds structured prompts for LLM verification following Section 18."""

    @classmethod
    def build_verification_prompt(
        cls,
        raw_name: str,
        candidates: List[str],
        search_evidence: Optional[List[SearchResult]] = None,
        crawl_evidence: Optional[List[CrawlEvidence]] = None,
        contextual_notes: Optional[str] = None,
    ) -> Dict[str, str]:
        """Construct system and user messages for the LLM."""
        user_lines = [
            "Resolve the canonical software application name for the following raw record:",
            f"RAW APPLICATION NAME: {raw_name}",
            "",
            "CANDIDATE HYPOTHESES:",
        ]

        for i, cand in enumerate(candidates, 1):
            user_lines.append(f"  {i}. {cand}")

        if crawl_evidence:
            user_lines.append("")
            user_lines.append("OFFICIAL & HIGH-AUTHORITY WEB EVIDENCE:")
            for ev in crawl_evidence:
                tag = "[OFFICIAL VENDOR]" if ev.is_official else "[THIRD-PARTY]"
                user_lines.append(f"- {tag} {ev.domain} (Authority: {ev.authority_score:.2f})")
                if ev.clean_title:
                    user_lines.append(f"  Page Title: {ev.clean_title}")
                if ev.application_name:
                    user_lines.append(f"  App Name: {ev.application_name}")
                if ev.text_summary:
                    snippet = ev.text_summary[:160].replace("\n", " ")
                    user_lines.append(f"  Summary: {snippet}...")

        elif search_evidence:
            user_lines.append("")
            user_lines.append("SEARCH ENGINE EVIDENCE:")
            for s in search_evidence[:3]:
                user_lines.append(f"- [{s.engine.upper()}] {s.title}")
                if s.snippet:
                    user_lines.append(f"  Snippet: {s.snippet[:140]}...")

        if contextual_notes:
            user_lines.append("")
            user_lines.append(f"ADDITIONAL GUIDANCE: {contextual_notes}")

        user_lines.append("")
        user_lines.append("Return ONLY the clean canonical application name (no explanations, no punctuation):")

        return {
            "system": SYSTEM_PROMPT.strip(),
            "user": "\n".join(user_lines).strip(),
        }
