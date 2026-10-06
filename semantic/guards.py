"""Anti-hallucination validation and output sanitization for LLM verification."""

import re
from typing import List, Optional, Set
from app.text_cleaner import clean_text


class AntiHallucinationGuard:
    """Sanitizes and validates LLM responses to prevent hallucinations and over-cleaning."""

    PREFIX_PATTERNS = re.compile(
        r"^(?:"
        r"canonical(?:\s+application)?(?:\s+name)?\s*:\s*|"
        r"application(?:\s+name)?\s*:\s*|"
        r"product(?:\s+name)?\s*:\s*|"
        r"answer\s*:\s*|"
        r"result\s*:\s*|"
        r"the\s+canonical\s+name\s+is\s*:\s*"
        r")",
        re.IGNORECASE,
    )

    CONVERSATIONAL_PATTERNS = re.compile(
        r"\b(?:as\s+an\s+ai|i\s+cannot|sorry|here\s+is|i\s+believe|i\s+recommend|according\s+to)\b",
        re.IGNORECASE,
    )

    def __init__(self, min_token_overlap: float = 0.3, max_length_expansion: int = 15):
        self.min_token_overlap = min_token_overlap
        self.max_length_expansion = max_length_expansion

    def sanitize(self, raw_response: str) -> str:
        """Strip conversational filler, markdown formatting, quotes, and prefixes."""
        if not raw_response:
            return ""

        text = raw_response.strip()

        # Strip markdown fences if present
        text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
        text = re.sub(r"\s*```$", "", text)

        # Extract first non-fence, non-empty line
        lines = [line.strip() for line in text.splitlines() if line.strip() and not line.strip().startswith("```")]
        if not lines:
            return ""
        text = lines[0]

        # Strip bold/italic/code markdown tags
        text = re.sub(r"[*_`]", "", text)

        # Strip leading conversational prefixes ("Canonical Name: AutoCAD")
        text = self.PREFIX_PATTERNS.sub("", text).strip()

        # Strip surrounding quotation marks
        text = text.strip("\"'«»“”‘’")

        # Strip trailing periods if mistakenly added
        text = re.sub(r"\.+$", "", text).strip()

        return clean_text(text)

    def validate(
        self,
        cleaned_response: str,
        raw_name: str,
        candidates: List[str],
        web_evidence_titles: Optional[List[str]] = None,
    ) -> bool:
        """Verify that the LLM response is grounded and not a hallucination."""
        if not cleaned_response:
            return False

        # Reject conversational answers
        if self.CONVERSATIONAL_PATTERNS.search(cleaned_response):
            return False

        # Reject massive length expansion
        if len(cleaned_response) > len(raw_name) + self.max_length_expansion:
            return False

        # Build set of all known valid tokens from raw name, candidate hypotheses, and web evidence
        reference_text = f"{raw_name} {' '.join(candidates)} {' '.join(web_evidence_titles or [])}".lower()
        reference_tokens: Set[str] = set(re.findall(r"\b[a-zA-Z0-9]{2,}\b", reference_text))

        response_tokens = set(re.findall(r"\b[a-zA-Z0-9]{2,}\b", cleaned_response.lower()))
        if not response_tokens:
            return False

        # Calculate token overlap: at least min_token_overlap of response tokens must exist in references
        overlapping_tokens = response_tokens.intersection(reference_tokens)
        overlap_ratio = len(overlapping_tokens) / len(response_tokens)

        if overlap_ratio < self.min_token_overlap:
            # Hallucinated tokens not grounded in any evidence or raw name
            return False

        return True
