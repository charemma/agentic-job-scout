"""Analysis -> write -> self-review pipeline (Athena/Kalliope/Bella
equivalents from cv/.kuro), run unattended via headless `claude -p`
(subscription billing, see claude_cli.py) -- the same CLI-shellout pattern
kuro uses in production, just driven from Python instead of flow YAML.

Bounded: one review round, at most one writer retry on REQUEST CHANGES. No
human-in-the-loop here -- that happens downstream. A still-REQUEST-CHANGES
result after the retry, or MAPPING SCHWACH at any point, is committed with
status="needs-review" rather than "composed" (see app.py), so the candidate reviews
it before sending -- consistent with the project's non-goal of never
auto-submitting applications.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from application_writer import claude_cli
from application_writer.models import ComposeRequest, FitAnalysis, MatchScore, ReviewResult

RULES_DIR = Path(__file__).parent / "rules"
TARGET_RATE_EUR_PER_HOUR = 100


def load_rule(name: str) -> str:
    return (RULES_DIR / f"{name}.md").read_text(encoding="utf-8")


class PipelineError(RuntimeError):
    """Raised on anything unparseable from the LLM -- callers should treat
    this as a failed /compose request (no commit), not silently degrade."""


@dataclass
class ComposedApplication:
    fit_analysis: FitAnalysis
    anschreiben: str
    tailored_profil_tex: str
    review: ReviewResult
    needs_review: bool
    match_score: MatchScore | None


ANALYSIS_INSTRUCTIONS = """
## Aufgabe

Du bist die Match-Analystin. Analysiere die Stellenausschreibung gegen
the candidate's Profil (Hintergrund oben, plus das mitgelieferte profil.tex und
common/experience.tex). Liefere:

1. Freitext-Analyse: welche Anforderungen matchen 1:1, was fehlt, wie stark
   der Fit insgesamt ist.
2. Am Ende GENAU einen Block in dieser Form (sonst nichts danach):

```json
{"fit_level": "stark", "matched": ["..."], "gaps": ["..."], "summary": "..."}
```

fit_level ist genau eines von: stark, solide, schwach.
"""

WRITER_INSTRUCTIONS = """
## Aufgabe

Du bist die Anschreiben-Autorin, zustaendig auch fuer das Tailoring von
profil.tex. Nutze die Fit-Analyse oben und die Stil-/
Anti-Fabrikations-Regeln. Liefere GENAU zwei Bloecke, sonst nichts:

```anschreiben
<Anschreiben-Text, 120-150 Woerter, den Regeln folgend>
```

```profil_tex
<vollstaendiger neuer Inhalt fuer profil.tex mit angewendeten Schaerfungen,
keine neuen Faehigkeiten erfinden -- siehe tailor-cv-Regeln oben>
```
"""

REVIEW_INSTRUCTIONS = """
## Aufgabe

Du bist die Reviewerin. Pruefe Anschreiben und profil.tex gegen die
Review-Essentials-Regeln oben. Antworte GENAU im dort vorgegebenen Format
(### Verdict / ### Funde / ### Writer-Instruction).
"""


MATCH_EVAL_INSTRUCTIONS = """
## Aufgabe

Du bist die Match-Evaluatorin (Blind-Screening, siehe Regel oben). Bewerte
die Bewerbungsunterlagen gegen die Stellenausschreibung nach der
Score-Methodik. Liefere zuerst deine Analyse als Freitext, dann am Ende
GENAU einen Block in dieser Form (sonst nichts danach):

```json
{"total": 75, "keyword_score": 70, "semantic_score": 80,
 "missing_keywords": ["..."], "fixable": ["..."], "real_gaps": ["..."]}
```

Alle Scores sind Ganzzahlen 0-100. "fixable" sind ehrlich belegbare
Umformulierungen (leer wenn keine), "real_gaps" sind Anforderungen ohne
Beleg im CV.
"""


def _extract_json_block(text: str) -> dict:
    match = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
    if not match:
        raise PipelineError("no ```json block found in analysis output")
    return json.loads(match.group(1))


def _extract_section(text: str, tag: str) -> str:
    match = re.search(rf"```{tag}\s*\n(.*?)\n```", text, re.DOTALL)
    if not match:
        raise PipelineError(f"no ```{tag} block found in writer output")
    return match.group(1).strip()


def _posting_context(request: ComposeRequest) -> str:
    return (
        "## Stellenausschreibung\n"
        f"Titel: {request.title}\n"
        f"Firma: {request.company or 'unbekannt'}\n"
        f"Portal: {request.portal}, URL: {request.url}\n"
        f"Contract: {request.contract_type}, Remote: {request.remote_percent}%\n"
        f"Matched keywords: {', '.join(request.matched_keywords)}\n\n"
        f"{request.posting_text}"
    )


def analyse(request: ComposeRequest, profil_tex: str, common: dict[str, str]) -> FitAnalysis:
    system = load_rule("candidate-profile") + "\n\n" + ANALYSIS_INSTRUCTIONS
    user = (
        _posting_context(request)
        + f"\n\n## Aktuelles profil.tex\n{profil_tex}"
        + f"\n\n## common/experience.tex\n{common.get('experience', '')}"
    )
    raw = claude_cli.complete(system, user)
    data = _extract_json_block(raw)
    return FitAnalysis(raw_text=raw, **data)


def write(
    request: ComposeRequest,
    profil_tex: str,
    common: dict[str, str],
    fit: FitAnalysis,
    retry_instruction: str | None = None,
) -> tuple[str, str]:
    system = (
        load_rule("senior-cover-letter")
        + "\n\n"
        + load_rule("customer-anonymization")
        + "\n\n"
        + load_rule("tailor-cv")
        + "\n\n"
        + WRITER_INSTRUCTIONS
    )
    user = (
        _posting_context(request)
        + f"\n\n## Fit-Analyse\n{fit.raw_text}"
        + f"\n\n## Aktuelles profil.tex\n{profil_tex}"
        + f"\n\n## common/experience.tex\n{common.get('experience', '')}"
        + f"\n\n## Zielrate\n{TARGET_RATE_EUR_PER_HOUR} EUR/Stunde"
    )
    if retry_instruction:
        user += f"\n\n## Ueberarbeitung noetig (Reviewer-Feedback)\n{retry_instruction}"

    raw = claude_cli.complete(system, user)
    anschreiben = _extract_section(raw, "anschreiben")
    tailored_profil_tex = _extract_section(raw, "profil_tex")
    return anschreiben, tailored_profil_tex


def review(anschreiben: str, tailored_profil_tex: str, profil_tex: str, common: dict[str, str]) -> ReviewResult:
    system = (
        load_rule("review-essentials") + "\n\n" + load_rule("customer-anonymization") + "\n\n" + REVIEW_INSTRUCTIONS
    )
    user = (
        f"## Anschreiben\n{anschreiben}\n\n"
        f"## Tailored profil.tex\n{tailored_profil_tex}\n\n"
        f"## Original profil.tex (Beleg-Quelle)\n{profil_tex}\n\n"
        f"## common/experience.tex (Beleg-Quelle)\n{common.get('experience', '')}"
    )
    raw = claude_cli.complete(system, user)
    return _parse_review(raw)


def _parse_review(raw: str) -> ReviewResult:
    verdict_match = re.search(
        r"###\s*Verdict\s*\n\s*(APPROVE|REQUEST CHANGES|MAPPING SCHWACH)", raw, re.IGNORECASE
    )
    if not verdict_match:
        raise PipelineError("no parseable ### Verdict in review output")
    verdict = verdict_match.group(1).upper()

    findings_match = re.search(r"###\s*Funde\s*\n(.*?)(?=###|\Z)", raw, re.DOTALL)
    findings = findings_match.group(1).strip() if findings_match else ""

    instruction_match = re.search(r"###\s*Writer-Instruction\s*\n(.*?)(?=###|\Z)", raw, re.DOTALL)
    writer_instruction = instruction_match.group(1).strip() if instruction_match else None

    return ReviewResult(verdict=verdict, findings=findings, writer_instruction=writer_instruction)


def evaluate(
    request: ComposeRequest,
    profil_tex: str,
    common: dict[str, str],
    anschreiben: str | None = None,
) -> MatchScore:
    """Blind screening simulation. Deliberately NOT given the fit analysis,
    matched keywords, or any writing context -- the evaluator must see
    exactly what a screening system sees, nothing more."""
    system = load_rule("match-eval") + "\n\n" + MATCH_EVAL_INSTRUCTIONS
    user = (
        "## Stellenausschreibung\n"
        f"Titel: {request.title}\n"
        f"Contract: {request.contract_type}, Remote: {request.remote_percent}%\n\n"
        f"{request.posting_text}"
        f"\n\n## CV: profil.tex\n{profil_tex}"
        f"\n\n## CV: common/experience.tex\n{common.get('experience', '')}"
    )
    if anschreiben:
        user += f"\n\n## Anschreiben\n{anschreiben}"
    raw = claude_cli.complete(system, user)
    data = _extract_json_block(raw)
    return MatchScore(raw_text=raw, **data)


def compose(request: ComposeRequest, profil_tex: str, common: dict[str, str]) -> ComposedApplication:
    fit = analyse(request, profil_tex, common)
    anschreiben, tailored_profil_tex = write(request, profil_tex, common, fit)
    result = review(anschreiben, tailored_profil_tex, profil_tex, common)

    review_retried = False
    if result.verdict == "REQUEST CHANGES" and result.writer_instruction:
        review_retried = True
        anschreiben, tailored_profil_tex = write(
            request, profil_tex, common, fit, retry_instruction=result.writer_instruction
        )
        result = review(anschreiben, tailored_profil_tex, profil_tex, common)

    # Blind screening score of the tailored result. If the evaluator found
    # honestly fixable wording and the single bounded retry wasn't already
    # spent on review findings, spend it here and re-review + re-score.
    score = evaluate(request, tailored_profil_tex, common, anschreiben=anschreiben)
    if score.fixable and not review_retried:
        instruction = "Match-Evaluation (Blind-Screening) fand ehrlich hebbare Punkte:\n" + "\n".join(
            f"- {item}" for item in score.fixable
        )
        anschreiben, tailored_profil_tex = write(request, profil_tex, common, fit, retry_instruction=instruction)
        result = review(anschreiben, tailored_profil_tex, profil_tex, common)
        score = evaluate(request, tailored_profil_tex, common, anschreiben=anschreiben)

    return ComposedApplication(
        fit_analysis=fit,
        anschreiben=anschreiben,
        tailored_profil_tex=tailored_profil_tex,
        review=result,
        needs_review=result.verdict != "APPROVE",
        match_score=score,
    )
