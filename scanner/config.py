"""Config loading: static settings from config.yaml, secrets from env vars
(sourced from k8s Secrets in-cluster -- see k8s/secrets.md)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import yaml

DEFAULT_CONFIG_PATH = Path(os.environ.get("JOBSCOUT_CONFIG", "config.yaml"))


@dataclass(frozen=True)
class Secrets:
    ntfy_token: str
    applications_repo_token: str
    application_writer_token: str

    @classmethod
    def from_env(cls) -> "Secrets":
        return cls(
            ntfy_token=_require_env("NTFY_TOKEN"),
            applications_repo_token=_require_env("APPLICATIONS_REPO_TOKEN"),
            application_writer_token=_require_env("APPLICATION_WRITER_TOKEN"),
        )

    def credentials_for(self, portal_name: str) -> tuple[str, str] | None:
        """(username, password) for a portal, read from `<PORTAL>_USER` /
        `<PORTAL>_PASS` env vars. Returns None if either is unset -- adding a
        new portal never requires touching this class (Open/Closed)."""
        prefix = portal_name.upper()
        user = os.environ.get(f"{prefix}_USER")
        password = os.environ.get(f"{prefix}_PASS")
        if not user or not password:
            return None
        return user, password


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"required environment variable {name} is not set")
    return value


def load_config(path: Path = DEFAULT_CONFIG_PATH) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)
