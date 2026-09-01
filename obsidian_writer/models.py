from __future__ import annotations

from pydantic import BaseModel


class MatchInfo(BaseModel):
    total: int
    keyword_score: int
    semantic_score: int
    missing_keywords: list[str] = []
    fixable: list[str] = []
    real_gaps: list[str] = []


class NotesRequest(BaseModel):
    id: str
    title: str
    company: str | None = None
    contact_name: str | None = None
    portal: str
    url: str
    contract_type: str
    remote_percent: int | None = None
    posting_text: str
    rate: int
    anschreiben: str
    fit_level: str
    fit_summary: str
    matched_keywords: list[str] = []
    gaps: list[str] = []
    status: str
    match: MatchInfo | None = None
