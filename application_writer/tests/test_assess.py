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
from application_writer.models import FitAnalysis, MatchScore  # noqa: E402

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


def _match_score(total=75):
    return MatchScore(
        total=total, keyword_score=70, semantic_score=80,
        missing_keywords=["terraform"], fixable=[], real_gaps=["terraform"], raw_text="...",
    )


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
    monkeypatch.setattr(app_module.pipeline, "evaluate", lambda *a, **k: _match_score())

    response = client.post(
        "/assess", json=VALID_PAYLOAD, headers={"Authorization": "Bearer test-app-writer-token"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["fit_level"] == "stark"
    assert body["summary"] == "Starker Fit, remote, EU-weit ausgeschrieben."
    assert body["match_score"]["total"] == 75
    assert "raw_text" not in body["match_score"]


def test_assess_skips_match_scoring_for_schwach(monkeypatch):
    monkeypatch.setattr(
        app_module.cv_client, "fetch_profile", lambda *a, **k: ("\\section*{Profil}\nOld.", {"experience": "..."})
    )
    fit = FitAnalysis(fit_level="schwach", matched=[], gaps=["ai security"], summary="kein AI-Bezug", raw_text="...")
    monkeypatch.setattr(app_module.pipeline, "analyse", lambda *a, **k: fit)

    def fail_evaluate(*a, **k):
        raise AssertionError("evaluate must not be called for schwach postings")

    monkeypatch.setattr(app_module.pipeline, "evaluate", fail_evaluate)

    response = client.post(
        "/assess", json=VALID_PAYLOAD, headers={"Authorization": "Bearer test-app-writer-token"}
    )

    assert response.status_code == 200
    assert response.json()["match_score"] is None


def test_assess_survives_match_scoring_failure(monkeypatch):
    monkeypatch.setattr(
        app_module.cv_client, "fetch_profile", lambda *a, **k: ("\\section*{Profil}\nOld.", {"experience": "..."})
    )
    fit = FitAnalysis(fit_level="stark", matched=["platform"], gaps=[], summary="guter fit", raw_text="...")
    monkeypatch.setattr(app_module.pipeline, "analyse", lambda *a, **k: fit)

    def raise_pipeline_error(*a, **k):
        raise app_module.pipeline.PipelineError("no json block")

    monkeypatch.setattr(app_module.pipeline, "evaluate", raise_pipeline_error)

    response = client.post(
        "/assess", json=VALID_PAYLOAD, headers={"Authorization": "Bearer test-app-writer-token"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["fit_level"] == "stark"
    assert body["match_score"] is None


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
