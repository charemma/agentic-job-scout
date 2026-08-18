# jobscout Deployment Secrets

One-time `kubectl` steps against the live cluster, same style as
`zeddl`/`cv`'s sibling docs. Not automated here -- run with the candidate present.

For local dev (docker-compose / a direct `python -m scanner.main` run), the
same `<PORTAL>_USER`/`<PORTAL>_PASS` keys go in the repo-root `.env` file
(gitignored, never committed) instead of a k8s Secret -- see
`scanner/config.py`'s `Secrets.credentials_for()`.

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
read -s APPLICATION_WRITER_TOKEN       # shared bearer secret: scanner -> application-writer
read -s CV_SERVICE_TOKEN               # shared bearer secret: application-writer -> cv-service
                                        # (must match cv-service's secret, see cv/k8s/secrets.md)
read -s OBSIDIAN_WRITER_TOKEN          # shared bearer secret: application-writer -> obsidian-writer

# Portal credentials, generic <PORTAL>_USER/<PORTAL>_PASS shape (see
# scanner/config.py's Secrets.credentials_for()). Every portal logs in now
# (driver: playwright, uniformly, decided 2026-08-14) -- anonymous access
# was only ever verified to return *a* result set, never confirmed to be
# the *complete* one a logged-in account sees. See each fetcher's docstring
# for portal-specific login-flow notes/caveats.
read -s XING_USER
read -s XING_PASS
read -s LINKEDIN_USER
read -s LINKEDIN_PASS
read -s SOLCOM_USER
read -s SOLCOM_PASS
read -s FREELANCERMAP_USER
read -s FREELANCERMAP_PASS
read -s RANDSTAD_USER
read -s RANDSTAD_PASS
read -s HAYS_USER
read -s HAYS_PASS
read -s FREELANCE_USER
read -s FREELANCE_PASS
```

## 2. jobscout-scanner secrets

```bash
kubectl create secret generic jobscout-scanner-secrets \
  --namespace jobscout \
  --from-literal=NTFY_TOKEN="$NTFY_TOKEN" \
  --from-literal=APPLICATIONS_REPO_TOKEN="$APPLICATIONS_REPO_TOKEN" \
  --from-literal=APPLICATION_WRITER_TOKEN="$APPLICATION_WRITER_TOKEN" \
  --from-literal=XING_USER="$XING_USER" \
  --from-literal=XING_PASS="$XING_PASS" \
  --from-literal=LINKEDIN_USER="$LINKEDIN_USER" \
  --from-literal=LINKEDIN_PASS="$LINKEDIN_PASS" \
  --from-literal=SOLCOM_USER="$SOLCOM_USER" \
  --from-literal=SOLCOM_PASS="$SOLCOM_PASS" \
  --from-literal=FREELANCERMAP_USER="$FREELANCERMAP_USER" \
  --from-literal=FREELANCERMAP_PASS="$FREELANCERMAP_PASS" \
  --from-literal=RANDSTAD_USER="$RANDSTAD_USER" \
  --from-literal=RANDSTAD_PASS="$RANDSTAD_PASS" \
  --from-literal=HAYS_USER="$HAYS_USER" \
  --from-literal=HAYS_PASS="$HAYS_PASS" \
  --from-literal=FREELANCE_USER="$FREELANCE_USER" \
  --from-literal=FREELANCE_PASS="$FREELANCE_PASS"
```

### 2a. jobscout-linkedin-session (persisted login, not username/password)

A fresh username/password login on every cron run was itself the bot
signal -- LinkedIn started throwing a PIN/2FA verification checkpoint on
essentially every automated login (found 2026-08-15). Fix: a persisted
Playwright session (cookies), bootstrapped once interactively and reused
by the fetcher instead of logging in fresh each time. See
`scanner/fetchers/linkedin.py`'s docstring (point 4) for the full
rationale.

```bash
just linkedin-session-bootstrap
# opens a real (non-headless) Chromium -- log in manually, clear any
# PIN/2FA/CAPTCHA challenge by hand, press Enter in the terminal once
# logged in. Prints the exact kubectl command to run next, which is:

kubectl create secret generic jobscout-linkedin-session \
  --namespace jobscout \
  --from-file=linkedin.json=./linkedin_storage_state.json

rm ./linkedin_storage_state.json  # live session credential, don't leave it lying around
```

Mounted at `/etc/jobscout-sessions/linkedin.json` in the scanner CronJob
(`k8s/scanner-cronjob.yaml`), read via `Secrets.session_state_path_for()`
in `scanner/config.py`. `optional: true` on the volume -- the CronJob runs
fine before this is ever bootstrapped, `linkedin.py` just falls back to a
fresh `LINKEDIN_USER`/`LINKEDIN_PASS` login (which will likely hit the
verification checkpoint again, that's expected until this is set up).

**This will also need periodic refresh** if the session ever expires
(LinkedIn invalidates it, force-logout, etc.) -- `linkedin.py` fails
loudly with a clear message when that happens rather than silently
falling back to a fresh login (see the module docstring for why). Re-run
`just linkedin-session-bootstrap` and `kubectl apply` the new file
(`--dry-run=client -o yaml | kubectl apply -f -` to update in place, same
as `jobscout-claude-token` below).

### 2b. jobscout-xing-session (persisted login, not username/password)

Same pattern and rationale as `jobscout-linkedin-session` above, adopted
2026-08-18 for a different reason: `xing.py`'s original `_login()` guessed
`https://www.xing.com/login`, which is a plain 404 -- Xing's real login
lives on a separate `login.xing.com` subdomain, a JS SPA with no
server-rendered form to inspect safely without logging a real account out
first. See `scanner/fetchers/xing.py`'s docstring for the full story.

```bash
just xing-session-bootstrap
# opens a real (non-headless) Chromium -- log in manually, clear any
# 2FA/CAPTCHA challenge by hand, press Enter in the terminal once logged
# in. Prints the exact kubectl command to run next, which is:

kubectl create secret generic jobscout-xing-session \
  --namespace jobscout \
  --from-file=xing.json=./xing_storage_state.json

rm ./xing_storage_state.json  # live session credential, don't leave it lying around
```

Mounted at `/etc/jobscout-sessions/xing.json` in the scanner CronJob, same
`optional: true` fallback-to-fresh-login behavior, same periodic-refresh
need if the session expires -- re-run `just xing-session-bootstrap` and
re-apply.

## 3. jobscout-application-writer secrets

**No `ANTHROPIC_API_KEY` here, deliberately.** `application_writer/anthropic_client.py`
shells out to `claude -p` (Claude Code CLI), authenticated via
`CLAUDE_CODE_OAUTH_TOKEN` instead -- billed against the Claude Code
subscription, not metered API pricing (see that module's docstring for the
full rationale and verification). Setting `ANTHROPIC_API_KEY` in this Secret
would silently switch it back to metered billing (API key takes precedence
over the OAuth token), so don't add it here even if you have one lying
around from the old implementation.

```bash
kubectl create secret generic jobscout-application-writer-secrets \
  --namespace jobscout \
  --from-literal=APPLICATION_WRITER_TOKEN="$APPLICATION_WRITER_TOKEN" \
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

### 3a. jobscout-claude-token (Claude Code long-lived OAuth token)

A **separate** Secret, injected as the `CLAUDE_CODE_OAUTH_TOKEN` env var in
the application-writer Deployment (see
`k8s/application-writer-deployment.yaml`).

**History:** originally this was `jobscout-claude-credentials`, a mounted
`credentials.json` copied from a real interactive `claude login` session on
`home-node`. That shared a single rotating refresh token between the local
CLI and the cluster pod -- whichever side refreshed first silently revoked
the other's copy, causing recurring, confusing 401s
(`OAuth access token has been revoked`). Replaced 2026-08-17 with a token
from `claude setup-token`, which is a fully independent session with no
such collision, valid for 1 year.

**How to (re-)generate**, since `setup-token` needs an interactive
browser step and there's no reason to expose that flow on a long-running
pod:

```bash
# throwaway debug pod, same image, no secret mounts
cat <<'EOF' | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: claude-login-debug
  namespace: jobscout
spec:
  restartPolicy: Never
  imagePullSecrets:
    - name: ghcr-pull-secret
  containers:
    - name: claude-login-debug
      image: ghcr.io/charemma/jobscout-application-writer:latest
      command: ["sleep", "3600"]
      stdin: true
      tty: true
EOF
kubectl wait --for=condition=Ready pod/claude-login-debug -n jobscout --timeout=60s

# run interactively yourself -- opens a URL, prompts for a code
kubectl exec -it -n jobscout claude-login-debug -- claude setup-token

# copy the printed token, then:
kubectl create secret generic jobscout-claude-token \
  --namespace jobscout \
  --from-literal=token="$CLAUDE_CODE_OAUTH_TOKEN" \
  --dry-run=client -o yaml | kubectl apply -f -

kubectl delete pod claude-login-debug -n jobscout
kubectl rollout restart deployment/jobscout-application-writer -n jobscout
```

Valid for 1 year from creation -- next refresh due around 2027-08-17.
Application-writer's Claude usage still draws from the same subscription
quota as the candidate's interactive sessions (unchanged from before), worth
keeping in mind if usage limits ever get tight.

## 4. jobscout-obsidian-writer secrets

```bash
kubectl create secret generic jobscout-obsidian-writer-secrets \
  --namespace jobscout \
  --from-literal=OBSIDIAN_WRITER_TOKEN="$OBSIDIAN_WRITER_TOKEN"
```

## 5. ntfy user/ACL -- done 2026-08-14, kept here for reference

ntfy's `auth-default-access` is `deny-all` (confirmed via
`ntfy user list`: the anonymous role has no access to any topic), so a
scoped user was needed before anything could publish to (or read) the
`jobscout` topic. `--role=none` doesn't exist as a flag (only
`admin`/`user`); the write-only/read-only scoping happens via a separate
`ntfy access` grant, not the role itself:

```bash
# Publish side (scanner -> topic), write-only
kubectl -n ntfy exec deploy/ntfy -- env NTFY_PASSWORD="$NTFY_TOKEN" ntfy user add --role=user jobscout-bot
kubectl -n ntfy exec deploy/ntfy -- ntfy access jobscout-bot jobscout write-only
kubectl -n ntfy exec deploy/ntfy -- ntfy token add jobscout-bot
# use the printed tk_... token as $NTFY_TOKEN in the scanner/application-writer
# secrets above -- ntfy accepts it as `Authorization: Bearer <token>`

# Read side (the candidate's phone), read-only, separate from any other ntfy topic's
# user so this doesn't touch existing viewer/admin accounts
kubectl -n ntfy exec deploy/ntfy -- env NTFY_PASSWORD="<pick a password>" ntfy user add --role=user jobscout-viewer
kubectl -n ntfy exec deploy/ntfy -- ntfy access jobscout-viewer jobscout read-only
# in the ntfy phone app: add server ntfy.charemma.de with these credentials
# (stored per-server, not per-topic -- entered once when adding the server),
# then subscribe to topic "jobscout"
```

## 6. home-node node labels (infra-config change, not kubectl)

Two declarative labels needed on the `home-node` node, both set the same way
(Nix, `infra-config/hosts/home-node/configuration.nix` /
`infra-config/services/k3s/agent.nix`, applied via `just home-node::deploy` --
not `kubectl label`, so they survive a node rebuild):

- `vault-access: "true"` -- `obsidian-writer`'s `nodeSelector` (Obsidian
  vault is only synced to this node).
- `home-network: "true"` -- `jobscout-scanner`'s `nodeSelector`. Every
  portal now logs in via Playwright (see `scanner/fetchers/linkedin.py`'s
  docstring for the residential-vs-datacenter-IP rationale, which applies
  uniformly now, not just to xing/linkedin/solcom).

See `infra-config`'s PR for the exact diff.

## 7. Verify

```bash
kubectl -n jobscout get cronjob,deploy
kubectl create job --from=cronjob/jobscout-scanner -n jobscout manual-test-1
kubectl -n jobscout logs -f job/manual-test-1
```
