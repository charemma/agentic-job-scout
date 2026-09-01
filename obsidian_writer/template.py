"""Renders the exact shape of ~/Documents/Notes/Templates/Bewerbung.md so
notes jobscout creates are indistinguishable from ones the candidate creates by hand
-- the existing `kuro run apply` flow (and the candidate's own manual review) can
work with them unchanged.

`status` (draft/versendet/...) is the template's own manual tracking field
and is deliberately left at "draft" here -- the candidate progresses it himself as
he applies/hears back. jobscout's own pipeline outcome (composed vs
needs-review) goes into a separate `jobscout_status` field so the two never
collide.
"""

from __future__ import annotations

import yaml

from obsidian_writer.models import NotesRequest


def render(request: NotesRequest) -> str:
    frontmatter = {
        "tags": ["bewerbung", "jobscout"],
        "id": request.id,
        "status": "draft",
        "firma": request.company or "",
        "agentur": "",
        "kontakt": request.contact_name or "",
        "stundensatz": request.rate,
        "versandt": "",
        "portal": request.portal,
        "url": request.url,
        "contract_type": request.contract_type,
        "remote_percent": request.remote_percent,
        "matched_keywords": request.matched_keywords,
        "jobscout_status": request.status,
        "fit_level": request.fit_level,
        "match_score": request.match.total if request.match else None,
    }
    yaml_block = yaml.safe_dump(frontmatter, allow_unicode=True, sort_keys=False)

    gaps = "\n".join(f"- {gap}" for gap in request.gaps) or "(keine)"
    matched = ", ".join(request.matched_keywords) or "(keine)"
    match_section = _render_match_section(request)

    return f"""---
{yaml_block}---

## Beschreibung

{request.posting_text}

## Anschreiben

{request.anschreiben}
{match_section}
## Vorbereitung

> Automatisch von jobscout vorbefuellt (Fit-Level: {request.fit_level}) -- vor dem Gespraech gegenlesen.

### Warum bin ich ein guter fit

{request.fit_summary}

Gematchte Keywords: {matched}

### Framing was fehlt

{gaps}
"""


def _render_match_section(request: NotesRequest) -> str:
    """Mirrors the ## Match-Evaluation section the kuro apply flow's Themis
    step writes, so manual and jobscout-created notes stay interchangeable."""
    if request.match is None:
        return ""
    m = request.match
    missing = ", ".join(m.missing_keywords) or "(keine)"
    fixable = "\n".join(f"- {item}" for item in m.fixable) or "(keine)"
    real_gaps = "\n".join(f"- {item}" for item in m.real_gaps) or "(keine)"
    return f"""
## Match-Evaluation

### Match-Score: {m.total}%

Keyword-Score: {m.keyword_score}% | Semantik-Score: {m.semantic_score}%

### Fehlende Keywords

{missing}

### Ehrlich hebbare Punkte

{fixable}

### Echte Luecken

{real_gaps}
"""
