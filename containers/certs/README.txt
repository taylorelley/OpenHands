Drop your corporate root CA certificate(s) here (as *.crt or *.pem) to have them
baked into the container trust store during an offline build. See
docs/deployment/offline.md.

This placeholder keeps the directory present (and non-empty for both git and the
Dockerfile COPY) when no custom CA is supplied. It is not a certificate and is
ignored by the install-ca-cert.sh script.
