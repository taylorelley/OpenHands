#!/bin/sh
# Install custom CA certificate(s) into the system trust store.
#
# Usage: install-ca-cert.sh [SRC_DIR]
#
# Any *.crt / *.pem files in SRC_DIR (default /tmp/ca-certs) are installed into
# /usr/local/share/ca-certificates/ and merged into the combined bundle at
# /etc/ssl/certs/ca-certificates.crt via update-ca-certificates. The ca-certificates
# package is installed on demand (only when a custom cert is supplied or the bundle
# is missing) so the common, no-custom-CA build path needs no apt access.
#
# Dropping no custom certs into containers/certs/ leaves the standard public
# trust store intact, so public builds are unaffected.
set -eu

SRC_DIR="${1:-/tmp/ca-certs}"
BUNDLE=/etc/ssl/certs/ca-certificates.crt

ensure_ca_certificates() {
    if ! command -v update-ca-certificates >/dev/null 2>&1; then
        apt-get update -y
        apt-get install -y ca-certificates
    fi
    mkdir -p /usr/local/share/ca-certificates
}

# Collect candidate cert files (the README.txt placeholder is ignored).
found=0
for f in "$SRC_DIR"/*.crt "$SRC_DIR"/*.pem; do
    [ -e "$f" ] || continue
    found=1
    break
done

if [ "$found" -eq 0 ]; then
    # No custom CA. Only ensure the bundle exists (it normally already does on
    # Debian-based images), so REQUESTS_CA_BUNDLE/PIP_CERT/NODE_EXTRA_CA_CERTS
    # point at a valid file without requiring apt access.
    if [ ! -f "$BUNDLE" ]; then
        ensure_ca_certificates
        update-ca-certificates
    fi
    echo "install-ca-cert: no custom CA certificates in $SRC_DIR; using defaults."
    exit 0
fi

echo "install-ca-cert: installing custom CA certificate(s) from $SRC_DIR"
ensure_ca_certificates

for f in "$SRC_DIR"/*.crt; do
    [ -e "$f" ] || continue
    cp "$f" "/usr/local/share/ca-certificates/$(basename "$f")"
done
# PEM files must be renamed to *.crt for update-ca-certificates to pick them up.
for f in "$SRC_DIR"/*.pem; do
    [ -e "$f" ] || continue
    cp "$f" "/usr/local/share/ca-certificates/$(basename "$f" .pem).crt"
done

update-ca-certificates
echo "install-ca-cert: done."
