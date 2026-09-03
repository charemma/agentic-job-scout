"""The provider-independent LLM backend interface. pipeline.py imports
only from here (and router.py) -- never a concrete backend module -- so it
has no knowledge of any specific CLI, API, or provider."""

from __future__ import annotations

from typing import Protocol

from application_writer.llm.types import LLMRequest, LLMResult


class LLMBackendError(RuntimeError):
    """Common base for backend failures -- a non-zero exit, malformed
    output, a timeout that survived retries, etc. Concrete backends raise
    their own subclass (see e.g. claude_cli_backend.ClaudeCliBackendError)
    so failures are still distinguishable by type, but callers that only
    care "did the completion fail" can catch this base class without
    knowing which backend was involved."""


class LLMBackend(Protocol):
    name: str

    def complete(self, request: LLMRequest) -> LLMResult:
        """Run one completion. Backends own their own bounded retry policy
        internally -- callers get either a result or an LLMBackendError,
        never a partial/ambiguous outcome."""
        ...
