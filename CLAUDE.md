# CLAUDE.md

Guidance for Claude Code (and humans) working in this repository.

## What this project is

OpenHands is an AI software-development agent platform. A FastAPI **app server**
(`openhands/app_server/`) serves the web UI and API, and delegates the actual
agent work to an **agent-server** "sandbox" container (the OpenHands SDK image,
`ghcr.io/openhands/agent-server:<tag>`) that it pulls and runs per conversation.
The browser talks to *both* the app server and, directly, the agent-server.

Key paths:
- `openhands/app_server/` — app server (routing, sandbox lifecycle, integrations).
- `containers/app/Dockerfile` — production image (multi-stage: frontend-builder →
  backend-builder → openhands-app).
- `containers/dev/` — development image + compose.
- `docker-compose.yml` — the default run/build entrypoint.
- `frontend/` — React UI.
- `enterprise/` — SaaS stack (**out of scope** for our changes).

Tooling: Python deps via **poetry** (`pyproject.toml` / `poetry.lock`); tests via
`uv run --no-sync python -m pytest`; lint/format via `ruff check` /
`ruff format --check`.

---

## This fork: offline / air-gapped customizations

This fork (`taylorelley/OpenHands`) adds support for running OpenHands in an
**isolated environment** with: a self-hosted GitLab container + package registry
(no Docker Hub / ghcr.io / PyPI / npm), an aggressive **SSL-inspection** proxy
(custom corporate root CA), and a self-hosted **OpenAI-compatible LLM**.

**Design principle — everything is additive and defaults to a no-op.** Every
change is gated behind an environment variable or build arg whose default
reproduces upstream behavior, so a normal online build/run is unaffected. We do
**not** hardcode any customer registry/mirror/CA into committed files.

Full operator guide: **`docs/deployment/offline.md`**. Example env file:
**`.env.offline.example`**.

### Files we own (and why)

New files (will never conflict on merge):
- `docs/deployment/offline.md` — the deployment guide.
- `.env.offline.example` — documented example env.
- `containers/app/install-ca-cert.sh` — bakes a CA from `containers/certs/` into
  the image trust store (no-op if the dir is empty).
- `containers/app/insecure-tls.sh` — build-time TLS-verify bypass for pip/poetry/
  npm, gated on `INSECURE_SKIP_TLS_VERIFY` (no-op otherwise).
- `containers/certs/README.txt` — placeholder so `containers/certs/` exists (named
  `.txt`, not `.gitkeep`/`.md`, because `.dockerignore` excludes those).
- `tests/unit/app_server/utils/test_http_session.py` — tests for the SSL helper.

Modified upstream files (these are the merge-conflict candidates):
- `openhands/app_server/utils/http_session.py` — **central SSL control point**.
  `httpx_verify_option()` returns `False` (disable), an `SSLContext` (CA bundle),
  or a default context; `configure_litellm_ssl()` wires litellm. Reads
  `OPENHANDS_DISABLE_SSL_VERIFY` / `OPENHANDS_CA_BUNDLE` / `REQUESTS_CA_BUNDLE` /
  `SSL_CERT_FILE`.
- `openhands/app_server/services/httpx_client_injector.py` — passes
  `verify=httpx_verify_option()` to the shared client.
- `openhands/app_server/integrations/azure_devops/azure_devops_service.py` — same
  `verify=` on its own client.
- `openhands/app_server/app_lifespan/oss_app_lifespan_service.py` — calls
  `configure_litellm_ssl()` at startup.
- `openhands/app_server/sandbox/sandbox_spec_service.py` — `AUTO_FORWARD_VARS`
  forwards SSL env into the agent-server sandbox.
- `openhands/app_server/utils/llm.py` — doc comment only.
- `containers/app/Dockerfile` — base-image ARGs (`NODE_IMAGE`/`PYTHON_IMAGE`), CA
  baking, pip/npm mirror ARGs, insecure-bypass hooks, poetry/pip resilience.
- `containers/dev/Dockerfile` — `BASE_IMAGE` + `APT_MIRROR` ARGs, CA baking.
- `docker-compose.yml` / `containers/dev/compose.yml` — forward build args and
  runtime env (SSL, CORS, LLM, registry) into the containers.
- `tests/unit/app_server/test_agent_server_env_override.py`,
  `tests/unit/app_server/test_httpx_client_injector.py` — updated assertions.

### Environment variables / build args we introduced

Runtime (set in shell / `.env`, forwarded by `docker-compose.yml`):
- `AGENT_SERVER_IMAGE_REPOSITORY` / `AGENT_SERVER_IMAGE_TAG` — mirrored sandbox image.
- `OPENHANDS_CA_BUNDLE` / `REQUESTS_CA_BUNDLE` / `SSL_CERT_FILE` — CA bundle path.
- `OPENHANDS_DISABLE_SSL_VERIFY` — runtime TLS-verify off (escape hatch).
- `OH_WEB_URL` / `OH_PERMITTED_CORS_ORIGINS_0` / `PERMITTED_CORS_ORIGINS` — CORS
  allow-list for remote browser access (propagated to the sandbox).
- LLM is configured in Settings as `openai/<model>` + `base_url` + `api_key`
  (the `openai/` prefix is **required**).

Build-time (`--build-arg` or compose `build.args`):
- `NODE_IMAGE` / `PYTHON_IMAGE` / `BASE_IMAGE` — base-image mirrors.
- `PIP_INDEX_URL` / `PIP_TRUSTED_HOST` / `NPM_CONFIG_REGISTRY` / `APT_MIRROR` — pkg mirrors.
- `INSECURE_SKIP_TLS_VERIFY` — build-time TLS-verify off (insecure escape hatch).
- `POETRY_INSTALLER_MAX_WORKERS` / `POETRY_REQUESTS_TIMEOUT` — flaky-proxy resilience.

> **Gotchas worth remembering** (all documented in `docs/deployment/offline.md`):
> - `INSECURE_SKIP_TLS_VERIFY` is **build-time only**; `OPENHANDS_DISABLE_SSL_VERIFY`
>   is **runtime only**. They are not interchangeable.
> - **poetry ignores `PIP_INDEX_URL`** — it always resolves from `pypi.org` unless a
>   source is declared in `pyproject.toml`. A GitLab registry that only hosts
>   *published* packages cannot be poetry's index.
> - A CA **file path** forwarded to the sandbox only works if that file exists
>   inside the (mirrored) agent-server image — bake it in.
> - Remote-browser "network errors" are almost always **CORS** (set `OH_WEB_URL`),
>   not SSL.

---

## Merging updates from upstream without undoing our changes

Upstream is the canonical OpenHands repo (org `OpenHands`; confirm the exact
repo, e.g. `OpenHands/OpenHands`). Our work lives on branch
`claude/gifted-wozniak-rs4ba2`, forked from upstream `main`.

### One-time setup

```bash
git remote add upstream https://github.com/OpenHands/OpenHands.git   # confirm URL
git fetch upstream
```

### Routine update (merge — preserves our commits as-is)

```bash
git fetch upstream
git checkout claude/gifted-wozniak-rs4ba2
git merge upstream/main
# resolve conflicts (see below), then:
git push origin claude/gifted-wozniak-rs4ba2
```

Prefer **merge** over rebase here so our published branch history stays stable
for the open PR(s). Use rebase only on a private/local branch.

### Where conflicts will happen, and how to resolve them

Our new files never conflict. Conflicts only arise in the **modified upstream
files** listed above. Because every change is additive and env/arg-gated:

1. **When in doubt, keep BOTH sides.** Our additions don't replace upstream logic;
   they add a parameter (`verify=`), a forwarded var, a build ARG, or a startup
   call. Take upstream's new code *and* re-apply our addition next to it.
2. **`containers/app/Dockerfile`** is the most likely conflict (upstream bumps base
   images / pins). Resolution pattern:
   - Keep upstream's new pin **as the ARG default**, e.g. if upstream changes
     `FROM node:26-...`, set `ARG NODE_IMAGE=node:26-...` and keep `FROM ${NODE_IMAGE}`.
   - Preserve the `COPY install-ca-cert.sh` / `insecure-tls.sh` + `RUN` lines and
     the pip/npm/poetry ENV/ARG blocks in each stage.
3. **`docker-compose.yml`** — keep upstream's service changes; re-add our
   `build.args` block and the env pass-through entries (SSL, CORS, LLM, registry).
4. **Python files** — re-apply the one-line `verify=httpx_verify_option()`, the
   `AUTO_FORWARD_VARS` block, and the `configure_litellm_ssl()` call if upstream
   refactors around them. The SSL helper logic lives entirely in
   `http_session.py`; keep that file's additions intact.
5. **`poetry.lock`** — never hand-merge. Take upstream's lock, then if needed
   `poetry lock --no-update`. We did not add runtime dependencies.

### After any merge — verify our changes survived

```bash
# our SSL helper + sandbox forwarding tests
uv run --no-sync python -m pytest \
  tests/unit/app_server/utils/test_http_session.py \
  tests/unit/app_server/test_httpx_client_injector.py \
  tests/unit/app_server/test_agent_server_env_override.py -q

ruff check openhands/app_server/utils/http_session.py
# sanity: a normal (online) build is still a no-op build
docker compose config >/dev/null     # compose file still parses
```

Checklist that nothing regressed:
- [ ] `http_session.py` still exposes `httpx_verify_option` + `configure_litellm_ssl`.
- [ ] `sandbox_spec_service.py` still has `AUTO_FORWARD_VARS`.
- [ ] `docker-compose.yml` still has the `build.args` block + SSL/CORS/LLM env.
- [ ] `containers/app/Dockerfile` still copies + runs `install-ca-cert.sh` and
      `insecure-tls.sh` in all three stages and keeps the base-image ARGs.
- [ ] `docs/deployment/offline.md` and `.env.offline.example` still present.

---

## Conventions for changes in this fork

- Keep customizations **additive and default-to-no-op**; never hardcode a specific
  registry/mirror/CA/endpoint into committed files — parametrize via env/ARG.
- Update `docs/deployment/offline.md` **and** `.env.offline.example` whenever you
  add or change an offline-related variable.
- Run `ruff check` / `ruff format --check` and the relevant `pytest` slice before
  committing.
- Do not modify `enterprise/` for offline support — it is out of scope.
