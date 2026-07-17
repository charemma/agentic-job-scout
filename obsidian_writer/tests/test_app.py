import os

os.environ.setdefault("OBSIDIAN_WRITER_TOKEN", "test-obsidian-token")

from fastapi.testclient import TestClient  # noqa: E402

from obsidian_writer import app as app_module  # noqa: E402

client = TestClient(app_module.app)

VALID_PAYLOAD = {
    "id": "freelancermap-1",
    "title": "DevOps Engineer",
    "company": "Acme GmbH",
    "contact_name": "Frau Muster",
    "portal": "freelancermap",
    "url": "https://example.com/job",
    "contract_type": "contracting",
    "remote_percent": 100,
    "posting_text": "Wir suchen DevOps mit Kubernetes.",
    "rate": 100,
    "anschreiben": "Sehr geehrte Frau Muster, ...",
    "fit_level": "stark",
    "fit_summary": "Guter Fit auf DevOps und Kubernetes.",
    "matched_keywords": ["devops", "kubernetes"],
    "gaps": ["terraform"],
    "status": "composed",
}


def test_notes_requires_auth():
    response = client.post("/notes", json=VALID_PAYLOAD)
    assert response.status_code == 401


def test_notes_writes_note_matching_real_template_shape(monkeypatch, tmp_path):
    monkeypatch.setattr(app_module, "VAULT_PATH", tmp_path)
    monkeypatch.setattr(app_module, "BEWERBUNG_PROJEKT_DIR", tmp_path / "1 Projects" / "Bewerbung Projekt")

    response = client.post(
        "/notes", json=VALID_PAYLOAD, headers={"Authorization": "Bearer test-obsidian-token"}
    )

    assert response.status_code == 200
    assert response.json() == {"id": "freelancermap-1", "written": True}

    note_path = tmp_path / "1 Projects" / "Bewerbung Projekt" / "freelancermap-1.md"
    content = note_path.read_text(encoding="utf-8")
    assert content.startswith("---\n")
    assert "## Beschreibung" in content
    assert "## Anschreiben" in content
    assert "### Warum bin ich ein guter fit" in content
    assert "### Framing was fehlt" in content
    assert "Sehr geehrte Frau Muster" in content


def test_notes_does_not_overwrite_existing_note(monkeypatch, tmp_path):
    bewerbung_dir = tmp_path / "1 Projects" / "Bewerbung Projekt"
    bewerbung_dir.mkdir(parents=True)
    existing = bewerbung_dir / "freelancermap-1.md"
    existing.write_text("the candidate's eigene Notizen, nicht anfassen.", encoding="utf-8")

    monkeypatch.setattr(app_module, "VAULT_PATH", tmp_path)
    monkeypatch.setattr(app_module, "BEWERBUNG_PROJEKT_DIR", bewerbung_dir)

    response = client.post(
        "/notes", json=VALID_PAYLOAD, headers={"Authorization": "Bearer test-obsidian-token"}
    )

    assert response.status_code == 200
    assert response.json()["written"] is False
    assert existing.read_text(encoding="utf-8") == "the candidate's eigene Notizen, nicht anfassen."


def test_notes_rejects_path_traversal_id(monkeypatch, tmp_path):
    monkeypatch.setattr(app_module, "VAULT_PATH", tmp_path)
    monkeypatch.setattr(app_module, "BEWERBUNG_PROJEKT_DIR", tmp_path / "1 Projects" / "Bewerbung Projekt")

    payload = {**VALID_PAYLOAD, "id": "../../../etc/passwd"}
    response = client.post(
        "/notes", json=payload, headers={"Authorization": "Bearer test-obsidian-token"}
    )

    assert response.status_code == 400
