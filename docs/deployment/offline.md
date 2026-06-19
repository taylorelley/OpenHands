# Running OpenHands in an isolated / offline environment

This guide explains how to run OpenHands inside an air-gapped environment that
has:

1. **A self-hosted GitLab** providing the container registry and pip/npm/apt
   package mirrors — no access to Docker Hub, ghcr.io, PyPI, npmjs, nodesource,
   etc.
2. **Aggressive SSL inspection** — a MITM proxy presenting a custom corporate
   root CA that breaks ordinary TLS verification on outbound HTTPS.
3. **A self-hosted LLM** behind an OpenAI-compatible endpoint.

All of the changes below are driven by environment variables and build args with
upstream defaults, so a normal (online) build/run is unaffected.

A ready-to-edit `.env.offline.example` lives at the repository root.

---

## 1. Container & package mirrors (GitLab)

### Runtime sandbox image

The agent runs inside an **agent-server** container that OpenHands pulls at
runtime. Mirror it into your registry and point OpenHands at it:

```bash
# one-time mirror
docker pull ghcr.io/openhands/agent-server:1.29.0-python
docker tag  ghcr.io/openhands/agent-server:1.29.0-python \
            registry.gitlab.local/openhands/agent-server:1.29.0-python
docker push registry.gitlab.local/openhands/agent-server:1.29.0-python

# runtime config (env)
export AGENT_SERVER_IMAGE_REPOSITORY=registry.gitlab.local/openhands/agent-server
export AGENT_SERVER_IMAGE_TAG=1.29.0-python
```

These are read by `get_agent_server_image()` in
`openhands/app_server/sandbox/sandbox_spec_service.py` and are already wired into
`docker-compose.yml` and `containers/dev/compose.yml`.

### Build-time base images & package mirrors

`containers/app/Dockerfile` (production) and `containers/dev/Dockerfile`
(development) accept build args:

| Build arg | Dockerfile | Purpose |
|-----------|-----------|---------|
| `NODE_IMAGE` | app | Node base image (default `node:25.9-trixie-slim`) |
| `PYTHON_IMAGE` | app | Python base image (default `python:3.13.7-slim-trixie`) |
| `BASE_IMAGE` | dev | Ubuntu base image (default `ubuntu:26.04`) |
| `PIP_INDEX_URL` | app | Private PyPI mirror for **pip** (see poetry note below) |
| `PIP_TRUSTED_HOST` | app | Skip TLS to the pip mirror if needed |
| `NPM_CONFIG_REGISTRY` | app | Private npm registry |
| `INSECURE_SKIP_TLS_VERIFY` | app | Disable build-time TLS verification (insecure) |
| `POETRY_INSTALLER_MAX_WORKERS` | app | Lower poetry download parallelism (e.g. `2`) |
| `POETRY_REQUESTS_TIMEOUT` | app | Raise poetry per-request timeout (e.g. `60`) |
| `APT_MIRROR` | dev | Private Ubuntu apt mirror |

> **poetry does not read `PIP_INDEX_URL`.** `poetry install` always resolves from
> `pypi.org` unless a source is declared in `pyproject.toml`. A GitLab PyPI
> *registry* that only hosts your **published** packages is **not** a pull-through
> proxy and cannot serve the full dependency tree, so it can't be used as the
> poetry index. To pull everything from a private index you need a real PyPI
> pull-through proxy (Nexus/Artifactory/devpi/GitLab dependency proxy) declared as
> a primary `[[tool.poetry.source]]`, with `poetry.lock` regenerated against it.

Example offline build:

```bash
docker build -f containers/app/Dockerfile \
  --build-arg NODE_IMAGE=registry.gitlab.local/mirror/node:25.9-trixie-slim \
  --build-arg PYTHON_IMAGE=registry.gitlab.local/mirror/python:3.13.7-slim-trixie \
  --build-arg PIP_INDEX_URL=https://gitlab.local/api/v4/projects/1/packages/pypi/simple \
  --build-arg PIP_TRUSTED_HOST=gitlab.local \
  --build-arg NPM_CONFIG_REGISTRY=https://gitlab.local/api/v4/projects/1/packages/npm/ \
  -t openhands:offline .
```

### Building through `docker compose`

`docker-compose.yml` forwards `NODE_IMAGE`, `PYTHON_IMAGE`, `PIP_INDEX_URL`,
`PIP_TRUSTED_HOST`, `NPM_CONFIG_REGISTRY`, `INSECURE_SKIP_TLS_VERIFY`,
`POETRY_INSTALLER_MAX_WORKERS`, and `POETRY_REQUESTS_TIMEOUT` from the environment
into the image build, so you can drive the whole offline build with env vars
(e.g. from `.env.offline.example`) and run:

```bash
docker compose up -d --build
```

### `poetry install` fails partway through a flaky proxy

Symptom: the build gets past the TLS/cert stage, `poetry install` starts
downloading, then fails with `connection error ... the server is not responding`
or `the hostname cannot be resolved`. This is a throughput/stability problem, not
a certificate problem — many parallel TLS connections to `files.pythonhosted.org`
through an SSL-inspection proxy can overwhelm or get throttled by the proxy.

Fix: reduce poetry's parallelism and raise its timeout, then rebuild:

```bash
export POETRY_INSTALLER_MAX_WORKERS=2   # fewer concurrent downloads
export POETRY_REQUESTS_TIMEOUT=60       # seconds
docker compose up -d --build
```

(The build already sets `PIP_DEFAULT_TIMEOUT=60` / `PIP_RETRIES=5` for pip.) If it
still fails intermittently, lower `POETRY_INSTALLER_MAX_WORKERS` to `1` and
re-run — the build resumes from cached layers, so only the `poetry install` step
repeats.

> The dev image (`containers/dev/Dockerfile`) additionally pulls third-party apt
> repos (Docker, GitHub CLI, deadsnakes, NodeSource, Poetry). For a fully
> air-gapped dev build, serve those components from your GitLab apt mirror and
> set `APT_MIRROR`, or pre-bake them. The production `containers/app/Dockerfile`
> does **not** depend on those repos.

---

## 2. SSL inspection (custom root CA)

### Preferred: install the corporate CA, keep verification ON

**Build time** — drop your root CA as a `*.crt` (or `*.pem`) file into
`containers/certs/`. The Dockerfiles run `containers/app/install-ca-cert.sh`,
which installs it into the system trust store
(`/etc/ssl/certs/ca-certificates.crt`) and points pip / requests / npm at that
bundle. No build arg is required; an empty `containers/certs/` leaves public
trust intact.

**Runtime** — the central helper
`openhands/app_server/utils/http_session.py::httpx_verify_option()` reads the CA
from the first of `OPENHANDS_CA_BUNDLE`, `REQUESTS_CA_BUNDLE`, or `SSL_CERT_FILE`
that is set, and applies it to every outbound HTTPX client (git providers, the
shared per-request client, Azure DevOps, etc.). litellm is configured separately
at startup by `configure_litellm_ssl()`.

Because the app image already bakes the CA into
`/etc/ssl/certs/ca-certificates.crt`, the default runtime config works with no
extra env. To use a different bundle path, set `OPENHANDS_CA_BUNDLE` (and/or the
standard `REQUESTS_CA_BUNDLE` / `SSL_CERT_FILE`).

### Sandbox propagation

The agent's LLM calls run **inside the agent-server sandbox container**, not in
the app server. The SSL vars are auto-forwarded there via
`AUTO_FORWARD_VARS` in `sandbox_spec_service.py`
(`REQUESTS_CA_BUNDLE`, `SSL_CERT_FILE`, `OPENHANDS_CA_BUNDLE`,
`OPENHANDS_DISABLE_SSL_VERIFY`, `SSL_VERIFY`, `SSL_CERTIFICATE`).

> A CA **file path** is only meaningful inside the sandbox if that file exists
> there. Bake the CA into your mirrored agent-server image at a known path (e.g.
> `/etc/ssl/certs/ca-certificates.crt` after `update-ca-certificates`) and make
> sure the forwarded path matches. You can inject extra sandbox env via
> `OH_AGENT_SERVER_ENV` (JSON).

### Escape hatch: disable verification entirely

There are **two separate** verification phases — runtime and build — with
**different** flags. They do not substitute for each other.

**Runtime** (the app process) — set:

```bash
export OPENHANDS_DISABLE_SSL_VERIFY=true
```

This makes `httpx_verify_option()` return `False` and sets `litellm.ssl_verify =
False`. The flag is auto-forwarded into the sandbox too.

**Build** (`docker build` / `docker compose build`) — `OPENHANDS_DISABLE_SSL_VERIFY`
has **no effect here**; the image build runs `pip`, `poetry`, and `npm`, which
verify TLS independently. If you cannot drop the CA into `containers/certs/`,
build with:

```bash
export INSECURE_SKIP_TLS_VERIFY=1
docker compose up -d --build
```

`containers/app/insecure-tls.sh` then disables TLS verification for each build
package manager (pip via `/etc/pip.conf` trusted-host, poetry via
`poetry config certificates.pypi.cert false`, npm via `strict-ssl false`). If you
also set `PIP_INDEX_URL`, its host is added to pip's trusted-host list.

Both flags are **insecure** (no certificate validation) and are a last resort —
prefer installing the CA.

---

## 3. Self-hosted LLM (OpenAI-compatible)

Configure the LLM in Settings (or the settings API) with an explicit endpoint —
the `openhands/*` provider and the public managed proxy are not reachable
offline:

```json
{
  "model": "openai/your-served-model",
  "base_url": "https://llm.internal.local/v1",
  "api_key": "your-key"
}
```

The `openai/` prefix routes litellm to the OpenAI-compatible path and honors
`base_url`; `resolve_llm_base_url` passes an explicit `base_url` through
unchanged (`openhands/app_server/utils/llm.py`). `LLM_*` environment variables
are auto-forwarded into the sandbox. If you front the model with a LiteLLM proxy,
override the default proxy URL with `LITE_LLM_API_URL`.

---

## 4. Verification checklist

1. **Offline build** with egress blocked succeeds, pulling only from GitLab.
2. **SSL helper:** `httpx_verify_option()` returns `False` when
   `OPENHANDS_DISABLE_SSL_VERIFY=1`, an `SSLContext` when a CA bundle is set, and
   a default context otherwise (see `tests/.../test_http_session.py`).
3. **MITM egress:** with the CA installed, a git provider call succeeds with no
   `CERTIFICATE_VERIFY_FAILED`; toggling the escape hatch also works.
4. **LLM round-trip:** the agent completes a turn against the self-hosted
   endpoint.
5. **Sandbox propagation:** `docker exec` into the agent-server container and
   confirm the SSL/LLM vars are present and the CA file exists at the referenced
   path.
6. **Registry pull:** with `AGENT_SERVER_IMAGE_REPOSITORY`/`_TAG` set, the
   sandbox image is pulled from GitLab.
