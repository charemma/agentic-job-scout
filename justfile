_default:
    @just --list

# Install dev dependencies for all three services into one .venv
venv:
    python3 -m venv .venv
    .venv/bin/pip install -q -r scanner/requirements-dev.txt
    .venv/bin/pip install -q -r application_writer/requirements-dev.txt
    .venv/bin/pip install -q -r obsidian_writer/requirements-dev.txt

# Run the full test suite (all three services)
test: venv
    .venv/bin/python -m pytest -q

# Build container images locally
docker-build-scanner:
    docker build -f Dockerfile.scanner -t jobscout-scanner:dev .

docker-build-application-writer:
    docker build -f Dockerfile.application-writer -t jobscout-application-writer:dev .

docker-build-obsidian-writer:
    docker build -f Dockerfile.obsidian-writer -t jobscout-obsidian-writer:dev .

docker-build-all: docker-build-scanner docker-build-application-writer docker-build-obsidian-writer

# Run the scanner once locally (needs env vars -- see k8s/secrets.md)
docker-run-scanner:
    docker run --rm --env-file .env jobscout-scanner:dev

# Bring up all services + fixtures locally via docker-compose (inner dev loop,
# no cluster needed -- see docker-compose.yml)
compose-up:
    docker compose up --build

compose-down:
    docker compose down -v

# Render kustomize and schema-check the manifests
k8s-validate:
    kustomize build k8s/ | kubeconform -strict -summary

# One-time interactive LinkedIn login to bootstrap a persisted session for
# the linkedin fetcher (see scripts/linkedin_login_bootstrap.py). Dedicated
# minimal venv -- scanner/requirements.txt, not the full `venv` recipe's
# three-services deps. Needs the whole scanner requirements (not just
# playwright) because the bootstrap script imports
# scanner.fetchers.linkedin for its USER_AGENT constant, which pulls in
# scanner.fetchers' package init (imports every portal module, e.g. httpx
# via base.py) as a side effect of the import.
# Built under /tmp, not in the repo: this repo is often accessed over NFS
# (e.g. Mac <-> home-node), and a Python venv's thousands of small files
# are painfully slow -- and prone to landing corrupted (missing bin/) --
# over a network filesystem. /tmp is always a real local disk.
linkedin-session-bootstrap:
    #!/usr/bin/env bash
    set -euo pipefail
    venv_dir="${TMPDIR:-/tmp}/jobscout-linkedin-bootstrap-venv"
    if [ ! -x "$venv_dir/bin/python" ]; then
        rm -rf "$venv_dir"
        python3 -m venv "$venv_dir"
        "$venv_dir/bin/pip" install -q -r scanner/requirements.txt
    fi
    "$venv_dir/bin/python" -m playwright install chromium
    "$venv_dir/bin/python" scripts/linkedin_login_bootstrap.py
