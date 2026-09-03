import pytest

from application_writer.llm.claude_cli_backend import ClaudeCliBackend
from application_writer.llm.codex_cli_backend import CodexCliBackend
from application_writer.llm.config import load_llm_config
from application_writer.llm.fake_backend import FakeBackend
from application_writer.llm.router import BackendRouter, LLMConfigError, build_backend, build_router

CONFIG = {
    "backends": {
        "claude": {"type": "claude-cli", "model": "sonnet", "timeout_seconds": 180},
        "codex": {"type": "codex-cli", "model": "auto", "timeout_seconds": 90},
    },
    "stages": {
        "analysis": "claude",
        "writing": "claude",
        "review": "codex",
        "scoring": "codex",
    },
}


def test_build_router_resolves_stage_to_backend_instance():
    router = build_router(CONFIG)

    assert isinstance(router.for_stage("analysis"), ClaudeCliBackend)
    assert isinstance(router.for_stage("review"), CodexCliBackend)


def test_build_router_applies_per_backend_model_and_timeout():
    router = build_router(CONFIG)

    claude = router.for_stage("writing")
    codex = router.for_stage("scoring")
    assert claude.model == "sonnet"
    assert claude.timeout_seconds == 180
    assert codex.model == "auto"
    assert codex.timeout_seconds == 90


def test_same_backend_type_different_stages_can_have_different_models():
    config = {
        "backends": {
            "claude-fast": {"type": "claude-cli", "model": "haiku"},
            "claude-strong": {"type": "claude-cli", "model": "fable"},
        },
        "stages": {"analysis": "claude-fast", "writing": "claude-strong"},
    }
    router = build_router(config)

    assert router.for_stage("analysis").model == "haiku"
    assert router.for_stage("writing").model == "fable"


def test_for_stage_raises_llm_config_error_for_unknown_stage():
    router = build_router(CONFIG)
    with pytest.raises(LLMConfigError):
        router.for_stage("summarization")


def test_build_router_raises_when_stage_points_at_undefined_backend():
    config = {"backends": {"claude": {"type": "claude-cli"}}, "stages": {"analysis": "does-not-exist"}}
    router = build_router(config)
    with pytest.raises(LLMConfigError):
        router.for_stage("analysis")


def test_build_backend_raises_on_missing_type():
    with pytest.raises(LLMConfigError):
        build_backend("claude", {"model": "sonnet"})


def test_build_backend_raises_on_unknown_type():
    with pytest.raises(LLMConfigError):
        build_backend("claude", {"type": "not-a-real-backend"})


def test_build_router_raises_on_missing_sections():
    with pytest.raises(LLMConfigError):
        build_router({"backends": {}})  # no "stages"
    with pytest.raises(LLMConfigError):
        build_router({"stages": {}})  # no "backends"


def test_fake_backend_type_is_buildable_from_config():
    router = build_router(
        {
            "backends": {"stub": {"type": "fake", "fixed_response": "canned"}},
            "stages": {"analysis": "stub"},
        }
    )
    backend = router.for_stage("analysis")
    assert isinstance(backend, FakeBackend)
    assert backend.fixed_response == "canned"


def test_load_llm_config_reads_the_real_config_yaml():
    """The actual committed config.yaml -- catches drift between the
    documented `llm:` shape and what's really in the repo."""
    llm_config = load_llm_config()
    router = build_router(llm_config)

    # every stage pipeline.py actually calls must resolve to a real backend
    for stage in ("analysis", "writing", "review", "scoring"):
        backend = router.for_stage(stage)
        assert hasattr(backend, "complete")

    # the project's stated default: Claude CLI everywhere unless someone
    # deliberately reconfigures a stage
    assert isinstance(router.for_stage("analysis"), ClaudeCliBackend)


def test_backend_router_construction_directly():
    claude = FakeBackend(name="claude")
    router = BackendRouter(backends={"claude": claude}, stages={"analysis": "claude"})
    assert router.for_stage("analysis") is claude
