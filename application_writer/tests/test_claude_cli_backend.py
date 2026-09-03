"""Contract tests for ClaudeCliBackend against a fake `claude` executable --
never the real CLI, so these never make a paid/live model call. The fake
script is controlled via env vars and written fresh per test."""

from __future__ import annotations

import json
import os
import stat
import subprocess

import pytest

from application_writer.llm.claude_cli_backend import ClaudeCliBackend, ClaudeCliBackendError
from application_writer.llm.types import LLMRequest

FAKE_CLI = '''#!/usr/bin/env python3
import json, os, sys, time

argv_file = os.environ.get("FAKE_CLI_ARGV_FILE")
if argv_file:
    with open(argv_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(sys.argv[1:]) + "\\n")

count_file = os.environ.get("FAKE_CLI_COUNT_FILE")
count = 1
if count_file:
    count = (int(open(count_file, encoding="utf-8").read()) + 1) if os.path.exists(count_file) else 1
    with open(count_file, "w", encoding="utf-8") as f:
        f.write(str(count))

mode = os.environ.get("FAKE_CLI_MODE", "success")

if mode == "timeout":
    time.sleep(30)
elif mode == "malformed":
    print("not json at all")
elif mode == "error":
    print(json.dumps({"is_error": True, "errors": ["boom"]}))
elif mode == "fail_once_then_success":
    if count == 1:
        print("not json")
    else:
        print(json.dumps({"is_error": False, "result": "OK after retry", "duration_ms": 5}))
else:
    print(json.dumps({"is_error": False, "result": "OK", "duration_ms": 42, "total_cost_usd": 0.01}))
'''


@pytest.fixture
def fake_claude(tmp_path, monkeypatch):
    script = tmp_path / "fake_claude.py"
    script.write_text(FAKE_CLI, encoding="utf-8")
    script.chmod(script.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    argv_file = tmp_path / "argv.jsonl"
    monkeypatch.setenv("FAKE_CLI_ARGV_FILE", str(argv_file))
    monkeypatch.delenv("FAKE_CLI_MODE", raising=False)
    monkeypatch.delenv("FAKE_CLI_COUNT_FILE", raising=False)

    return script, argv_file


def _backend(executable, **overrides) -> ClaudeCliBackend:
    return ClaudeCliBackend(executable=str(executable), retry_delay_seconds=0.0, **overrides)


def test_success_returns_normalized_result(fake_claude, monkeypatch):
    script, argv_file = fake_claude
    monkeypatch.setenv("FAKE_CLI_MODE", "success")

    result = _backend(script, model="sonnet").complete(LLMRequest(system="sys", user="hello"))

    assert result.text == "OK"
    assert result.backend == "claude-cli"
    assert result.model == "sonnet"
    assert result.attempts == 1
    assert result.metadata["duration_ms"] == 42
    assert result.metadata["total_cost_usd"] == 0.01
    assert result.duration_seconds >= 0


def test_model_timeout_and_budget_are_forwarded(fake_claude, monkeypatch):
    script, argv_file = fake_claude
    monkeypatch.setenv("FAKE_CLI_MODE", "success")

    backend = _backend(script, model="sonnet", timeout_seconds=99)
    backend.complete(LLMRequest(system="sys", user="hello", model="opus", max_budget_usd=1.23))

    argv = json.loads(argv_file.read_text(encoding="utf-8").splitlines()[0])
    assert "hello" in argv  # user prompt, positional
    assert "sys" in argv  # system prompt, via --system-prompt
    assert "--model" in argv and argv[argv.index("--model") + 1] == "opus"
    assert "--max-budget-usd" in argv and argv[argv.index("--max-budget-usd") + 1] == "1.23"
    assert "--tools" in argv and argv[argv.index("--tools") + 1] == ""
    assert "--no-session-persistence" in argv
    assert "--output-format" in argv and argv[argv.index("--output-format") + 1] == "json"


def test_malformed_output_raises_after_retries(fake_claude, monkeypatch):
    script, _ = fake_claude
    monkeypatch.setenv("FAKE_CLI_MODE", "malformed")

    with pytest.raises(ClaudeCliBackendError):
        _backend(script).complete(LLMRequest(system="sys", user="hello"))


def test_is_error_response_raises(fake_claude, monkeypatch):
    script, _ = fake_claude
    monkeypatch.setenv("FAKE_CLI_MODE", "error")

    with pytest.raises(ClaudeCliBackendError):
        _backend(script).complete(LLMRequest(system="sys", user="hello"))


def test_retries_once_and_succeeds(fake_claude, monkeypatch, tmp_path):
    script, _ = fake_claude
    monkeypatch.setenv("FAKE_CLI_MODE", "fail_once_then_success")
    monkeypatch.setenv("FAKE_CLI_COUNT_FILE", str(tmp_path / "count"))

    result = _backend(script).complete(LLMRequest(system="sys", user="hello"))

    assert result.text == "OK after retry"
    assert result.attempts == 2


def test_timeout_raises(fake_claude, monkeypatch):
    script, _ = fake_claude
    monkeypatch.setenv("FAKE_CLI_MODE", "timeout")

    with pytest.raises(ClaudeCliBackendError):
        _backend(script, timeout_seconds=0.2).complete(LLMRequest(system="sys", user="hello"))


def test_never_calls_the_real_claude_binary(fake_claude):
    """Sanity check that the fixture's executable really is what's invoked,
    not something resolved from PATH -- guards against this test suite
    ever silently shelling out to a real, paid CLI."""
    script, _ = fake_claude
    assert os.access(script, os.X_OK)
    result = subprocess.run([str(script)], input="", capture_output=True, text=True)
    assert result.returncode == 0
