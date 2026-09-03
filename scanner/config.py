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

    def session_state_path_for(self, portal_name: str) -> Path | None:
        """Path to a Playwright `storage_state` JSON file for a portal, if
        one was bootstrapped -- see scripts/linkedin_login_bootstrap.py and
        fetchers/linkedin.py's docstring for why this exists (persisted
        login session avoids re-triggering a verification prompt on
        every fresh username/password login). Convention: a file
        named `<portal>.json` under `JOBSCOUT_SESSION_DIR` (mounted from a
        per-portal k8s Secret, see k8s/secrets.md). Returns None if no such
        file exists -- a fetcher without a bootstrapped session just falls
        back to a fresh login, same as before this existed.

        Deliberately `is_file()`, not `exists()`: the k8s manifest mounts
        each session Secret via `subPath` with `optional: true` so the
        CronJob still runs before a session is ever bootstrapped -- but
        when the referenced Secret doesn't exist yet, kubelet still
        creates the subPath mount point as an empty directory instead of
        leaving it absent. `exists()` returns True for that empty
        directory, which then gets handed to Playwright's
        `storage_state=` as if it were a real session file (crashes with
        `IsADirectoryError`) instead of falling back to a fresh login as
        intended. Confirmed live 2026-09-02: `jobscout-xing-session` was
        never bootstrapped, and `/etc/jobscout-sessions/xing.json` was an
        empty directory in the running pod, not a missing path."""
        session_dir = Path(os.environ.get("JOBSCOUT_SESSION_DIR", "/etc/jobscout-sessions"))
        path = session_dir / f"{portal_name}.json"
        return path if path.is_file() else None


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"required environment variable {name} is not set")
    return value


def load_config(path: Path = DEFAULT_CONFIG_PATH) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)
