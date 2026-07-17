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
from application_writer.models import FitAnalysis, ReviewResult  # noqa: E402
from application_writer.pipeline import ComposedApplication  # noqa: E402

client = TestClient(app_module.app)

VALID_PAYLOAD = {
    "id": "freelancermap-1",
    "portal": "freelancermap",
    "title": "DevOps Engineer",
    "url": "https://example.com/job",
    "posting_text": "Wir suchen DevOps mit Kubernetes.",
    "contract_type": "contracting",
    "remote_percent": 100,
    "company": "Acme GmbH",
    "matched_keywords": ["devops", "kubernetes"],
}


def _patch_pipeline(monkeypatch, needs_review: bool):
    fit = FitAnalysis(fit_level="stark", matched=["devops"], gaps=[], summary="guter fit", raw_text="...")
    review = ReviewResult(verdict="REQUEST CHANGES" if needs_review else "APPROVE", findings="...")
    composed = ComposedApplication(
        fit_analysis=fit,
        anschreiben="Sehr geehrte Damen und Herren, ...",
        tailored_profil_tex="\\section*{Profil}",
        review=review,
        needs_review=needs_review,
    )
    monkeypatch.setattr(app_module.pipeline, "compose", lambda *a, **k: composed)


def _patch_io(monkeypatch, tmp_path):
    monkeypatch.setattr(
        app_module.cv_client, "fetch_profile", lambda *a, **k: ("\\section*{Profil}\nOld.", {"experience": "..."})
    )
    monkeypatch.setattr(app_module.cv_client, "build_pdf", lambda *a, **k: b"%PDF-fake")
    monkeypatch.setattr(app_module.applications_repo, "sync", lambda *a, **k: tmp_path)
    committed = {}

    def fake_write_and_commit(repo_path, clone_url, token, request, **kwargs):
        committed["status"] = kwargs["status"]
        committed["id"] = request.id

    monkeypatch.setattr(app_module.applications_repo, "write_and_commit", fake_write_and_commit)
    monkeypatch.setattr(app_module.obsidian_client, "notify_note", lambda *a, **k: None)
    monkeypatch.setattr(app_module.notifier, "notify", lambda *a, **k: None)
    return committed


def test_compose_requires_auth():
    response = client.post("/compose", json=VALID_PAYLOAD)
    assert response.status_code == 401


def test_compose_commits_as_composed_when_approved(monkeypatch, tmp_path):
    _patch_pipeline(monkeypatch, needs_review=False)
    committed = _patch_io(monkeypatch, tmp_path)

    response = client.post(
        "/compose", json=VALID_PAYLOAD, headers={"Authorization": "Bearer test-app-writer-token"}
    )

    assert response.status_code == 200
    assert response.json()["status"] == "composed"
    assert committed["status"] == "composed"


def test_compose_commits_as_needs_review_when_not_approved(monkeypatch, tmp_path):
    _patch_pipeline(monkeypatch, needs_review=True)
    committed = _patch_io(monkeypatch, tmp_path)

    response = client.post(
        "/compose", json=VALID_PAYLOAD, headers={"Authorization": "Bearer test-app-writer-token"}
    )

    assert response.status_code == 200
    assert response.json()["status"] == "needs-review"
    assert committed["status"] == "needs-review"


def test_compose_returns_502_and_does_not_commit_on_pipeline_error(monkeypatch, tmp_path):
    def raise_pipeline_error(*a, **k):
        raise app_module.pipeline.PipelineError("boom")

    monkeypatch.setattr(app_module.pipeline, "compose", raise_pipeline_error)
    committed = _patch_io(monkeypatch, tmp_path)

    response = client.post(
        "/compose", json=VALID_PAYLOAD, headers={"Authorization": "Bearer test-app-writer-token"}
    )

    assert response.status_code == 502
    assert "status" not in committed
