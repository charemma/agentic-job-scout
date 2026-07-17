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
    freelancermap_username: str | None = None
    freelancermap_password: str | None = None

    @classmethod
    def from_env(cls) -> "Secrets":
        return cls(
            ntfy_token=_require_env("NTFY_TOKEN"),
            applications_repo_token=_require_env("APPLICATIONS_REPO_TOKEN"),
            application_writer_token=_require_env("APPLICATION_WRITER_TOKEN"),
            freelancermap_username=os.environ.get("FREELANCERMAP_USERNAME"),
            freelancermap_password=os.environ.get("FREELANCERMAP_PASSWORD"),
        )


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"required environment variable {name} is not set")
    return value


def load_config(path: Path = DEFAULT_CONFIG_PATH) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)
