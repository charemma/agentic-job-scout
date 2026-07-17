from __future__ import annotations

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
    fit_level: str  # "stark" | "solide" | "schwach"
    matched: list[str]
    gaps: list[str]
    summary: str
    raw_text: str


class ReviewResult(BaseModel):
    verdict: str  # "APPROVE" | "REQUEST CHANGES" | "MAPPING SCHWACH"
    findings: str
    writer_instruction: str | None = None
