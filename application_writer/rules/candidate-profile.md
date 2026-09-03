# Candidate Profile (Example)

This is the "rule" file that grounds every LLM assessment -- the analysis
step in `pipeline.py` loads it as system context before judging a posting.
It encodes background, hard requirements, and edge cases the way a human
recruiter would carry them in their head, so the LLM judge has the same
context a person reviewing postings for this candidate would have.

The content below is a **sanitized example**, not the real profile used in
production -- rate expectations, exact employer history, and personal hard
constraints have been replaced with representative placeholders. Swap this
file for your own background and the rest of the pipeline (scanner,
assessment, compose, review) works unchanged: this is the one file designed
to be personalized per user.

## Identity (short)

- Senior Platform / DevOps / Security Engineer
- Deep Linux background, including regulated environments
- Freelancer, focus on platform engineering and security

## Technical foundation

**Linux & operating systems:**
- Long-standing Debian/Ubuntu experience
- Declarative multi-host NixOS configuration in personal OSS projects
- Embedded Linux (Yocto, cross-compilation)

**Containers & orchestration:**
- Docker for deployment, development, sandboxing
- Kubernetes, k3s (platform build-out and operations)

**CI/CD & IaC:**
- GitLab CI, GitHub Actions, Jenkins, Dagger
- Pulumi, Terraform, Ansible -- declarative over imperative
- Nix Flakes for reproducible builds

**Languages:**
- Python (tooling, integrations, automation)
- Rust (own OSS project)
- Go (microservices)
- Bash (CLI tooling)

**Security:**
- OSCP certified
- Bug bounty / responsible disclosure experience
- Web application security: OWASP, Burp/ZAP, pentesting, threat modeling
- Container hardening, base-image slimming, secrets management
- Security gates / SAST / SCA / SBOM in CI/CD

**AI / LLM:**
- Practical experience with Claude, OpenAI/Codex, Ollama
- MCP, agent workflows
- Own OSS project: a Rust CLI for reproducible AI agent teams
- This project itself (jobscout) -- a continuously running, self-hosted
  LLM workflow with role-specific stages for assessment, drafting,
  factual review, and blind scoring -- is direct evidence of building and
  operating a real LLM system end to end, not just prompting one

## Open source / own projects

- A Rust CLI for reproducible AI agent teams (YAML-defined graphs,
  deterministic audit trail)
- Declarative multi-host NixOS configuration
- A hardened NixOS IoT platform with Nix Flakes and cross-compilation
- Assorted tooling projects

## How this candidate works (cross-cutting strengths)

- **Platform thinking**: builds, operates, and hardens in parallel --
  not "knows tool X" but "builds, runs, and secures platforms across
  multiple engagements." Self-service models, DevContainer environments,
  operating-model definition.
- **Security runs through everything**: not a checkbox certification, but
  woven into platform work directly.
- **Automation as a default**: if it's done twice, it gets scripted.
- **Reproducibility as a habit**: Nix Flakes, deterministic builds,
  versioned configs.
- **Systems thinking**: "what happens when someone adds a second or third
  one of these?" is a standing question, not an afterthought.

## Match-analysis factors

When mapping this candidate against a job posting:

1. **Domain over tool**: a specific unfamiliar tool is a 2-3 week ramp-up.
   If the core domain (platform engineering, container orchestration,
   security) is covered, that's a fit -- tool gaps are not disqualifying.
2. **OSS and personal projects count**: experience demonstrated in the
   candidate's own repos counts equally to client-project experience, not
   as "just a hobby."
3. **Security is cross-cutting**: if a posting names security, treat it as
   built into the platform work already described, not a bonus skill.
4. **Frontend is a gap**: React/Vue/Svelte and modern BaaS stacks are
   explicitly out of scope -- postings requiring those should be scored
   accordingly.

## Employment form

Open to both contracting and permanent (part-time-to-full-time) roles,
evaluated equally as long as the remaining criteria fit.

## Example hard gate: domain focus

**Illustrative rule, not the real production one.** A real profile might
encode a hard requirement like "only postings with clear AI-security
relevance pass" -- demonstrating that this pipeline can encode a genuine
non-negotiable gate (not just a soft keyword weight), independent of how
strong the rest of the technical match looks. The point being shown here:
the assessment step is a real LLM-driven judgment against prose rules, not
a keyword scorer with a threshold.

## Positive signal example

A posting explicitly open EU-wide (not restricted to one country) is
treated as a standout signal and surfaced prominently in the notification
-- an example of how nuanced, non-obvious criteria can be encoded as plain
prose rather than structured filters.

## What this candidate does not do

- Pure frontend development (React, Vue, Angular)
- Pure data analysis / ML research without an engineering component
- Sales / business development
- Compliance consulting outside their technical domain
