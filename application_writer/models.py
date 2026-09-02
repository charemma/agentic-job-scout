from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class ComposeRequest(BaseModel):
    id: str
    portal: str
    title: str
    url: str
    posting_text: str
    contract_type: str
    remote_percent: int | None = None
    company: str | None = None
    contact_name: str | None = None
    contact_email: str | None = None
    location: str | None = None
    published_at: str | None = None
    matched_keywords: list[str] = []


class FitAnalysis(BaseModel):
    fit_level: Literal["stark", "solide", "schwach"]
    matched: list[str]
    gaps: list[str]
    summary: str
    raw_text: str


class MatchScore(BaseModel):
    """Blind screening simulation result -- see rules/match-eval.md."""

    total: int  # weighted percent, rounded to 5s
    keyword_score: int
    semantic_score: int
    missing_keywords: list[str]
    fixable: list[str]  # honestly backed rewording opportunities
    real_gaps: list[str]  # requirements no wording can fix
    raw_text: str


class ReviewResult(BaseModel):
    verdict: Literal["APPROVE", "REQUEST CHANGES", "MAPPING SCHWACH"]
    findings: str
    writer_instruction: str | None = None
