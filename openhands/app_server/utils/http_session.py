import os
import ssl


def _is_truthy(value: str | None) -> bool:
    return value is not None and value.strip().lower() in ('1', 'true', 'yes', 'on')


# When true, TLS verification is disabled entirely. This is an escape hatch for
# isolated environments behind an aggressive SSL-inspection proxy where the
# corporate root CA cannot be installed. Prefer OPENHANDS_CA_BUNDLE instead.
_disable_ssl_verify: bool = _is_truthy(os.getenv('OPENHANDS_DISABLE_SSL_VERIFY'))


def get_ca_bundle_path() -> str | None:
    """Return the path to a custom CA bundle, if one is configured.

    Checks ``OPENHANDS_CA_BUNDLE`` first, then the standard ``REQUESTS_CA_BUNDLE``
    and ``SSL_CERT_FILE`` variables that requests / httpx / litellm also honor.
    Returns ``None`` when no custom bundle is configured.
    """
    for var in ('OPENHANDS_CA_BUNDLE', 'REQUESTS_CA_BUNDLE', 'SSL_CERT_FILE'):
        path = os.getenv(var)
        if path:
            return path
    return None


def is_ssl_verify_disabled() -> bool:
    """Return whether TLS verification has been disabled via env."""
    return _disable_ssl_verify


def httpx_verify_option() -> ssl.SSLContext | bool:
    """Return the verify option to pass when creating an HTTPX client.

    - ``False`` when verification is disabled via ``OPENHANDS_DISABLE_SSL_VERIFY``.
    - An ``SSLContext`` loaded from the custom CA bundle when one is configured.
    - Otherwise a default context (which also auto-loads ``SSL_CERT_FILE`` /
      ``SSL_CERT_DIR`` when present).
    """
    if _disable_ssl_verify:
        return False
    ca_bundle = get_ca_bundle_path()
    if ca_bundle:
        return ssl.create_default_context(cafile=ca_bundle)
    return ssl.create_default_context()


def configure_litellm_ssl() -> None:
    """Apply the configured SSL settings to litellm at startup.

    litellm uses its own httpx clients for completion calls, so it must be
    configured separately from :func:`httpx_verify_option`. It natively honors
    the standard ``SSL_VERIFY`` / ``SSL_CERTIFICATE`` / ``REQUESTS_CA_BUNDLE``
    env vars, but we also set the module attributes explicitly so behavior is
    deterministic regardless of how litellm was imported.
    """
    import litellm

    if _disable_ssl_verify:
        litellm.ssl_verify = False
        return
    ca_bundle = get_ca_bundle_path()
    if ca_bundle:
        litellm.ssl_certificate = ca_bundle
