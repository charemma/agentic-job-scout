"""Contract tests for CodexCliBackend against a fake `codex` executable --
never the real CLI, so these never make a paid/live model call, and never
depend on the (unverified in this dev environment, see
codex_cli_backend.py's docstring) live success-path event schema."""

from __future__ import annotations

import json
import stat

import pytest

from application_writer.llm.codex_cli_backend import CodexCliBackend, CodexCliBackendError
from application_writer.llm.types import LLMRequest

FAKE_CLI = '''#!/usr/bin/env python3
import json, os, sys, time

argv_file = os.environ.get("FAKE_CLI_ARGV_FILE")
if argv_file:
    with open(argv_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(sys.argv[1:]) + "\\n")

stdin_file = os.environ.get("FAKE_CLI_STDIN_FILE")
stdin_text = sys.stdin.read()
if stdin_file:
    with open(stdin_file, "w", encoding="utf-8") as f:
        f.write(stdin_text)

count_file = os.environ.get("FAKE_CLI_COUNT_FILE")
count = 1
if count_file:
    count = (int(open(count_file, encoding="utf-8").read()) + 1) if os.path.exists(count_file) else 1
    with open(count_file, "w", encoding="utf-8") as f:
        f.write(str(count))

mode = os.environ.get("FAKE_CLI_MODE", "success")

# find --output-last-message <path>
output_path = None
argv = sys.argv[1:]
if "--output-last-message" in argv:
    output_path = argv[argv.index("--output-last-message") + 1]

print(json.dumps({"type": "thread.started", "thread_id": "fake-thread"}))
print(json.dumps({"type": "turn.started"}))

if mode == "timeout":
    time.sleep(30)
elif mode == "error":
    print(json.dumps({"type": "error", "message": "boom"}))
    print(json.dumps({"type": "turn.failed", "error": {"message": "boom"}}))
    sys.exit(1)
elif mode == "empty_output":
    if output_path:
        open(output_path, "w", encoding="utf-8").close()
    print(json.dumps({"type": "turn.completed"}))
elif mode == "fail_once_then_success":
    if count == 1:
        print(json.dumps({"type": "error", "message": "boom"}))
        sys.exit(1)
    else:
        if output_path:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write("OK after retry")
        print(json.dumps({"type": "turn.completed"}))
else:
    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("PONG")
    print(json.dumps({"type": "turn.completed"}))
'''


@pytest.fixture
def fake_codex(tmp_path, monkeypatch):
    script = tmp_path / "fake_codex.py"
    script.write_text(FAKE_CLI, encoding="utf-8")
    script.chmod(script.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    argv_file = tmp_path / "argv.jsonl"
    stdin_file = tmp_path / "stdin.txt"
    monkeypatch.setenv("FAKE_CLI_ARGV_FILE", str(argv_file))
    monkeypatch.setenv("FAKE_CLI_STDIN_FILE", str(stdin_file))
    monkeypatch.delenv("FAKE_CLI_MODE", raising=False)
    monkeypatch.delenv("FAKE_CLI_COUNT_FILE", raising=False)

    return script, argv_file, stdin_file


def _backend(executable, **overrides) -> CodexCliBackend:
    return CodexCliBackend(executable=str(executable), retry_delay_seconds=0.0, **overrides)


def test_success_reads_text_from_output_last_message_file(fake_codex, monkeypatch):
    script, argv_file, stdin_file = fake_codex
    monkeypatch.setenv("FAKE_CLI_MODE", "success")

    result = _backend(script).complete(LLMRequest(system="be terse", user="ping"))

    assert result.text == "PONG"
    assert result.backend == "codex-cli"
    assert result.attempts == 1
    assert len(result.metadata["events"]) >= 2
    assert result.metadata["events"][0]["type"] == "thread.started"


def test_prompt_goes_through_stdin_not_argv(fake_codex, monkeypatch):
    script, argv_file, stdin_file = fake_codex
    monkeypatch.setenv("FAKE_CLI_MODE", "success")

    _backend(script).complete(LLMRequest(system="secret system prompt", user="secret user prompt"))

    argv = json.loads(argv_file.read_text(encoding="utf-8").splitlines()[0])
    assert not any("secret" in a for a in argv)  # never in argv
    assert "secret system prompt" in stdin_file.read_text(encoding="utf-8")
    assert "secret user prompt" in stdin_file.read_text(encoding="utf-8")


def test_model_is_omitted_when_auto(fake_codex, monkeypatch):
    script, argv_file, _ = fake_codex
    monkeypatch.setenv("FAKE_CLI_MODE", "success")

    _backend(script, model="auto").complete(LLMRequest(system="sys", user="hi"))

    argv = json.loads(argv_file.read_text(encoding="utf-8").splitlines()[0])
    assert "--model" not in argv


def test_model_is_forwarded_when_set(fake_codex, monkeypatch):
    script, argv_file, _ = fake_codex
    monkeypatch.setenv("FAKE_CLI_MODE", "success")

    _backend(script, model="gpt-5-codex").complete(LLMRequest(system="sys", user="hi"))

    argv = json.loads(argv_file.read_text(encoding="utf-8").splitlines()[0])
    assert "--model" in argv and argv[argv.index("--model") + 1] == "gpt-5-codex"


def test_sandbox_flag_is_read_only_by_default(fake_codex, monkeypatch):
    script, argv_file, _ = fake_codex
    monkeypatch.setenv("FAKE_CLI_MODE", "success")

    _backend(script).complete(LLMRequest(system="sys", user="hi"))

    argv = json.loads(argv_file.read_text(encoding="utf-8").splitlines()[0])
    assert "--sandbox" in argv and argv[argv.index("--sandbox") + 1] == "read-only"


def test_nonzero_exit_raises(fake_codex, monkeypatch):
    script, _, _ = fake_codex
    monkeypatch.setenv("FAKE_CLI_MODE", "error")

    with pytest.raises(CodexCliBackendError):
        _backend(script).complete(LLMRequest(system="sys", user="hi"))


def test_empty_output_file_raises(fake_codex, monkeypatch):
    script, _, _ = fake_codex
    monkeypatch.setenv("FAKE_CLI_MODE", "empty_output")

    with pytest.raises(CodexCliBackendError):
        _backend(script).complete(LLMRequest(system="sys", user="hi"))


def test_retries_once_and_succeeds(fake_codex, monkeypatch, tmp_path):
    script, _, _ = fake_codex
    monkeypatch.setenv("FAKE_CLI_MODE", "fail_once_then_success")
    monkeypatch.setenv("FAKE_CLI_COUNT_FILE", str(tmp_path / "count"))

    result = _backend(script).complete(LLMRequest(system="sys", user="hi"))

    assert result.text == "OK after retry"
    assert result.attempts == 2


def test_timeout_raises(fake_codex, monkeypatch):
    script, _, _ = fake_codex
    monkeypatch.setenv("FAKE_CLI_MODE", "timeout")

    with pytest.raises(CodexCliBackendError):
        _backend(script, timeout_seconds=0.2).complete(LLMRequest(system="sys", user="hi"))
