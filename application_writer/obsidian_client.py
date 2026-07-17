"""Triggers obsidian-writer to materialize/update the Obsidian note.
Best-effort: a failure here must not lose the already-committed application
(job.md/anschreiben.md/PDF in jobscout-applications is the durable record;
the Obsidian note is a convenience view on top of it)."""

from __future__ import annotations

import logging

import httpx

from application_writer.models import ComposeRequest
from application_writer.pipeline import ComposedApplication

log = logging.getLogger("application-writer")


def notify_note(
    base_url: str,
    token: str,
    request: ComposeRequest,
    composed: ComposedApplication,
    status: str,
    rate: int,
) -> None:
    try:
        response = httpx.post(
            f"{base_url.rstrip('/')}/notes",
            json={
                "id": request.id,
                "title": request.title,
                "company": request.company,
                "contact_name": request.contact_name,
                "portal": request.portal,
                "url": request.url,
                "contract_type": request.contract_type,
                "remote_percent": request.remote_percent,
                "posting_text": request.posting_text,
                "rate": rate,
                "anschreiben": composed.anschreiben,
                "fit_level": composed.fit_analysis.fit_level,
                "fit_summary": composed.fit_analysis.summary,
                "matched_keywords": request.matched_keywords,
                "gaps": composed.fit_analysis.gaps,
                "status": status,
            },
            headers={"Authorization": f"Bearer {token}"},
            timeout=30.0,
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        log.error("obsidian-writer /notes failed for %s (non-fatal): %s", request.id, exc)
