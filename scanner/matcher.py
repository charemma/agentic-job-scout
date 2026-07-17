"""Portal-independent keyword/criteria matching.

Deliberately dumb (word-boundary keyword matching, no ML/embedding scoring):
the LLM-based fit analysis happens downstream in application-writer, once a
posting already cleared this cheap filter. This step only decides whether a
posting is worth spending an LLM call on at all.
"""

from __future__ import annotations

import re

from scanner.models import JobPosting, MatchResult


def _contains_keyword(haystack: str, keyword: str) -> bool:
    pattern = r"\b" + re.escape(keyword.lower()) + r"\b"
    return re.search(pattern, haystack) is not None


def match(posting: JobPosting, keywords: list[str], min_matches: int = 1) -> MatchResult | None:
    """Return a MatchResult if the posting mentions at least `min_matches` keywords."""
    haystack = f"{posting.title}\n{posting.posting_text}".lower()
    matched = [kw for kw in keywords if _contains_keyword(haystack, kw)]
    if len(matched) < min_matches:
        return None
    return MatchResult(posting=posting, matched_keywords=matched)
