"""Dedup state against the jobscout-applications repo.

Git itself is the dedup store: no separate database. If
`applications/<id>/` already exists in that repo, the posting has already
been seen (composed or pending) and is skipped.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit


def _authenticated_url(clone_url: str, token: str) -> str:
    parts = urlsplit(clone_url)
    if parts.scheme not in ("http", "https"):
        return clone_url  # e.g. file:// for local dev (docker-compose) -- no host to inject a token into
    netloc = f"{token}@{parts.netloc}"
    return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))


def sync_applications_repo(clone_url: str, token: str, local_path: Path) -> Path:
    """Clone the applications repo if absent, else fast-forward pull. Returns local_path."""
    authenticated_url = _authenticated_url(clone_url, token)
    if (local_path / ".git").exists():
        subprocess.run(
            ["git", "-C", str(local_path), "pull", "--ff-only"],
            check=True,
            capture_output=True,
        )
    else:
        local_path.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["git", "clone", "--depth", "1", authenticated_url, str(local_path)],
            check=True,
            capture_output=True,
        )
    return local_path


def already_seen(repo_path: Path, job_id: str) -> bool:
    return (repo_path / "applications" / job_id).exists()
