"""Builds backend instances and stage -> backend routing from the `llm:`
section of config.yaml. This module is the only place that knows about
concrete backend types -- pipeline.py only ever calls
`router.for_stage(<stage name>)`."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from application_writer.llm.backend import LLMBackend
from application_writer.llm.claude_cli_backend import ClaudeCliBackend
from application_writer.llm.codex_cli_backend import CodexCliBackend
from application_writer.llm.fake_backend import FakeBackend

BACKEND_TYPES: dict[str, type] = {
    "claude-cli": ClaudeCliBackend,
    "codex-cli": CodexCliBackend,
    "fake": FakeBackend,
}


class LLMConfigError(RuntimeError):
    """Raised for missing/invalid `llm:` configuration -- a stage without a
    configured backend, or a backend of an unknown type. Deliberately fails
    loudly at startup/call time rather than silently falling back to a
    default backend."""


@dataclass
class BackendRouter:
    backends: dict[str, LLMBackend]
    stages: dict[str, str]

    def for_stage(self, stage: str) -> LLMBackend:
        try:
            backend_name = self.stages[stage]
        except KeyError:
            raise LLMConfigError(f"no backend configured for pipeline stage {stage!r}") from None
        try:
            return self.backends[backend_name]
        except KeyError:
            raise LLMConfigError(
                f"stage {stage!r} is configured to use backend {backend_name!r}, "
                f"which isn't defined under llm.backends"
            ) from None


def build_backend(name: str, spec: dict[str, Any]) -> LLMBackend:
    spec = dict(spec)
    try:
        backend_type = spec.pop("type")
    except KeyError:
        raise LLMConfigError(f"backend {name!r} is missing a required 'type' field") from None
    try:
        backend_cls = BACKEND_TYPES[backend_type]
    except KeyError:
        raise LLMConfigError(
            f"backend {name!r} has unknown type {backend_type!r} (known types: {sorted(BACKEND_TYPES)})"
        ) from None
    return backend_cls(name=name, **spec)


def build_router(llm_config: dict[str, Any]) -> BackendRouter:
    try:
        backend_specs = llm_config["backends"]
        stages = llm_config["stages"]
    except KeyError as exc:
        raise LLMConfigError(f"llm config is missing required section: {exc}") from None
    backends = {backend_name: build_backend(backend_name, spec) for backend_name, spec in backend_specs.items()}
    return BackendRouter(backends=backends, stages=stages)
