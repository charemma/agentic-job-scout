"""Dedup state against the jobscout-applications repo.

Git itself is the dedup store: no separate database. If
`applications/<id>/` already exists in that repo, the posting has already
been seen (composed or pending) and is skipped.

`mark_seen()` is what actually keeps this true when `compose_enabled` is
false: without it, nothing ever gets written to jobscout-applications, so
`already_seen()` always returns False and every scan run re-notifies the
same postings forever. It writes a minimal marker (not a full application)
-- just enough to remember "already shown to the candidate", independent of
whether a CV/Anschreiben was ever drafted for it.
"""

from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import yaml

from scanner.models import JobPosting


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


def mark_seen(
    repo_path: Path,
    clone_url: str,
    token: str,
    posting: JobPosting,
    fit_level: str,
    summary: str,
) -> None:
    """Commit a minimal marker so this posting is never re-notified. Safe
    to call even if `applications/<id>/` already exists (e.g. a later
    /compose run adds job.md/anschreiben.md/the PDF alongside this file) --
    only ever adds seen.md, never touches anything else in that directory."""
    app_dir = repo_path / "applications" / posting.id
    app_dir.mkdir(parents=True, exist_ok=True)

    frontmatter = {
        "id": posting.id,
        "portal": posting.portal,
        "url": posting.url,
        "firma": posting.company,
        "fit_level": fit_level,
        "notified": datetime.now(timezone.utc).isoformat(),
    }
    content = f"---\n{yaml.safe_dump(frontmatter, allow_unicode=True, sort_keys=False)}---\n\n{summary}\n"
    (app_dir / "seen.md").write_text(content, encoding="utf-8")

    subprocess.run(["git", "-C", str(repo_path), "add", f"applications/{posting.id}"], check=True, capture_output=True)
    result = subprocess.run(
        ["git", "-C", str(repo_path), "-c", "user.name=jobscout-bot",
         "-c", "user.email=jobscout-bot@charemma.de",
         "commit", "-m", f"chore(applications): mark {posting.id} as seen"],
        capture_output=True,
    )
    if result.returncode != 0 and b"nothing to commit" not in result.stdout:
        raise subprocess.CalledProcessError(result.returncode, result.args, result.stdout, result.stderr)
    if result.returncode == 0:
        authenticated_url = _authenticated_url(clone_url, token)
        subprocess.run(
            ["git", "-C", str(repo_path), "push", authenticated_url, "HEAD:main"], check=True, capture_output=True
        )
