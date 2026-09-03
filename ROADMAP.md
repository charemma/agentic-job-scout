# Roadmap

Agentic Job Scout started as a way to improve a recurring personal workflow and to gain hands-on experience designing, evaluating, and operating LLM-based systems. The roadmap focuses on making the project more portable, observable, secure, and useful as a technical reference without turning it into an automatic application-submission service.

## Current state

- Multi-portal scanner with configurable keyword prefiltering
- LLM-based fit assessment against a prose candidate profile
- Separate analysis, drafting, factual-review, and blind-scoring stages
- Bounded feedback loops and explicit `needs-review` handling
- Human review before any application is used
- FastAPI services, container images, Kubernetes manifests, and GitOps deployment
- Version-controlled application artifacts and push notifications
- Automated test suite

## Near term

### 1. Clean public reference version

- Add the missing MIT LICENSE file.
- Restore a green GitHub Actions workflow and add a CI badge to the README.
- Replace internal hostnames, filesystem paths, repository names, and personal service URLs with documented placeholders.
- Remove stale references to private agent names and renamed files.
- Replace real portal responses in test fixtures with synthetic or fully anonymized data.
- Reduce dated debugging history in source comments; keep comments focused on current design decisions.
- Document portal connectors neutrally and make compliance with portal terms the operator's responsibility.

**Done when:** an unauthenticated reader can understand the repository without access to any private sibling project, and the default branch has a green CI status.

### 2. Pluggable LLM backends

Introduce a small provider-independent interface instead of calling `claude_cli.complete()` directly from the pipeline.

Planned backends:

- `ClaudeCliBackend`
- `CodexCliBackend`
- `AnthropicApiBackend`
- `OpenAIApiBackend`
- deterministic fake backend for tests and local demos

Keep backend selection separate from model selection. Configure both per pipeline stage:

```yaml
llm:
  backends:
    claude:
      type: claude-cli
      model: sonnet
      timeout_seconds: 180

    codex:
      type: codex-cli
      model: auto
      timeout_seconds: 180

  stages:
    analysis: claude
    writing: claude
    review: codex
    scoring: codex
```

Every backend should return one normalized result containing:

- generated text
- backend and resolved model
- duration
- retry count
- provider metadata and usage information when available

**Done when:** each stage can use a different configured backend without changes to `pipeline.py`, and all backend contract tests run without paid model calls.

### 3. Cross-model review and evaluation

- Allow the writer and reviewer to use different providers or models.
- Record the backend and model used for every pipeline stage in the audit trail.
- Compare same-model and cross-model review outcomes on a small sanitized evaluation set.
- Keep retries bounded and never silently switch providers.
- Make fallback behavior explicit and configurable.

**Done when:** a Claude-generated draft can be reviewed and scored by Codex, with the complete execution path visible in the stored metadata.

### 4. Portable local demo

- Add a synthetic candidate profile and sample job postings.
- Add a fake LLM backend with deterministic fixture responses.
- Remove mandatory dependencies on private sibling repositories from the demo path.
- Provide a local notification sink instead of requiring a real ntfy server.
- Make `just demo` run the complete pipeline without credentials or paid model usage.
- Include one sanitized end-to-end example in the README.

**Done when:** a new contributor can clone the repository and see a complete assessment, draft, review, and audit-trail result with one command.

## Reliability and security

### 5. Backend and subprocess hardening

- Pin tested CLI versions in container builds.
- Avoid passing sensitive prompt content through process arguments where possible.
- Preserve explicit timeouts, bounded retries, disabled tools, and disabled session persistence for completion-only CLI backends.
- Use structured backend-specific error types and normalized failure reporting.
- Ensure model, token, and budget settings are actually forwarded by every backend.
- Add cancellation handling for timed-out HTTP requests and child processes.

### 6. Credentials and Git operations

- Stop embedding repository tokens in Git remote URLs.
- Use a short-lived credential helper, `GIT_ASKPASS`, or an equivalent mechanism.
- Confirm credentials cannot appear in process lists, logs, exception messages, or persisted `.git/config` files.
- Document the minimum required scopes for every credential.

### 7. Kubernetes hardening

- Add CPU and memory requests and limits.
- Add `runAsNonRoot`, `allowPrivilegeEscalation: false`, a runtime-default seccomp profile, and dropped Linux capabilities.
- Use read-only root filesystems where compatible.
- Add NetworkPolicies for service-to-service traffic.
- Replace deployment-specific host paths and node names with overlays or documented placeholders.
- Add an example production overlay separate from the portable base.

## Quality and evaluation

### 8. Configuration consistency

- Define target rate and candidate identity in one configuration source.
- Remove duplicated constants from the scanner, writer, and prompt pipeline.
- Validate configuration on startup with a typed schema.
- Rename the committed configuration to `config.example.yaml` if runtime values are deployment-specific.

### 9. Reproducible builds

- Add a dependency lockfile or pinned constraints.
- Pin container base images and important build tooling.
- Build all service images in CI without publishing on pull requests.
- Publish images only from a green, trusted main-branch workflow.

### 10. LLM evaluation and observability

- Create a sanitized evaluation set containing strong, borderline, and weak job matches.
- Track structured-output failures, retry rates, latency, and review verdicts.
- Measure disagreement between analysis, review, and blind scoring.
- Add OpenTelemetry traces or equivalent correlation across scanner, writer, reviewer, and notification steps.
- Track estimated usage without logging candidate profiles, CV contents, or full prompts.

## Later

- Optional support for locally hosted models.
- Model-routing policies based on stage, cost, latency, and required capability.
- A small comparison report for backend/model combinations.
- Additional output formats and knowledge-base integrations.
- Improved handling of duplicate or updated postings across portals.
- A lightweight UI for reviewing fit assessments and generated drafts.

## Non-goals

- Automatically submitting applications
- Removing human judgment from application decisions
- Pretending a personal reference deployment is a turnkey enterprise product
- Hiding real skill or technology gaps in generated application material
- Adding autonomous tool use where deterministic orchestration is safer and sufficient
