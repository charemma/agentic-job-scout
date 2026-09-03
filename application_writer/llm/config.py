"""Reads the `llm:` section of config.yaml. Deliberately self-contained
(doesn't import scanner.config) -- jobscout's services share no code by
design, see README's "How it works"."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

DEFAULT_CONFIG_PATH = Path(os.environ.get("JOBSCOUT_CONFIG", "config.yaml"))


def load_llm_config(path: Path | None = None) -> dict[str, Any]:
    path = path or DEFAULT_CONFIG_PATH
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return data.get("llm", {})
