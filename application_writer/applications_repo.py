"""Commits the generated application (job.md, anschreiben.md, profil.tex,
PDF) to the jobscout-applications repo -- the audit trail and dedup state
the scanner checks against. Renders job.md with the same frontmatter shape
as the cv repo's existing `.kuro` Bewerbung note template, so the local
`kuro run apply` flow (and the planned Obsidian sync) can still read it.
"""

from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import yaml

from application_writer.models import ComposeRequest, MatchScore


def _authenticated_url(clone_url: str, token: str) -> str:
    parts = urlsplit(clone_url)
    if parts.scheme not in ("http", "https"):
        return clone_url  # e.g. file:// for local dev (docker-compose) -- no host to inject a token into
    netloc = f"{token}@{parts.netloc}"
    return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))


def sync(clone_url: str, token: str, local_path: Path) -> Path:
    authenticated_url = _authenticated_url(clone_url, token)
    if (local_path / ".git").exists():
        # Reset first: a previous run may have crashed between writing files
        # and pushing, leaving an uncommitted/partial working tree that would
        # otherwise make `pull --ff-only` fail on the next run.
        subprocess.run(["git", "-C", str(local_path), "reset", "--hard", "HEAD"], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(local_path), "clean", "-fd"], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(local_path), "pull", "--ff-only"], check=True, capture_output=True)
    else:
        local_path.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["git", "clone", authenticated_url, str(local_path)], check=True, capture_output=True
        )
    return local_path


def _render_job_md(
    request: ComposeRequest,
    status: str,
    fit_level: str,
    target_rate: int,
    match_score: MatchScore | None = None,
) -> str:
    frontmatter = {
        "id": request.id,
        "portal": request.portal,
        "url": request.url,
        "firma": request.company,
        "kontakt": request.contact_name,
        "contract_type": request.contract_type,
        "remote_percent": request.remote_percent,
        "stundensatz": target_rate,
        "matched_keywords": request.matched_keywords,
        "status": status,
        "fit_level": fit_level,
        "match_score": match_score.total if match_score else None,
        "created": datetime.now(timezone.utc).isoformat(),
    }
    yaml_block = yaml.safe_dump(frontmatter, allow_unicode=True, sort_keys=False)
    return f"---\n{yaml_block}---\n\n## Beschreibung\n\n{request.posting_text}\n"


def _render_anschreiben_md(request: ComposeRequest, anschreiben: str, target_rate: int) -> str:
    return (
        f"# Anschreiben: {request.title}\n\n"
        f"**Stelle:** {request.title}\n"
        f"**Firma:** {request.company or 'unbekannt'}\n"
        f"**Portal:** {request.portal} -- {request.url}\n"
        f"**Rate:** {target_rate} EUR/Stunde\n\n"
        f"---\n\n{anschreiben}\n"
    )


def write_and_commit(
    repo_path: Path,
    clone_url: str,
    token: str,
    request: ComposeRequest,
    status: str,
    fit_level: str,
    anschreiben: str,
    tailored_profil_tex: str,
    pdf_bytes: bytes,
    target_rate: int,
    match_score: MatchScore | None = None,
    candidate_name: str = "Candidate",
) -> None:
    app_dir = repo_path / "applications" / request.id
    app_dir.mkdir(parents=True, exist_ok=True)

    (app_dir / "job.md").write_text(
        _render_job_md(request, status, fit_level, target_rate, match_score), encoding="utf-8"
    )
    (app_dir / "anschreiben.md").write_text(
        _render_anschreiben_md(request, anschreiben, target_rate), encoding="utf-8"
    )
    (app_dir / "profil.tex").write_text(tailored_profil_tex, encoding="utf-8")
    (app_dir / f"Lebenslauf_{candidate_name}.pdf").write_bytes(pdf_bytes)

    subprocess.run(["git", "-C", str(repo_path), "add", f"applications/{request.id}"], check=True)
    subprocess.run(
        ["git", "-C", str(repo_path), "-c", "user.name=jobscout-bot",
         "-c", "user.email=jobscout-bot@charemma.de",
         "commit", "-m", f"feat(applications): add {request.id} ({status})"],
        check=True,
        capture_output=True,
    )
    authenticated_url = _authenticated_url(clone_url, token)
    subprocess.run(["git", "-C", str(repo_path), "push", authenticated_url, "HEAD:main"], check=True, capture_output=True)
