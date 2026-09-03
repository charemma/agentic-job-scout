"""Claude Code CLI (`claude -p`) backend, headless/non-interactive.

Behavior ported from the original claude_cli.py module -- see that module
for the historical rationale (subscription billing via
CLAUDE_CODE_OAUTH_TOKEN rather than a metered ANTHROPIC_API_KEY, and why
`--tools ""` / `--no-session-persistence` are used).

Known limitation, verified against `claude -p --help` (Claude Code CLI
2.1.236): both the system prompt (`--system-prompt`) and the user prompt
(positional argument) are CLI arguments, not stdin input -- there is no
documented stdin-based alternative for either in this CLI version. Prompt
content therefore ends up in this process's argv (e.g. visible to other
users on the same host via `ps`), same trade-off the original
implementation made. Contrast with CodexCliBackend, whose CLI does accept
the prompt via stdin.

`request.max_tokens` is intentionally not forwarded: `claude -p --help`
has no output-length flag in this CLI version. `--max-budget-usd` is the
one budget control it does expose, and that's what's used here.
"""

from __future__ import annotations

import json
import subprocess
import time
from dataclasses import dataclass

from application_writer.llm.backend import LLMBackendError
from application_writer.llm.types import LLMRequest, LLMResult

DEFAULT_MODEL = "sonnet"
DEFAULT_TIMEOUT_SECONDS = 180.0
DEFAULT_MAX_BUDGET_USD = "0.50"
RETRY_DELAY_SECONDS = 5.0
MAX_ATTEMPTS = 2  # one retry, matches the original claude_cli.py


class ClaudeCliBackendError(LLMBackendError):
    pass


@dataclass
class ClaudeCliBackend:
    name: str = "claude-cli"
    model: str = DEFAULT_MODEL
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS
    max_budget_usd: str = DEFAULT_MAX_BUDGET_USD
    executable: str = "claude"
    retry_delay_seconds: float = RETRY_DELAY_SECONDS

    def complete(self, request: LLMRequest) -> LLMResult:
        model = request.model or self.model
        timeout = request.timeout_seconds or self.timeout_seconds
        max_budget = (
            f"{request.max_budget_usd:.2f}" if request.max_budget_usd is not None else self.max_budget_usd
        )

        last_error: Exception | None = None
        start = time.monotonic()
        for attempt in range(1, MAX_ATTEMPTS + 1):
            if attempt > 1:
                time.sleep(self.retry_delay_seconds)
            try:
                data = self._complete_once(request, model, timeout, max_budget)
                return LLMResult(
                    text=data["result"],
                    backend=self.name,
                    model=model,
                    duration_seconds=time.monotonic() - start,
                    attempts=attempt,
                    metadata={k: v for k, v in data.items() if k != "result"},
                )
            except (subprocess.TimeoutExpired, ClaudeCliBackendError) as exc:
                last_error = exc
        raise ClaudeCliBackendError(
            f"{self.name} failed after {MAX_ATTEMPTS} attempts: {last_error}"
        ) from last_error

    def _complete_once(self, request: LLMRequest, model: str, timeout: float, max_budget: str) -> dict:
        result = subprocess.run(
            [
                self.executable,
                "-p",
                request.user,
                "--system-prompt",
                request.system,
                "--model",
                model,
                "--output-format",
                "json",
                "--no-session-persistence",
                "--tools",
                "",
                "--max-budget-usd",
                max_budget,
            ],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise ClaudeCliBackendError(
                f"{self.name} produced non-JSON output (exit={result.returncode}): "
                f"{result.stdout[:500]!r} stderr={result.stderr[:500]!r}"
            ) from exc

        if data.get("is_error"):
            raise ClaudeCliBackendError(f"{self.name} reported an error: {data}")

        return data
