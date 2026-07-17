# jobscout Deployment Secrets

One-time `kubectl` steps against the live cluster, same style as
`zeddl`/`cv`'s sibling docs. Not automated here -- run with the candidate present.

## 0. Namespace + image pull secret

```bash
kubectl create namespace jobscout
read -s GHCR_TOKEN  # PAT with read:packages scope, same one used for other apps
kubectl create secret docker-registry ghcr-pull-secret \
  --namespace jobscout \
  --docker-server=ghcr.io \
  --docker-username=charemma \
  --docker-password="$GHCR_TOKEN"
```

## 1. Shared values (create these first, referenced below)

```bash
read -s NTFY_TOKEN                     # publish-only token for the "jobscout" ntfy topic
                                        # (create the ntfy user/ACL first -- see step 4)
read -s APPLICATIONS_REPO_TOKEN        # GitHub PAT, write access, charemma/jobscout-applications
read -s ANTHROPIC_API_KEY
read -s APPLICATION_WRITER_TOKEN       # shared bearer secret: scanner -> application-writer
read -s CV_SERVICE_TOKEN               # shared bearer secret: application-writer -> cv-service
                                        # (must match cv-service's secret, see cv/k8s/secrets.md)
read -s OBSIDIAN_WRITER_TOKEN          # shared bearer secret: application-writer -> obsidian-writer

# Optional, only if the freelancermap fetcher ends up needing a login
# (not required for the search/matching itself -- see scanner/fetchers/freelancermap.py docstring)
read -s FREELANCERMAP_USERNAME
read -s FREELANCERMAP_PASSWORD
```

## 2. jobscout-scanner secrets

```bash
kubectl create secret generic jobscout-scanner-secrets \
  --namespace jobscout \
  --from-literal=NTFY_TOKEN="$NTFY_TOKEN" \
  --from-literal=APPLICATIONS_REPO_TOKEN="$APPLICATIONS_REPO_TOKEN" \
  --from-literal=APPLICATION_WRITER_TOKEN="$APPLICATION_WRITER_TOKEN" \
  --from-literal=FREELANCERMAP_USERNAME="$FREELANCERMAP_USERNAME" \
  --from-literal=FREELANCERMAP_PASSWORD="$FREELANCERMAP_PASSWORD"
```

## 3. jobscout-application-writer secrets

```bash
kubectl create secret generic jobscout-application-writer-secrets \
  --namespace jobscout \
  --from-literal=APPLICATION_WRITER_TOKEN="$APPLICATION_WRITER_TOKEN" \
  --from-literal=ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY" \
  --from-literal=CV_SERVICE_BASE_URL="http://cv-service.cv.svc.cluster.local" \
  --from-literal=CV_SERVICE_TOKEN="$CV_SERVICE_TOKEN" \
  --from-literal=APPLICATIONS_REPO_CLONE_URL="https://github.com/charemma/jobscout-applications.git" \
  --from-literal=APPLICATIONS_REPO_TOKEN="$APPLICATIONS_REPO_TOKEN" \
  --from-literal=OBSIDIAN_WRITER_BASE_URL="http://jobscout-obsidian-writer.jobscout.svc.cluster.local" \
  --from-literal=OBSIDIAN_WRITER_TOKEN="$OBSIDIAN_WRITER_TOKEN" \
  --from-literal=NTFY_BASE_URL="https://ntfy.charemma.de" \
  --from-literal=NTFY_TOPIC="jobscout" \
  --from-literal=NTFY_TOKEN="$NTFY_TOKEN"
```

## 4. jobscout-obsidian-writer secrets

```bash
kubectl create secret generic jobscout-obsidian-writer-secrets \
  --namespace jobscout \
  --from-literal=OBSIDIAN_WRITER_TOKEN="$OBSIDIAN_WRITER_TOKEN"
```

## 5. ntfy user/ACL (one-time, against the running ntfy pod)

ntfy's `auth-default-access` is `deny-all` (see
`platform/gitops/manifests/ntfy/configmap.yaml`), so a scoped user is needed
before anything can publish to the `jobscout` topic:

```bash
kubectl -n ntfy exec -it deploy/ntfy -- ntfy user add --role=none jobscout-bot
kubectl -n ntfy exec -it deploy/ntfy -- ntfy access jobscout-bot jobscout write-only
# the password set here is $NTFY_TOKEN above (ntfy uses basic-auth-style
# username/password, not a bearer token -- application code sends it as
# `Authorization: Bearer <token>` via ntfy's token-auth mode; if using
# plain user/pass instead, generate a token with:
kubectl -n ntfy exec -it deploy/ntfy -- ntfy token add jobscout-bot
```

## 6. home-node node label (infra-config change, not kubectl)

`obsidian-writer`'s `nodeSelector: {vault-access: "true"}` needs this label
present on the `home-node` node. Declared in Nix
(`infra-config/hosts/home-node/configuration.nix` /
`infra-config/services/k3s/agent.nix`), applied via `just home-node::deploy`
-- not `kubectl label`, so it survives a node rebuild. See that repo's PR
for the exact diff.

## 7. Verify

```bash
kubectl -n jobscout get cronjob,deploy
kubectl create job --from=cronjob/jobscout-scanner -n jobscout manual-test-1
kubectl -n jobscout logs -f job/manual-test-1
```
