"""application-writer: FastAPI service that turns a matched job posting into
a reviewed draft (Anschreiben + tailored CV), commits it to
jobscout-applications, and triggers the Obsidian note + ntfy notification.

Triggered synchronously by scanner's POST /compose call. See pipeline.py for
the analysis -> write -> self-review logic and applications_repo.py for the
git-based audit trail / commit step.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException

from application_writer import applications_repo, cv_client, notifier, obsidian_client, pipeline
from application_writer.models import ComposeRequest

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("application-writer")

SERVICE_TOKEN = os.environ["APPLICATION_WRITER_TOKEN"]

CV_SERVICE_BASE_URL = os.environ["CV_SERVICE_BASE_URL"]
CV_SERVICE_TOKEN = os.environ["CV_SERVICE_TOKEN"]

APPLICATIONS_REPO_CLONE_URL = os.environ["APPLICATIONS_REPO_CLONE_URL"]
APPLICATIONS_REPO_TOKEN = os.environ["APPLICATIONS_REPO_TOKEN"]
APPLICATIONS_REPO_PATH = Path(os.environ.get("APPLICATIONS_REPO_PATH", "/tmp/jobscout-applications"))

OBSIDIAN_WRITER_BASE_URL = os.environ["OBSIDIAN_WRITER_BASE_URL"]
OBSIDIAN_WRITER_TOKEN = os.environ["OBSIDIAN_WRITER_TOKEN"]

NTFY_BASE_URL = os.environ["NTFY_BASE_URL"]
NTFY_TOPIC = os.environ["NTFY_TOPIC"]
NTFY_TOKEN = os.environ["NTFY_TOKEN"]

TARGET_RATE_EUR_PER_HOUR = int(os.environ.get("TARGET_RATE_EUR_PER_HOUR", "100"))

app = FastAPI(title="application-writer")


def _check_auth(authorization: str | None) -> None:
    if authorization != f"Bearer {SERVICE_TOKEN}":
        raise HTTPException(status_code=401, detail="invalid or missing bearer token")


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}


@app.post("/assess")
def assess(
    request: ComposeRequest,
    authorization: str | None = Header(default=None),
    x_request_id: str | None = Header(default=None),
) -> dict:
    """Cheap LLM fit-check (analysis only, no writing/review/PDF build) --
    lets the scanner filter out weak matches from broader/noisier portals
    before spending a full /compose cycle on them. See pipeline.analyse(),
    reused as-is."""
    _check_auth(authorization)
    request_id = x_request_id or request.id
    log.info("[%s] assessing fit for %s", request_id, request.id)

    profil_tex, common = cv_client.fetch_profile(CV_SERVICE_BASE_URL, CV_SERVICE_TOKEN)

    try:
        fit = pipeline.analyse(request, profil_tex, common)
    except pipeline.PipelineError as exc:
        log.error("[%s] assess failed: %s", request_id, exc)
        raise HTTPException(status_code=502, detail=f"LLM assessment failed: {exc}") from exc

    match_score = None
    if fit.fit_level != "schwach":
        # Blind score against the master CV (measurement point 1) -- skipped
        # for schwach postings, which the AI-Security hard-gate keeps from
        # ever being notified anyway. Best-effort: a scoring failure must
        # not turn a successful assessment into a 502.
        try:
            score = pipeline.evaluate(request, profil_tex, common)
            match_score = score.model_dump(exclude={"raw_text"})
        except pipeline.PipelineError as exc:
            log.warning("[%s] match scoring failed (non-fatal): %s", request_id, exc)

    log.info(
        "[%s] fit_level=%s match=%s", request_id, fit.fit_level,
        f"{match_score['total']}%" if match_score else "n/a",
    )
    return {"fit_level": fit.fit_level, "summary": fit.summary, "match_score": match_score}


@app.post("/compose")
def compose(
    request: ComposeRequest,
    authorization: str | None = Header(default=None),
    x_request_id: str | None = Header(default=None),
) -> dict:
    _check_auth(authorization)
    request_id = x_request_id or request.id
    log.info("[%s] composing application for %s", request_id, request.id)

    profil_tex, common = cv_client.fetch_profile(CV_SERVICE_BASE_URL, CV_SERVICE_TOKEN)

    try:
        composed = pipeline.compose(request, profil_tex, common)
    except pipeline.PipelineError as exc:
        log.error("[%s] pipeline failed, not committing: %s", request_id, exc)
        raise HTTPException(status_code=502, detail=f"LLM pipeline failed: {exc}") from exc

    pdf_bytes = cv_client.build_pdf(CV_SERVICE_BASE_URL, CV_SERVICE_TOKEN, request.id, composed.tailored_profil_tex)

    status = "needs-review" if composed.needs_review else "composed"

    repo_path = applications_repo.sync(APPLICATIONS_REPO_CLONE_URL, APPLICATIONS_REPO_TOKEN, APPLICATIONS_REPO_PATH)
    applications_repo.write_and_commit(
        repo_path,
        APPLICATIONS_REPO_CLONE_URL,
        APPLICATIONS_REPO_TOKEN,
        request,
        status=status,
        fit_level=composed.fit_analysis.fit_level,
        anschreiben=composed.anschreiben,
        tailored_profil_tex=composed.tailored_profil_tex,
        pdf_bytes=pdf_bytes,
        target_rate=TARGET_RATE_EUR_PER_HOUR,
        match_score=composed.match_score,
    )

    obsidian_client.notify_note(
        OBSIDIAN_WRITER_BASE_URL,
        OBSIDIAN_WRITER_TOKEN,
        request,
        composed,
        status=status,
        rate=TARGET_RATE_EUR_PER_HOUR,
    )

    _notify_draft_ready(request, status, composed.match_score)

    log.info(
        "[%s] done: status=%s fit_level=%s match=%s",
        request_id, status, composed.fit_analysis.fit_level,
        f"{composed.match_score.total}%" if composed.match_score else "n/a",
    )
    return {
        "id": request.id,
        "status": status,
        "fit_level": composed.fit_analysis.fit_level,
        "match_score": composed.match_score.model_dump(exclude={"raw_text"}) if composed.match_score else None,
    }


def _notify_draft_ready(request: ComposeRequest, status: str, match_score) -> None:
    title = "Draft braucht Review" if status == "needs-review" else "Draft fertig"
    match_line = f"\nMatch: {match_score.total}%" if match_score else ""
    notifier.notify(
        base_url=NTFY_BASE_URL,
        topic=NTFY_TOPIC,
        token=NTFY_TOKEN,
        title=f"{title}: {request.title}",
        message=(
            f"{request.company or 'Unbekannt'} -- Anschreiben + CV liegen in "
            f"jobscout-applications/{request.id}{match_line}"
        ),
        click_url=request.url,
    )
