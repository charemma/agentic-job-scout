from scanner.main import _match_notification
from scanner.models import JobPosting


def _posting() -> JobPosting:
    return JobPosting(
        id="freelancermap-1",
        portal="freelancermap",
        title="DevSecOps Engineer",
        url="https://example.com/job",
        posting_text="...",
        contract_type="contracting",
        remote_percent=100,
        company="Acme GmbH",
    )


def test_notification_carries_match_score_in_title_and_message():
    assessment = {
        "fit_level": "stark",
        "summary": "Guter Fit.",
        "match_score": {"total": 80, "keyword_score": 75, "semantic_score": 85},
    }

    title, message = _match_notification(_posting(), ["devops"], assessment, compose_enabled=False)

    assert title == "[stark 80%] DevSecOps Engineer"
    assert "Match: 80% (Keywords 75% / Semantik 85%)" in message


def test_notification_without_score_keeps_old_shape():
    assessment = {"fit_level": "solide", "summary": "Ok.", "match_score": None}

    title, message = _match_notification(_posting(), ["devops"], assessment, compose_enabled=False)

    assert title == "[solide] DevSecOps Engineer"
    assert "Match:" not in message
