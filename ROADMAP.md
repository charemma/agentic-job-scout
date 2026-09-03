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

**Status: mostly done, one item outstanding.**

- [x] Add the missing MIT LICENSE file.
- [x] Restore a green GitHub Actions workflow and add a CI badge to the README.
- [x] Replace internal hostnames, filesystem paths, repository names, and personal service URLs with documented placeholders.
- [x] Remove stale references to private agent names and renamed files.
- [x] Replace real portal responses in test fixtures with synthetic or fully anonymized data.
- [ ] Reduce dated debugging history in source comments; keep comments focused on current design decisions. Not done -- source comments still carry a lot of dated "found on 2026-08-xx" narrative from real development history, kept deliberately so the repo reads as a genuine project rather than a scrubbed snapshot. Worth a pass to trim the least useful ones, but that's a judgment call on a case-by-case basis, not a mechanical find-and-replace.
- [x] Document portal connectors neutrally and make compliance with portal terms the operator's responsibility.

**Done when:** an unauthenticated reader can understand the repository without access to any private sibling project, and the default branch has a green CI status. (Both true as of the backend-abstraction work in item 2.)

### 2. Pluggable LLM backends

**Status: architecture done, two of four backends implemented.** `pipeline.py` now calls `router.for_stage(<stage>)` instead of `claude_cli.complete()` directly (see `application_writer/llm/`), and which backend/model handles each stage is a `config.yaml` change, not a code change -- confirmed by tests that route the writer through one fake backend and the reviewer through another with no `pipeline.py` changes. `ClaudeCliBackend` (the default), `CodexCliBackend`, and a `FakeBackend` for tests exist and are covered by contract tests against fake executables -- no paid or live model calls happen in the test suite. `AnthropicApiBackend` and `OpenAIApiBackend` are not implemented yet (see "Later" below); the interface was designed so adding them doesn't require touching `pipeline.py`.

`CodexCliBackend` has a caveat worth knowing about: `codex exec` has no flag to fully disable tool/shell use the way `claude -p --tools ""` does, so it runs as a bounded coding agent under `--sandbox read-only` rather than a true stateless completion. Its live success path also hasn't been exercised against a real `codex exec` run in this repo's dev environment (the CLI login was broken when this was built) -- only the failure-path event shape was verified live. See the module's docstring for specifics.

Planned backends:

- `ClaudeCliBackend` -- done
- `CodexCliBackend` -- done, with the caveats above
- `AnthropicApiBackend` -- not started
- `OpenAIApiBackend` -- not started
- deterministic fake backend for tests and local demos -- done (`FakeBackend`)

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

This example routes review/scoring to Codex to illustrate the capability -- the actual `config.yaml` shipped in this repo routes every stage to `claude` (see "Deliberate default" below), since Codex hasn't been exercised against a live successful run here yet.

Every backend should return one normalized result containing:

- generated text
- backend and resolved model
- duration
- retry count
- provider metadata and usage information when available

**Done when:** each stage can use a different configured backend without changes to `pipeline.py`, and all backend contract tests run without paid model calls.

**Deliberate default: CLI subscription billing, not a metered API.** Every stage in the shipped `config.yaml` uses `ClaudeCliBackend`, which shells out to `claude -p` and bills against a Claude Code subscription rather than per-token API pricing (see `claude_cli_backend.py`'s docstring). That's the right tradeoff for what this actually is: one person's low-volume personal job-search pipeline, running a handful of times a day. It is not the right tradeoff for a shared or high-volume deployment -- many concurrent users, or a much higher request rate, would hit CLI-subprocess overhead and per-session limits long before a metered API would become the more expensive option. `AnthropicApiBackend` / `OpenAIApiBackend` (see "Later") exist in the roadmap specifically for that case, not because the CLI approach is a stopgap to be replaced -- both are meant to coexist, selected per deployment shape via config.

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
