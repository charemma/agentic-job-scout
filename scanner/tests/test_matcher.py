from scanner.matcher import match
from scanner.models import JobPosting

KEYWORDS = ["python", "devops", "platform", "oscp", "nixos", "nix", "kubernetes", "openshift", "linux"]


def _posting(title: str, text: str) -> JobPosting:
    return JobPosting(
        id="test-1",
        portal="test",
        title=title,
        url="https://example.com",
        posting_text=text,
        contract_type="contracting",
        remote_percent=100,
    )


def test_clear_match():
    posting = _posting(
        "Senior DevOps Engineer (m/w/d)",
        "Wir suchen einen erfahrenen DevOps Engineer mit Kubernetes-Kenntnissen.",
    )
    result = match(posting, KEYWORDS)
    assert result is not None
    assert set(result.matched_keywords) == {"devops", "kubernetes"}


def test_clear_non_match():
    posting = _posting(
        "SAP FI/CO Berater (m/w/d)",
        "Wir suchen einen SAP-Berater mit Erfahrung in Rechnungswesen und Controlling.",
    )
    assert match(posting, KEYWORDS) is None


def test_keyword_boundary_does_not_match_substring():
    # "nix" must not match inside "Unix" or "Phoenix" -- word-boundary check.
    posting = _posting(
        "Unix Systemadministrator",
        "Verwaltung von Unix-Servern, Phoenix-Migration und Solaris-Systemen.",
    )
    assert match(posting, KEYWORDS) is None


def test_min_matches_threshold():
    posting = _posting("Python Entwickler", "Wir suchen einen Python-Entwickler.")
    assert match(posting, KEYWORDS, min_matches=1) is not None
    assert match(posting, KEYWORDS, min_matches=2) is None
