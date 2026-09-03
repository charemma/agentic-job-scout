"""Deterministic backend for tests and local demos -- no subprocess, no
network, no cost. Returns a fixed string, or calls a `responder` callback
per request for tests that need different output per call (e.g. simulating
a bounded retry loop)."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field

from application_writer.llm.types import LLMRequest, LLMResult


@dataclass
class FakeBackend:
    name: str = "fake"
    model: str = "fake-model"
    fixed_response: str = "FAKE RESPONSE"
    responder: Callable[[LLMRequest], str] | None = None
    calls: list[LLMRequest] = field(default_factory=list)

    def complete(self, request: LLMRequest) -> LLMResult:
        self.calls.append(request)
        start = time.monotonic()
        text = self.responder(request) if self.responder is not None else self.fixed_response
        return LLMResult(
            text=text,
            backend=self.name,
            model=request.model or self.model,
            duration_seconds=time.monotonic() - start,
            attempts=1,
            metadata={},
        )
