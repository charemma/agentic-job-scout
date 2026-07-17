"""HTTP client for cv-service -- the only way application-writer touches
CV content, so cv-service stays the sole owner of the cv git checkout."""

from __future__ import annotations

import httpx


def fetch_profile(base_url: str, token: str) -> tuple[str, dict[str, str]]:
    response = httpx.get(
        f"{base_url.rstrip('/')}/profile",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30.0,
    )
    response.raise_for_status()
    data = response.json()
    return data["profil_tex"], data["common"]


def build_pdf(base_url: str, token: str, application_id: str, profil_tex: str) -> bytes:
    response = httpx.post(
        f"{base_url.rstrip('/')}/build",
        json={"id": application_id, "profil_tex": profil_tex},
        headers={"Authorization": f"Bearer {token}"},
        timeout=120.0,  # LaTeX builds are slow, and may be queued behind another build
    )
    response.raise_for_status()
    return response.content
