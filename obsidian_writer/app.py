"""obsidian-writer: the only jobscout service with Obsidian vault access.

Runs pinned (nodeSelector) to the home-node node, where the vault is synced
locally via Syncthing -- see k8s/obsidian-writer-deployment.yaml. Writes are
scoped to exactly one subfolder (`1 Projects/Bewerbung Projekt/`) and never
read or touch anything else in the vault.
"""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException

from obsidian_writer.models import NotesRequest
from obsidian_writer.template import render

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("obsidian-writer")

SERVICE_TOKEN = os.environ["OBSIDIAN_WRITER_TOKEN"]
VAULT_PATH = Path(os.environ.get("VAULT_PATH", "/vault"))
BEWERBUNG_PROJEKT_DIR = VAULT_PATH / "1 Projects" / "Bewerbung Projekt"

_SAFE_ID = re.compile(r"^[a-zA-Z0-9_-]+$")

app = FastAPI(title="obsidian-writer")


def _check_auth(authorization: str | None) -> None:
    if authorization != f"Bearer {SERVICE_TOKEN}":
        raise HTTPException(status_code=401, detail="invalid or missing bearer token")


def _note_path(application_id: str) -> Path:
    # Defense in depth: `id` ultimately comes from a scraped external source
    # (portal posting id). Reject anything that isn't a plain slug before it
    # ever touches a real path on the user's machine -- this service is the
    # one place in jobscout with host filesystem write access.
    if not _SAFE_ID.match(application_id):
        raise HTTPException(status_code=400, detail="invalid id: must match [a-zA-Z0-9_-]+")
    return BEWERBUNG_PROJEKT_DIR / f"{application_id}.md"


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok", "vault_reachable": BEWERBUNG_PROJEKT_DIR.parent.exists()}


@app.post("/notes")
def notes(request: NotesRequest, authorization: str | None = Header(default=None)) -> dict:
    _check_auth(authorization)

    note_path = _note_path(request.id)
    BEWERBUNG_PROJEKT_DIR.mkdir(parents=True, exist_ok=True)

    if note_path.exists():
        log.info("note for %s already exists, leaving the candidate's edits alone, skipping overwrite", request.id)
        return {"id": request.id, "written": False, "reason": "note already exists"}

    note_path.write_text(render(request), encoding="utf-8")
    log.info("wrote %s", note_path)
    return {"id": request.id, "written": True}
