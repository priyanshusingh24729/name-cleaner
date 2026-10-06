"""Safe text cleaner and unicode preprocessor."""

import unicodedata
import re

# Various unicode dash variants to replace with standard ASCII hyphen
UNICODE_DASHES = re.compile(r"[\u2010\u2011\u2012\u2013\u2014\u2015\u2212\uFE58\uFE63\uFF0D]")

# Various unicode quotes to ASCII equivalents
UNICODE_DOUBLE_QUOTES = re.compile(r"[\u201C\u201D\u201E\u201F\u00AB\u00BB]")
UNICODE_SINGLE_QUOTES = re.compile(r"[\u2018\u2019\u201A\u201B\u2032]")

# Multiple spaces and control/whitespace characters
MULTI_WHITESPACE = re.compile(r"[\s\u00A0\u2000-\u200B\u202F\u205F\u3000]+")

# Dangling separators at the end or start of strings (e.g. "Software - " or " - Software")
DANGLING_SEPARATORS = re.compile(r"^[\s\-–—:;,._/|\\]+|[\s\-–—:;,._/|\\]+$")


def clean_text(text: str) -> str:
    """Preprocess and safely clean raw application name text.

    Preserves meaningful internal punctuation (like '/' in MapToaster Topo/NZ).
    """
    if not text:
        return ""

    # Ensure string type
    if not isinstance(text, str):
        text = str(text)

    # 1. Unicode normalization (NFKC decomposes compatibility chars and recomposes)
    cleaned = unicodedata.normalize("NFKC", text)

    # 2. Normalize quotes
    cleaned = UNICODE_DOUBLE_QUOTES.sub('"', cleaned)
    cleaned = UNICODE_SINGLE_QUOTES.sub("'", cleaned)

    # 3. Normalize dashes
    cleaned = UNICODE_DASHES.sub("-", cleaned)

    # 4. Collapse consecutive whitespace / non-breaking spaces into single space
    cleaned = MULTI_WHITESPACE.sub(" ", cleaned)

    # 5. Strip leading/trailing whitespace
    cleaned = cleaned.strip()

    # 6. Clean dangling edge separators if any (e.g., trailing hyphens)
    cleaned = DANGLING_SEPARATORS.sub("", cleaned).strip()

    return cleaned
