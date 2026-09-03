import pytest

from application_writer import pipeline
from application_writer.llm.fake_backend import FakeBackend
from application_writer.llm.router import BackendRouter, LLMConfigError
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


def _router_for(responder) -> BackendRouter:
    """All four stages routed to one FakeBackend driven by `responder` --
    matches how the pipeline previously monkeypatched a single
    claude_cli.complete function, just through the new interface."""
    backend = FakeBackend(name="fake", responder=lambda request: responder(request.system, request.user))
    return BackendRouter(
        backends={"fake": backend},
        stages={"analysis": "fake", "writing": "fake", "review": "fake", "scoring": "fake"},
    )


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


def test_evaluate_parses_score_and_stays_blind():
    seen = {}

    def responder(system, user):
        seen["system"], seen["user"] = system, user
        return EVAL_CLEAN

    router = _router_for(responder)
    score = pipeline.evaluate(_request(), "\\section*{Profil}", {"experience": "exp"}, router)

    assert score.total == 85
    assert score.real_gaps == ["terraform"]
    # blind: no scanner keyword hints, no fit analysis in the prompt
    assert "Matched keywords" not in seen["user"]
    assert "Fit-Analyse" not in seen["user"]


def test_compose_approves_on_first_pass():
    calls = iter([ANALYSIS_OUTPUT, WRITER_OUTPUT, REVIEW_APPROVE, EVAL_CLEAN])
    router = _router_for(lambda system, user: next(calls))

    result = pipeline.compose(_request(), "\\section*{Profil}\nOld.", {"experience": "..."}, router)

    assert result.needs_review is False
    assert result.fit_analysis.fit_level == "stark"
    assert "Tagesgeschaeft" in result.anschreiben
    assert result.match_score.total == 85


def test_compose_spends_retry_on_fixable_match_findings():
    calls = iter(
        [ANALYSIS_OUTPUT, WRITER_OUTPUT, REVIEW_APPROVE, EVAL_FIXABLE, WRITER_OUTPUT, REVIEW_APPROVE, EVAL_CLEAN]
    )
    router = _router_for(lambda system, user: next(calls))

    result = pipeline.compose(_request(), "\\section*{Profil}\nOld.", {"experience": "..."}, router)

    assert result.needs_review is False
    assert result.match_score.total == 85  # re-scored after the improvement round


def test_compose_retries_once_on_request_changes():
    # EVAL_FIXABLE at the end: the bounded retry was already spent on review
    # findings, so fixable match findings must NOT trigger another round --
    # a further call would exhaust the iterator and fail the test.
    calls = iter(
        [ANALYSIS_OUTPUT, WRITER_OUTPUT, REVIEW_REQUEST_CHANGES, WRITER_OUTPUT, REVIEW_APPROVE, EVAL_FIXABLE]
    )
    router = _router_for(lambda system, user: next(calls))

    result = pipeline.compose(_request(), "\\section*{Profil}\nOld.", {"experience": "..."}, router)

    assert result.needs_review is False
    assert result.match_score.total == 70


def test_compose_flags_needs_review_if_still_not_approved_after_retry():
    calls = iter(
        [ANALYSIS_OUTPUT, WRITER_OUTPUT, REVIEW_REQUEST_CHANGES, WRITER_OUTPUT, REVIEW_REQUEST_CHANGES, EVAL_CLEAN]
    )
    router = _router_for(lambda system, user: next(calls))

    result = pipeline.compose(_request(), "\\section*{Profil}\nOld.", {"experience": "..."}, router)

    assert result.needs_review is True


def test_compose_uses_a_different_backend_per_stage():
    """The point of the router: analysis/writing can run on one backend
    while review/scoring runs on another, with zero pipeline.py changes."""

    def claude_responder(request):
        return ANALYSIS_OUTPUT if "Match-Analystin" in request.system else WRITER_OUTPUT

    def codex_responder(request):
        return REVIEW_APPROVE if "Reviewerin" in request.system else EVAL_CLEAN

    claude = FakeBackend(name="claude", responder=claude_responder)
    codex = FakeBackend(name="codex", responder=codex_responder)

    router = BackendRouter(
        backends={"claude": claude, "codex": codex},
        stages={"analysis": "claude", "writing": "claude", "review": "codex", "scoring": "codex"},
    )

    result = pipeline.compose(_request(), "\\section*{Profil}\nOld.", {"experience": "..."}, router)

    assert result.needs_review is False
    assert len(claude.calls) == 2  # analysis + writing
    assert len(codex.calls) == 2  # review + scoring
    assert all(r.model is None for r in claude.calls)  # pipeline never overrides model per-call


def test_compose_raises_llm_config_error_when_a_stage_has_no_backend():
    router = BackendRouter(backends={}, stages={})
    with pytest.raises(LLMConfigError):
        pipeline.compose(_request(), "\\section*{Profil}", {"experience": "exp"}, router)


def test_analyse_uses_fit_analysis_model():
    router = _router_for(lambda system, user: ANALYSIS_OUTPUT)
    fit = pipeline.analyse(_request(), "\\section*{Profil}", {"experience": "exp"}, router)
    assert isinstance(fit, FitAnalysis)
    assert fit.fit_level == "stark"
