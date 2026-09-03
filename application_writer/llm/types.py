"""Provider-independent request/result shapes for the LLM backend
interface -- see backend.py for the protocol these are passed to/from."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class LLMRequest:
    system: str
    user: str
    # None means "use the backend's own configured default" for each field
    # below -- callers only override what a given pipeline step actually
    # needs to control.
    model: str | None = None
    timeout_seconds: float | None = None
    max_tokens: int | None = None
    max_budget_usd: float | None = None


@dataclass(frozen=True)
class LLMResult:
    text: str
    backend: str
    model: str | None
    duration_seconds: float
    attempts: int
    metadata: dict[str, Any] = field(default_factory=dict)
