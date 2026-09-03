"""Codex CLI (`codex exec`) backend, non-interactive.

Verified against `codex exec --help` (codex-cli 0.128.0) before writing
this. Two things that shaped the implementation:

1. **No completion-only mode.** Unlike Claude's `claude -p --tools ""`,
   Codex has no flag to fully disable tool/shell use -- `codex exec`
   always runs as a bounded coding agent inside a sandbox policy
   (`-s/--sandbox {read-only,workspace-write,danger-full-access}`), not a
   pure text-completion call. This backend runs it with `--sandbox
   read-only`, the most restrictive option that still lets the agent
   respond, but that is a bounded agent, not a stateless completion --
   keep that difference in mind for stages where it matters (see
   ROADMAP.md).
2. **Prompt via stdin.** `codex exec --help`: "If not provided as an
   argument (or if `-` is used), instructions are read from stdin." There
   is no separate system-prompt argument in this CLI, so the system and
   user prompt are concatenated into one instruction block and piped in
   via stdin -- unlike ClaudeCliBackend, prompt content here does not end
   up in argv.

**Untested success path.** This repo's dev environment had a broken Codex
CLI login (expired/reused refresh token) when this backend was written, so
only the *failure*-path JSON event shape (`{"type": "error", ...}`,
`{"type": "turn.failed", ...}`) could be verified against a real `codex
exec` invocation. The success path was never observed live. To avoid
depending on an unverified event schema, this backend does NOT parse the
result text out of the `--json` event stream -- it reads it from the file
given to `-o/--output-last-message`, which is documented in `--help` and
is far less likely to have changed shape. The raw event stream is still
captured and attached as result metadata for debugging. Contract tests use
a fake `codex` executable, not the real CLI (see
tests/test_codex_cli_backend.py) -- this backend has not been exercised
against a live, successful `codex exec` run.
"""

from __future__ import annotations

import json
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

from application_writer.llm.backend import LLMBackendError
from application_writer.llm.types import LLMRequest, LLMResult

DEFAULT_MODEL = "auto"  # sentinel: omit --model, let codex use its own configured default
DEFAULT_TIMEOUT_SECONDS = 180.0
DEFAULT_SANDBOX = "read-only"
RETRY_DELAY_SECONDS = 5.0
MAX_ATTEMPTS = 2  # one retry, same bound as ClaudeCliBackend


class CodexCliBackendError(LLMBackendError):
    pass


@dataclass
class CodexCliBackend:
    name: str = "codex-cli"
    model: str = DEFAULT_MODEL
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS
    sandbox: str = DEFAULT_SANDBOX
    executable: str = "codex"
    retry_delay_seconds: float = RETRY_DELAY_SECONDS

    def complete(self, request: LLMRequest) -> LLMResult:
        model = request.model or self.model
        timeout = request.timeout_seconds or self.timeout_seconds
        prompt = f"{request.system}\n\n{request.user}"

        last_error: Exception | None = None
        start = time.monotonic()
        for attempt in range(1, MAX_ATTEMPTS + 1):
            if attempt > 1:
                time.sleep(self.retry_delay_seconds)
            try:
                text, events = self._complete_once(prompt, model, timeout)
                return LLMResult(
                    text=text,
                    backend=self.name,
                    model=model,
                    duration_seconds=time.monotonic() - start,
                    attempts=attempt,
                    metadata={"events": events},
                )
            except (subprocess.TimeoutExpired, CodexCliBackendError) as exc:
                last_error = exc
        raise CodexCliBackendError(
            f"{self.name} failed after {MAX_ATTEMPTS} attempts: {last_error}"
        ) from last_error

    def _complete_once(self, prompt: str, model: str, timeout: float) -> tuple[str, list[dict]]:
        with tempfile.TemporaryDirectory() as tmp:
            output_path = Path(tmp) / "last-message.txt"
            argv = [
                self.executable,
                "exec",
                "--sandbox",
                self.sandbox,
                "--skip-git-repo-check",
                "--json",
                "--output-last-message",
                str(output_path),
            ]
            if model and model != "auto":
                argv += ["--model", model]
            argv.append("-")

            result = subprocess.run(
                argv,
                input=prompt,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            events = _parse_jsonl(result.stdout)

            if result.returncode != 0 or not output_path.exists():
                raise CodexCliBackendError(
                    f"{self.name} failed (exit={result.returncode}): "
                    f"stderr={result.stderr[:500]!r} last_events={events[-3:]}"
                )

            text = output_path.read_text(encoding="utf-8").strip()
            if not text:
                raise CodexCliBackendError(f"{self.name} produced an empty response: last_events={events[-3:]}")
            return text, events


def _parse_jsonl(stdout: str) -> list[dict]:
    events = []
    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return events
