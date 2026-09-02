# jobscout

An automated freelance/permanent job search pipeline. It scans a handful of job portals on a schedule, has an LLM judge each posting's fit against a candidate CV, drafts a tailored CV and cover letter for the strong matches, and pushes a notification -- all unattended, running as a Kubernetes CronJob plus two backing services on a personal k3s cluster. Nothing gets auto-submitted; every draft lands as `needs-review` for a human to read and send.

## Architecture

```
                 ┌────────────────────────────────────────────┐
                 │                  scanner                    │
                 │        (k8s CronJob, 6x/day, 8-19 Uhr)       │
                 │                                              │
freelancermap ─▶ │  fetch ─▶ match ─▶ assess ─▶ notify ─▶ compose│
xing, linkedin ─▶│  (Playwright/httpx  (keyword   (LLM fit  (ntfy) (trigger)
hays, solcom ───▶│   per-portal        prefilter) via /assess)
randstad, ...  ─▶│   fetchers)                                  │
                 └───────────────────┬──────────────────────────┘
                                      │ POST /assess, POST /compose
                                      ▼
                 ┌────────────────────────────────────────────┐
                 │            application-writer                │
                 │         (FastAPI Deployment)                  │
                 │                                              │
                 │  analysis ─▶ write ─▶ self-review             │
                 │  (fit_level,  (tailored   (bounded 1 round,   │
                 │   match score) CV + cover  1 retry on         │
                 │                letter)    REQUEST CHANGES)    │
                 │                                              │
                 │  -- via claude_cli.py (`claude -p` subprocess)│
                 │  -- commits result to jobscout-applications   │
                 └──────┬───────────────────────────┬───────────┘
                        │ ntfy push                  │ POST /notes
                        ▼                             ▼
                 ┌─────────────┐          ┌────────────────────────┐
                 │    ntfy     │          │     obsidian-writer      │
                 │ (external)  │          │   (FastAPI Deployment,   │
                 └─────────────┘          │  pinned to vault node)   │
                                            │                          │
                                            │  writes one note per     │
                                            │  application to the      │
                                            │  Obsidian vault           │
                                            └────────────────────────┘
```

Three services, deliberately split so a blast radius stays contained:

- **scanner** -- the entrypoint, runs as a k8s CronJob. Fetches postings from each configured portal (freelancermap, xing, linkedin, hays, solcom, randstad, freelance.de) via Playwright-based fetchers, keyword-prefilters them against `config.yaml`, and for anything that clears the prefilter calls application-writer's `/assess` endpoint for an LLM fit judgment. A strong-enough match fires an ntfy notification and, if `compose_enabled`, triggers `/compose` to generate the full application. Fetch/assess/notify/compose failures for one posting are isolated -- they don't take down the run.
- **application-writer** -- FastAPI service exposing `/assess` and `/compose`. Runs an analysis -> write -> self-review pipeline (`pipeline.py`) against prose "rule" files in `application_writer/rules/` that encode the candidate's background and review criteria. All LLM calls go through `claude_cli.py`, which shells out to the `claude` CLI rather than calling the Anthropic API directly. Composed results (tailored CV + Anschreiben + blind match score) get committed to the sibling `jobscout-applications` repo as an audit trail, then trigger an Obsidian note and an ntfy push.
- **obsidian-writer** -- FastAPI service, the only one with filesystem access to the real Obsidian vault (synced via Syncthing onto a home k3s node). Pinned to that node via a node label. Writes one note per application; nothing else touches the vault.

ntfy notifications fire from two separate stages: scanner sends a "found a match" push as soon as `/assess` returns a strong fit, and application-writer sends a "draft ready" push once `/compose` finishes.

## Repo layout

- `scanner/` -- CronJob entrypoint, per-portal fetchers, keyword matcher, application-writer client
- `application_writer/` -- FastAPI app, `claude_cli.py` (Claude CLI shellout), `pipeline.py` (analysis/write/review), prose rule files under `rules/`
- `obsidian_writer/` -- FastAPI app, note template, sole writer to the Obsidian vault
- `k8s/` -- kustomize manifests (CronJob + two Deployments), plus `secrets.md` documenting one-time cluster bootstrap
- `scripts/` -- one-time interactive session bootstrap scripts for portals that need a persisted login (LinkedIn, Xing)
- `config.yaml` / `config.local.yaml` -- committed static config vs. gitignored local override
- `docker-compose.yml` -- local inner dev loop, all services wired together
- `justfile` -- task runner: venv/test/docker-build/compose/k8s-validate/session-bootstrap recipes

## Prerequisites

- Python 3.x
- [`just`](https://github.com/casey/just)
- Docker / Docker Compose
- `kustomize` and `kubeconform` (only needed for `just k8s-validate`)
- Sibling repo checkouts at `../cv` and `../jobscout-applications` (required for `docker-compose.yml`'s build contexts and read-only mounts)
- A logged-in `claude` CLI session (application-writer's LLM calls go through the CLI, not an API key)

## Quickstart: run it locally

```sh
just venv          # creates .venv, installs dev deps for all three services
just test          # runs the full pytest suite

just compose-up     # builds and runs all services via docker-compose
# or, for a one-shot run matching the real CronJob invocation:
docker compose run --rm scanner
```

`docker-compose.yml` mounts the sibling `../cv` and `../jobscout-applications` checkouts and requires `NTFY_TOKEN` to be set in the environment (`${NTFY_TOKEN:?...}` fails fast if it's missing) -- either use a real token for `ntfy.charemma.de` or point `NTFY_BASE_URL` at a throwaway local ntfy container.

## Configuration

- **`config.yaml`** -- committed, static settings: keywords, `min_fit_level`, per-portal search URLs, ntfy topic.
- **`config.local.yaml`** -- gitignored override for local test runs (e.g. pointing `base_url` at `localhost` instead of the in-cluster DNS name, or `applications_repo.clone_url` at a `file://` path instead of GitHub). Not present in a fresh checkout -- create it yourself, typically by copying `config.yaml` and editing the bits that differ locally.
- **`.env`** -- gitignored, per-portal `<PORTAL>_USER` / `<PORTAL>_PASS` credentials for local runs.

`JOBSCOUT_CONFIG` selects which config file the scanner reads (defaults to `config.yaml`); point it at `config.local.yaml` for a local override.

## Secrets and credentials

Locally: `.env` holds per-portal login credentials for the scanner. In-cluster: everything comes from k8s Secrets, referenced via `envFrom` in the manifests. `k8s/secrets.md` documents the full one-time bootstrap -- ntfy tokens, inter-service bearer tokens, a GitHub PAT for the `jobscout-applications` commits, a long-lived Claude Code OAuth token (`claude setup-token`, not a mounted `credentials.json` -- see its rationale below), and persisted LinkedIn/Xing browser sessions. None of it is meant to be copy-pasted blindly; it's real one-time setup notes for this specific cluster, not a generic runbook.

## Deploying

`k8s/` is a kustomize base: `scanner-cronjob.yaml` for the scanner, `application-writer-deployment.yaml` / `obsidian-writer-deployment.yaml` (+ matching Services) for the two backing services. Images are built from the three `Dockerfile.*` files and pushed to `ghcr.io/charemma/jobscout-{scanner,application-writer,obsidian-writer}` by CI; tags are bumped in `k8s/kustomization.yaml`. Run `just k8s-validate` (kustomize build + kubeconform) before applying anything.

## Why an LLM assesses fit instead of keyword matching alone

Keyword matching in `config.yaml` is a cheap prefilter, nothing more -- it decides whether a posting is worth spending an LLM call on, not whether it's actually a good match. The real judgment (`fit_level`: `schwach` / `solide` / `stark`, plus a blind match score against the candidate's CV) comes from a `claude -p` completion in `application_writer/claude_cli.py`.

That module shells out to the Claude Code CLI rather than calling the Anthropic Messages API directly. With `ANTHROPIC_API_KEY` unset and a long-lived OAuth token (`CLAUDE_CODE_OAUTH_TOKEN`, from `claude setup-token`) supplied instead, usage bills against a Claude Code subscription rather than metered per-token pricing -- deliberate, and worth keeping unset in-cluster, since setting `ANTHROPIC_API_KEY` silently switches billing back to the metered API path.

The actual reasoning happens in `pipeline.py`'s bounded analysis -> write -> self-review pipeline: one analysis pass produces the fit judgment, a write pass drafts the CV/cover letter, and a single self-review round can send it back for at most one retry. Anything that's still flagged after that retry (or scored `schwach` at any point) gets committed with `status="needs-review"` instead of `"composed"` -- consistent with the project never auto-submitting anything.

## Testing

```sh
just test
```

Runs pytest across all three services (`scanner/tests`, `application_writer/tests`, `obsidian_writer/tests`). Tests run against fixture data -- no live portal scraping and no live LLM calls.

## Gotchas

- `docker-compose.yml` assumes sibling checkouts at `../cv` and `../jobscout-applications` (used as build contexts and read-only volume mounts). It won't build or run without them present next to this repo -- adjust the paths in the compose file if your layout differs.
- `config.yaml`'s `applications_repo.clone_url` and `application_writer.base_url` point at real GitHub and an in-cluster k8s DNS name by default. A fully offline compose run needs a `config.local.yaml` override with a `file://` clone URL and a `localhost` base URL.
- `NTFY_TOKEN` is a hard requirement for both the `application-writer` and `scanner` compose services -- either get a real token for `ntfy.charemma.de` or point `NTFY_BASE_URL` at a throwaway local ntfy container.
- application-writer's LLM calls need a working `claude` CLI session, not an API key. Local dev mounts `~/.claude/.credentials.json` read-only into the container; `ANTHROPIC_API_KEY` must stay unset in-cluster or it silently falls back to metered billing (see `application_writer/claude_cli.py` and `k8s/secrets.md` section 3a).
- Every portal fetcher logs in via Playwright now -- anonymous access was never confirmed to return the complete result set for any portal. That means `<PORTAL>_USER` / `<PORTAL>_PASS` credentials in `.env` are required for the scanner to return real results locally, and LinkedIn/Xing additionally need a one-time interactive session bootstrap (`just linkedin-session-bootstrap` / `just xing-session-bootstrap`) or they'll hit 2FA/bot-detection checkpoints.
- AppleDouble/resource-fork files (`._config.yaml`, `._docker-compose.yml`, `._.env`, etc.) show up in the working tree from macOS/NFS usage. They're not part of the project -- don't commit them or read them as real config.
- The scanner CronJob is scheduled and node-pinned for a specific home cluster setup (the `home-node` node, Europe/Athens business hours only). Running it elsewhere means re-deriving those k8s specifics -- this isn't a portable out-of-the-box deploy target.
- `obsidian-writer` only makes sense with a real synced Obsidian vault mounted at `VAULT_PATH`. Local compose uses a throwaway scratch directory (`./.devdata/vault`) so notes written during local testing never touch the real vault.

## Known limitations / non-goals

- Never auto-submits applications -- everything lands as `composed`/`needs-review` for manual review before sending.
- Portal login flows are fragile and site-specific; see individual fetcher docstrings in `scanner/fetchers/` for portal-specific caveats.
- The scanner is pinned to a home-network node for bot-detection reasons, so it only runs on this specific self-hosted cluster as configured today -- not a general-purpose deploy.

## License

MIT. See [LICENSE](LICENSE).
