# agentic-job-scout

I got tired of manually checking freelance portals every day, so I built a pipeline that does it for me. It watches a handful of job boards, has an LLM read each posting the way I would, and for the good matches drafts a tailored CV and cover letter. I still read and send everything myself -- nothing goes out without me looking at it first.

It runs as three small services on Kubernetes instead of one script, mostly because I wanted a real system with actual service boundaries, not a cron job full of `if` statements.

## How it works

A CronJob (`scanner`) checks the configured portals on a schedule and filters postings by keyword. Anything that clears that filter gets sent to `application-writer`, a FastAPI service that asks an LLM whether it's actually a good match against a written profile of my background -- real judgment, not just keyword scoring. Things like "only AI-security roles" or "remote-only for permanent positions" live in that profile as plain prose, the way I'd explain them to a recruiter.

For a strong match, the same service drafts a CV and cover letter, then runs a second LLM pass over its own draft to check that every claim actually traces back to something real, and rewrites once if it doesn't hold up. Anything still shaky gets flagged `needs-review` instead of `composed` -- I read everything before it's sent. Every draft is committed to a separate repo as a running history of what got generated and when. A third service, `obsidian-writer`, writes a note per application into my own notes so I have it there too.

## Make it yours

Everything specific to a candidate -- background, hard requirements, edge cases -- lives in one file: `application_writer/rules/candidate-profile.md`. The LLM reads it as context before judging or drafting anything. Swap that file (and the keywords in `config.yaml`) and the same pipeline runs for someone else, no code changes needed.

The version in this repo is a sanitized example, not my real profile -- name, rate, and client history are placeholders. The logic is the real thing though.

## Running it

```sh
just venv          # install deps for all three services
just test           # run the test suite
just compose-up     # run everything locally via docker-compose
```

Config lives in `config.yaml` (committed) with a gitignored `config.local.yaml` for local overrides. Secrets come from `.env` locally and Kubernetes Secrets in the cluster -- `k8s/secrets.md` has the one-time bootstrap steps. Deploys go through a kustomize base under `k8s/`, checked with `just k8s-validate`. LLM calls go through an authenticated CLI session rather than a raw API key.

## A few things worth knowing

Applications aren't auto-submitted -- I always read and send them myself. Portal logins are fragile and different per site; the fetcher docstrings in `scanner/fetchers/` have the details. The scanner is pinned to a specific node in my home cluster for bot-detection reasons, so it's tuned for my setup rather than a drop-in deploy elsewhere.

MIT licensed, see [LICENSE](LICENSE).
