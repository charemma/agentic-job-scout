"""Claude Code CLI (`claude -p`) client, headless/non-interactive.

Shells out to the `claude` binary instead of calling the Anthropic Messages
API directly. Deliberate choice, made 2026-08-14: with `ANTHROPIC_API_KEY`
unset and a valid `claude login` session present (mounted into the
container as a k8s Secret -- see k8s/secrets.md), `claude -p` authenticates
via that OAuth/keychain session and usage is billed against the Claude
Code subscription instead of metered per-token API pricing. Verified
locally on `home-node` (headless invocation works without a TTY) and
confirmed by the candidate's own experience running kuromaku the same way, with no
API charges. Mirrors kuro's actual production pattern (CLI shellout), not
its unused `Backend::Api` direct-API code path -- see the project's memory
notes for that history.

Deliberately does **not** pass `--bare`: that flag forces
`ANTHROPIC_API_KEY`/apiKeyHelper-only auth and skips OAuth/keychain entirely,
which is exactly the subscription-billing path this module relies on.

`--tools ""` disables all built-in tools (Bash, Edit, etc.) -- these calls
are plain system+user -> text completions (fit analysis, cover letter
drafting, review), not agentic sessions, and a headless container has no
business running arbitrary tool calls.
"""

from __future__ import annotations

import json
import os
import subprocess

DEFAULT_MODEL = os.environ.get("CLAUDE_CLI_MODEL", "sonnet")
MAX_BUDGET_USD = os.environ.get("CLAUDE_CLI_MAX_BUDGET_USD", "0.50")
TIMEOUT_SECONDS = 180.0


class AnthropicCLIError(RuntimeError):
    """Raised on any failure to get a usable completion from `claude -p` --
    a non-zero exit, a malformed JSON result, or `is_error` in the result.
    Not caught anywhere in pipeline.py, same as the old httpx implementation
    never caught `raise_for_status()` -- both surface as an unhandled 500 in
    application-writer's FastAPI handlers, only `pipeline.PipelineError`
    (raised from unparseable *model output*, a separate failure mode) gets
    the dedicated 502 treatment."""


def complete(system: str, user: str, model: str = DEFAULT_MODEL, max_tokens: int = 4096) -> str:
    result = subprocess.run(
        [
            "claude",
            "-p",
            user,
            "--system-prompt",
            system,
            "--model",
            model,
            "--output-format",
            "json",
            "--no-session-persistence",
            "--tools",
            "",
            "--max-budget-usd",
            MAX_BUDGET_USD,
        ],
        capture_output=True,
        text=True,
        timeout=TIMEOUT_SECONDS,
    )

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise AnthropicCLIError(
            f"claude -p produced non-JSON output (exit={result.returncode}): "
            f"{result.stdout[:500]!r} stderr={result.stderr[:500]!r}"
        ) from exc

    if data.get("is_error"):
        raise AnthropicCLIError(f"claude -p reported an error: {data}")

    return data["result"]
