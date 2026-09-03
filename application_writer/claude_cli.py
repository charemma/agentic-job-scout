"""Compatibility shim over application_writer.llm.claude_cli_backend.

pipeline.py no longer imports this module -- it goes through
application_writer.llm.router instead (see ROADMAP.md #2, "Pluggable LLM
backends"). This wrapper is kept only so any external code still calling
`claude_cli.complete(system, user)` directly keeps working; all the actual
subprocess/CLI logic now lives in ClaudeCliBackend.
"""

from __future__ import annotations

from application_writer.llm.claude_cli_backend import ClaudeCliBackend
from application_writer.llm.claude_cli_backend import ClaudeCliBackendError as AnthropicCLIError
from application_writer.llm.types import LLMRequest

_backend = ClaudeCliBackend()


def complete(system: str, user: str, model: str = _backend.model) -> str:
    return _backend.complete(LLMRequest(system=system, user=user, model=model)).text


__all__ = ["complete", "AnthropicCLIError"]
