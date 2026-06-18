ARG OPENHANDS_BUILD_VERSION=dev
# Base images are parametrized so offline builds can point them at a private
# (e.g. GitLab) container registry mirror via --build-arg. Defaults match the
# public upstream images so standard builds are unaffected.
ARG NODE_IMAGE=node:25.9-trixie-slim
ARG PYTHON_IMAGE=python:3.13.7-slim-trixie
FROM ${NODE_IMAGE} AS frontend-builder

WORKDIR /app

# Offline build support. Drop a corporate root CA (for SSL-inspection proxies)
# as a *.crt into containers/certs/ and it is added to the system trust store;
# NODE_EXTRA_CA_CERTS then points npm at that store. NPM_CONFIG_REGISTRY lets the
# build resolve packages from a private (e.g. GitLab) mirror. Both default to a
# no-op so public builds are unaffected. INSECURE_SKIP_TLS_VERIFY=1 is an insecure
# escape hatch that disables TLS verification when no CA is available.
ARG NPM_CONFIG_REGISTRY=
ARG INSECURE_SKIP_TLS_VERIFY=
COPY containers/certs/ /tmp/ca-certs/
COPY containers/app/install-ca-cert.sh /tmp/install-ca-cert.sh
COPY containers/app/insecure-tls.sh /tmp/insecure-tls.sh
RUN /tmp/install-ca-cert.sh /tmp/ca-certs
ENV npm_config_registry=${NPM_CONFIG_REGISTRY} \
    NODE_EXTRA_CA_CERTS=/etc/ssl/certs/ca-certificates.crt

COPY frontend/package.json frontend/package-lock.json ./
RUN /tmp/insecure-tls.sh && npm ci

COPY frontend ./
RUN npm run build

FROM ${PYTHON_IMAGE} AS base
FROM base AS backend-builder

WORKDIR /app
ENV PYTHONPATH='/app'

ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

# Offline build support (see frontend stage). A *.crt in containers/certs/ is
# added to the system trust store and pip/requests are pointed at it. PIP_INDEX_URL
# (honored by both pip and poetry) selects a private PyPI mirror; PIP_TRUSTED_HOST
# skips TLS to the mirror when trust can't be established. All default to a no-op.
ARG PIP_INDEX_URL=
ARG PIP_TRUSTED_HOST=
ARG INSECURE_SKIP_TLS_VERIFY=
COPY containers/certs/ /tmp/ca-certs/
COPY containers/app/install-ca-cert.sh /tmp/install-ca-cert.sh
COPY containers/app/insecure-tls.sh /tmp/insecure-tls.sh
RUN /tmp/install-ca-cert.sh /tmp/ca-certs
ENV PIP_INDEX_URL=${PIP_INDEX_URL} \
    PIP_TRUSTED_HOST=${PIP_TRUSTED_HOST} \
    PIP_CERT=/etc/ssl/certs/ca-certificates.crt \
    REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt

# Pin Poetry version to match the version used to generate poetry.lock
ARG POETRY_VERSION=2.3.4
# insecure-tls.sh (no-op unless INSECURE_SKIP_TLS_VERIFY) writes /etc/pip.conf so
# the poetry pip install can skip TLS verification when no CA is available.
RUN /tmp/insecure-tls.sh \
    && apt-get update -y \
    && apt-get install -y curl make git build-essential jq gettext \
    && python3 -m pip install "poetry==${POETRY_VERSION}" --break-system-packages

COPY pyproject.toml poetry.lock ./
RUN touch README.md
# Re-run after poetry is installed so its own cert verification can be disabled.
RUN /tmp/insecure-tls.sh \
    && export POETRY_CACHE_DIR && poetry install --no-root && rm -rf $POETRY_CACHE_DIR

FROM base AS openhands-app

WORKDIR /app

# re-declare for this section
ARG OPENHANDS_BUILD_VERSION

ENV RUN_AS_OPENHANDS=true
# A random number--we need this to be different from the user's UID on the host machine
ENV OPENHANDS_USER_ID=42420
ENV SANDBOX_LOCAL_RUNTIME_URL=http://host.docker.internal
ENV USE_HOST_NETWORK=false
ENV WORKSPACE_BASE=/opt/workspace_base
ENV OPENHANDS_BUILD_VERSION=$OPENHANDS_BUILD_VERSION
ENV SANDBOX_USER_ID=0
ENV FILE_STORE=local
ENV FILE_STORE_PATH=/.openhands
ENV INIT_GIT_IN_EMPTY_WORKSPACE=1
RUN mkdir -p $FILE_STORE_PATH
RUN mkdir -p $WORKSPACE_BASE

# Offline build support for this stage: bake the CA into the trust store, point
# pip at it (pip uses certifi, not the system store, by default), allow a private
# mirror, and - when INSECURE_SKIP_TLS_VERIFY is set - write /etc/pip.conf so the
# pip pins below can reach PyPI without TLS verification.
ARG INSECURE_SKIP_TLS_VERIFY=
ARG PIP_INDEX_URL=
ARG PIP_TRUSTED_HOST=
COPY containers/certs/ /tmp/ca-certs/
COPY containers/app/install-ca-cert.sh /tmp/install-ca-cert.sh
COPY containers/app/insecure-tls.sh /tmp/insecure-tls.sh
RUN /tmp/install-ca-cert.sh /tmp/ca-certs && /tmp/insecure-tls.sh
ENV PIP_INDEX_URL=${PIP_INDEX_URL} \
    PIP_TRUSTED_HOST=${PIP_TRUSTED_HOST} \
    PIP_CERT=/etc/ssl/certs/ca-certificates.crt \
    REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt

RUN apt-get update -y \
    && apt-get install -y curl git ssh sudo \
    && rm -rf /var/lib/apt/lists/*

# Default is 1000, but OSX is often 501
RUN sed -i 's/^UID_MIN.*/UID_MIN 499/' /etc/login.defs
# Default is 60000, but we've seen up to 200000
RUN sed -i 's/^UID_MAX.*/UID_MAX 1000000/' /etc/login.defs

RUN groupadd --gid $OPENHANDS_USER_ID openhands
RUN useradd -l -m -u $OPENHANDS_USER_ID --gid $OPENHANDS_USER_ID -s /bin/bash openhands && \
    usermod -aG openhands openhands && \
    usermod -aG sudo openhands && \
    echo '%sudo ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers
RUN chown -R openhands:openhands /app && chmod -R 770 /app
RUN sudo chown -R openhands:openhands $WORKSPACE_BASE && sudo chmod -R 770 $WORKSPACE_BASE
USER openhands

ENV VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH='/app'

COPY --chown=openhands:openhands --chmod=770 --from=backend-builder ${VIRTUAL_ENV} ${VIRTUAL_ENV}

# Pin pip to a known-good version (reproducible builds) and fix CVE-2025-8869
# Pin both venv pip and system pip (Trivy scans both)
# - `python -m pip` uses the venv because `PATH` is prefixed with `${VIRTUAL_ENV}/bin`
# - `/usr/local/bin/python3 -m pip` uses the system interpreter regardless of `PATH`
ARG PIP_VERSION=26.0.1
RUN python -m pip install --no-cache-dir "pip==${PIP_VERSION}"

USER root
RUN /usr/local/bin/python3 -m pip install --no-cache-dir "pip==${PIP_VERSION}" --break-system-packages
USER openhands

COPY --chown=openhands:openhands --chmod=770 ./skills ./skills
COPY --chown=openhands:openhands --chmod=770 ./openhands ./openhands
COPY --chown=openhands:openhands pyproject.toml poetry.lock README.md MANIFEST.in LICENSE ./

# Add this line to set group ownership of all files/directories not already in "app" group
# openhands:openhands -> openhands:openhands
RUN find /app \! -group openhands -exec chgrp openhands {} +

COPY --chown=openhands:openhands --chmod=770 --from=frontend-builder /app/build ./frontend/build
COPY --chown=openhands:openhands --chmod=770 ./containers/app/entrypoint.sh /app/entrypoint.sh

USER root

WORKDIR /app

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["uvicorn", "openhands.server.listen:app", "--host", "0.0.0.0", "--port", "3000"]
