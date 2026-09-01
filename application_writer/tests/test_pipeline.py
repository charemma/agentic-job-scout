import pytest

from application_writer import pipeline
from application_writer.models import ComposeRequest, FitAnalysis


def _request(**overrides) -> ComposeRequest:
    defaults = dict(
        id="freelancermap-1",
        portal="freelancermap",
        title="DevOps Engineer (m/w/d)",
        url="https://example.com/job",
        posting_text="Wir suchen einen DevOps Engineer mit Kubernetes-Erfahrung.",
        contract_type="contracting",
        remote_percent=100,
        company="Acme GmbH",
        matched_keywords=["devops", "kubernetes"],
    )
    defaults.update(overrides)
    return ComposeRequest(**defaults)


ANALYSIS_OUTPUT = """Freitext-Analyse hier, matched Kubernetes und DevOps stark.

```json
{"fit_level": "stark", "matched": ["kubernetes", "devops"], "gaps": ["terraform"], "summary": "guter Fit"}
```
"""

WRITER_OUTPUT = """```anschreiben
Sehr geehrte Damen und Herren,

Plattformen aufbauen und betreiben ist mein Tagesgeschaeft.

Mit freundlichen Gruessen
the candidate
```

```profil_tex
\\section*{Profil}
Ich bin Platform Engineer.
```
"""

REVIEW_APPROVE = """### Verdict
APPROVE

### Funde
Keine.
"""

REVIEW_REQUEST_CHANGES = """### Verdict
REQUEST CHANGES

### Funde
- Absatz 2: Meta-Erklaerung enthalten. Fix: streichen.

### Writer-Instruction
Streiche die Meta-Erklaerung im zweiten Absatz.
"""

EVAL_CLEAN = """Blind-Screening: Kubernetes und DevOps decken die Muss-Anforderungen.

```json
{"total": 85, "keyword_score": 80, "semantic_score": 90,
 "missing_keywords": ["terraform"], "fixable": [], "real_gaps": ["terraform"]}
```
"""

EVAL_FIXABLE = """Blind-Screening: GitLab CI steht nur in der Skill-Liste.

```json
{"total": 70, "keyword_score": 65, "semantic_score": 75,
 "missing_keywords": ["gitlab ci/cd"],
 "fixable": ["GitLab CI als GitLab CI/CD ausschreiben"], "real_gaps": []}
```
"""


def test_extract_json_block_parses_fit_analysis():
    data = pipeline._extract_json_block(ANALYSIS_OUTPUT)
    assert data["fit_level"] == "stark"
    assert data["matched"] == ["kubernetes", "devops"]


def test_extract_json_block_raises_without_block():
    with pytest.raises(pipeline.PipelineError):
        pipeline._extract_json_block("no json here")


def test_extract_section_parses_writer_output():
    anschreiben = pipeline._extract_section(WRITER_OUTPUT, "anschreiben")
    profil = pipeline._extract_section(WRITER_OUTPUT, "profil_tex")
    assert "Tagesgeschaeft" in anschreiben
    assert "\\section*{Profil}" in profil


def test_parse_review_approve():
    result = pipeline._parse_review(REVIEW_APPROVE)
    assert result.verdict == "APPROVE"
    assert result.writer_instruction is None


def test_parse_review_request_changes():
    result = pipeline._parse_review(REVIEW_REQUEST_CHANGES)
    assert result.verdict == "REQUEST CHANGES"
    assert "Meta-Erklaerung" in result.writer_instruction


def test_parse_review_raises_without_verdict():
    with pytest.raises(pipeline.PipelineError):
        pipeline._parse_review("no verdict section here")


def test_evaluate_parses_score_and_stays_blind(monkeypatch):
    seen = {}

    def fake_complete(system, user):
        seen["system"], seen["user"] = system, user
        return EVAL_CLEAN

    monkeypatch.setattr(pipeline.claude_cli, "complete", fake_complete)

    score = pipeline.evaluate(_request(), profil_tex="\\section*{Profil}", common={"experience": "exp"})

    assert score.total == 85
    assert score.real_gaps == ["terraform"]
    # blind: no scanner keyword hints, no fit analysis in the prompt
    assert "Matched keywords" not in seen["user"]
    assert "Fit-Analyse" not in seen["user"]


def test_compose_approves_on_first_pass(monkeypatch):
    calls = iter([ANALYSIS_OUTPUT, WRITER_OUTPUT, REVIEW_APPROVE, EVAL_CLEAN])
    monkeypatch.setattr(pipeline.claude_cli, "complete", lambda system, user: next(calls))

    result = pipeline.compose(_request(), profil_tex="\\section*{Profil}\nOld.", common={"experience": "..."})

    assert result.needs_review is False
    assert result.fit_analysis.fit_level == "stark"
    assert "Tagesgeschaeft" in result.anschreiben
    assert result.match_score.total == 85


def test_compose_spends_retry_on_fixable_match_findings(monkeypatch):
    calls = iter(
        [ANALYSIS_OUTPUT, WRITER_OUTPUT, REVIEW_APPROVE, EVAL_FIXABLE, WRITER_OUTPUT, REVIEW_APPROVE, EVAL_CLEAN]
    )
    monkeypatch.setattr(pipeline.claude_cli, "complete", lambda system, user: next(calls))

    result = pipeline.compose(_request(), profil_tex="\\section*{Profil}\nOld.", common={"experience": "..."})

    assert result.needs_review is False
    assert result.match_score.total == 85  # re-scored after the improvement round


def test_compose_retries_once_on_request_changes(monkeypatch):
    # EVAL_FIXABLE at the end: the bounded retry was already spent on review
    # findings, so fixable match findings must NOT trigger another round --
    # a further call would exhaust the iterator and fail the test.
    calls = iter(
        [ANALYSIS_OUTPUT, WRITER_OUTPUT, REVIEW_REQUEST_CHANGES, WRITER_OUTPUT, REVIEW_APPROVE, EVAL_FIXABLE]
    )
    monkeypatch.setattr(pipeline.claude_cli, "complete", lambda system, user: next(calls))

    result = pipeline.compose(_request(), profil_tex="\\section*{Profil}\nOld.", common={"experience": "..."})

    assert result.needs_review is False
    assert result.match_score.total == 70


def test_compose_flags_needs_review_if_still_not_approved_after_retry(monkeypatch):
    calls = iter(
        [ANALYSIS_OUTPUT, WRITER_OUTPUT, REVIEW_REQUEST_CHANGES, WRITER_OUTPUT, REVIEW_REQUEST_CHANGES, EVAL_CLEAN]
    )
    monkeypatch.setattr(pipeline.claude_cli, "complete", lambda system, user: next(calls))

    result = pipeline.compose(_request(), profil_tex="\\section*{Profil}\nOld.", common={"experience": "..."})

    assert result.needs_review is True
