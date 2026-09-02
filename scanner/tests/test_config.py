from scanner.config import Secrets


def _secrets() -> Secrets:
    return Secrets(ntfy_token="t", applications_repo_token="t", application_writer_token="t")


def test_session_state_path_for_returns_path_when_file_exists(tmp_path, monkeypatch):
    monkeypatch.setenv("JOBSCOUT_SESSION_DIR", str(tmp_path))
    (tmp_path / "linkedin.json").write_text("{}")

    result = _secrets().session_state_path_for("linkedin")

    assert result == tmp_path / "linkedin.json"


def test_session_state_path_for_returns_none_when_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("JOBSCOUT_SESSION_DIR", str(tmp_path))

    assert _secrets().session_state_path_for("xing") is None


def test_session_state_path_for_returns_none_for_empty_directory(tmp_path, monkeypatch):
    """Reproduces the k8s subPath + optional-Secret gotcha: when the
    referenced Secret doesn't exist, kubelet still creates the subPath
    mount point as an empty directory rather than leaving it absent."""
    monkeypatch.setenv("JOBSCOUT_SESSION_DIR", str(tmp_path))
    (tmp_path / "xing.json").mkdir()

    assert _secrets().session_state_path_for("xing") is None
