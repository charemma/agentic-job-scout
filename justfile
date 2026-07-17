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
