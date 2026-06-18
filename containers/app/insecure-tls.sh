#!/bin/sh
# Disable TLS certificate verification for the build's package managers.
#
# This is an INSECURE escape hatch for building behind an SSL-inspection proxy
# when the corporate root CA is not available to drop into containers/certs/.
# It is a no-op unless INSECURE_SKIP_TLS_VERIFY is truthy. Prefer supplying the
# CA (see docs/deployment/offline.md) over using this.
#
# Covers the three managers the build uses, each of which needs a different knob:
#   * pip    -> /etc/pip.conf trusted-host (pip ignores REQUESTS_CA_BUNDLE for this)
#   * poetry -> `poetry config certificates.pypi.cert false` (requests/httpx based)
#   * npm    -> `npm config set strict-ssl false`
set -eu

case "${INSECURE_SKIP_TLS_VERIFY:-}" in
    1 | true | TRUE | yes | on) ;;
    *) exit 0 ;;
esac

echo "insecure-tls: WARNING - disabling TLS verification for build package managers"

# Build the pip trusted-host list: the public PyPI hosts plus the host of a
# custom PIP_INDEX_URL mirror, if one is configured.
hosts="pypi.org files.pythonhosted.org"
if [ -n "${PIP_INDEX_URL:-}" ]; then
    mirror_host=$(printf '%s' "$PIP_INDEX_URL" |
        sed -E 's#^[a-zA-Z]+://([^/@]*@)?([^/:]+).*#\2#')
    if [ -n "$mirror_host" ] && [ "$mirror_host" != "$PIP_INDEX_URL" ]; then
        hosts="$hosts $mirror_host"
    fi
fi

# pip: global config is picked up by every later pip invocation in this stage.
printf '[global]\ntrusted-host = %s\n' "$hosts" >/etc/pip.conf
echo "insecure-tls: pip trusted-host = $hosts"

# poetry: only configurable once poetry is installed; skipped otherwise.
if command -v poetry >/dev/null 2>&1; then
    poetry config certificates.pypi.cert false || true
    echo "insecure-tls: poetry cert verification disabled for PyPI"
fi

# npm: only present in the frontend build stage.
if command -v npm >/dev/null 2>&1; then
    npm config set -g strict-ssl false || true
    echo "insecure-tls: npm strict-ssl disabled"
fi
