import os

for key, value in {
    "APPLICATION_WRITER_TOKEN": "test-app-writer-token",
    "CV_SERVICE_BASE_URL": "http://cv-service.test",
    "CV_SERVICE_TOKEN": "test-cv-token",
    "APPLICATIONS_REPO_CLONE_URL": "https://github.com/charemma/jobscout-applications.git",
    "APPLICATIONS_REPO_TOKEN": "test-repo-token",
    "APPLICATIONS_REPO_PATH": "/tmp/jobscout-applications-test",
    "OBSIDIAN_WRITER_BASE_URL": "http://obsidian-writer.test",
    "OBSIDIAN_WRITER_TOKEN": "test-obsidian-token",
    "NTFY_BASE_URL": "https://ntfy.test",
    "NTFY_TOPIC": "jobscout",
    "NTFY_TOKEN": "test-ntfy-token",
}.items():
    os.environ.setdefault(key, value)

from fastapi.testclient import TestClient  # noqa: E402

from application_writer import app as app_module  # noqa: E402
from application_writer.models import FitAnalysis  # noqa: E402

client = TestClient(app_module.app)

VALID_PAYLOAD = {
    "id": "randstad-c01322436",
    "portal": "randstad",
    "title": "Platform Engineer (m/w/d)",
    "url": "https://example.com/job",
    "posting_text": "Remote Platform Engineering Rolle mit Fokus auf AI Security.",
    "contract_type": "permanent",
    "remote_percent": None,
    "company": "Acme GmbH",
    "matched_keywords": ["platform", "ai security"],
}


def test_assess_requires_auth():
    response = client.post("/assess", json=VALID_PAYLOAD)
    assert response.status_code == 401


def test_assess_returns_fit_level_and_summary(monkeypatch):
    monkeypatch.setattr(
        app_module.cv_client, "fetch_profile", lambda *a, **k: ("\\section*{Profil}\nOld.", {"experience": "..."})
    )
    fit = FitAnalysis(
        fit_level="stark",
        matched=["platform", "ai security"],
        gaps=[],
        summary="Starker Fit, remote, EU-weit ausgeschrieben.",
        raw_text="...",
    )
    monkeypatch.setattr(app_module.pipeline, "analyse", lambda *a, **k: fit)

    response = client.post(
        "/assess", json=VALID_PAYLOAD, headers={"Authorization": "Bearer test-app-writer-token"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body == {"fit_level": "stark", "summary": "Starker Fit, remote, EU-weit ausgeschrieben."}


def test_assess_returns_502_on_pipeline_error(monkeypatch):
    monkeypatch.setattr(
        app_module.cv_client, "fetch_profile", lambda *a, **k: ("\\section*{Profil}\nOld.", {"experience": "..."})
    )

    def raise_pipeline_error(*a, **k):
        raise app_module.pipeline.PipelineError("boom")

    monkeypatch.setattr(app_module.pipeline, "analyse", raise_pipeline_error)

    response = client.post(
        "/assess", json=VALID_PAYLOAD, headers={"Authorization": "Bearer test-app-writer-token"}
    )

    assert response.status_code == 502
