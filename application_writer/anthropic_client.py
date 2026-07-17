"""Direct Anthropic Messages API client.

Mirrors kuromaku's (unused-in-practice) `Backend::Api` code path
(`src/llm.rs`: POST https://api.anthropic.com/v1/messages, `x-api-key`
header, `anthropic-version: 2023-06-01`) -- kuro's own agents actually shell
out to the `claude`/`codex` CLIs today, which isn't available unattended in
a container, so this re-implements the one backend kuro has that *is*
container-friendly.
"""

from __future__ import annotations

import os

import httpx

API_URL = os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com") + "/v1/messages"
API_VERSION = "2023-06-01"
DEFAULT_MODEL = "claude-opus-4-7"


def complete(system: str, user: str, model: str = DEFAULT_MODEL, max_tokens: int = 4096) -> str:
    api_key = os.environ["ANTHROPIC_API_KEY"]
    response = httpx.post(
        API_URL,
        headers={
            "x-api-key": api_key,
            "anthropic-version": API_VERSION,
            "content-type": "application/json",
        },
        json={
            "model": model,
            "max_tokens": max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        },
        timeout=120.0,
    )
    response.raise_for_status()
    data = response.json()
    return "".join(block["text"] for block in data["content"] if block["type"] == "text")
