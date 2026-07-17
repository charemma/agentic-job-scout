"""Data models shared across the scanner pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class JobPosting:
    """A single job/project posting, normalized across portals."""

    id: str
    """Stable id, e.g. ``freelancermap-3024636``. Used as the dedup key
    (also doubles as the directory name in the jobscout-applications repo)."""

    portal: str
    title: str
    url: str
    posting_text: str
    contract_type: str
    remote_percent: int | None
    company: str | None = None
    contact_name: str | None = None
    contact_email: str | None = None
    location: str | None = None
    published_at: datetime | None = None


@dataclass(frozen=True)
class MatchResult:
    """A posting that passed the keyword/criteria filter."""

    posting: JobPosting
    matched_keywords: list[str] = field(default_factory=list)
