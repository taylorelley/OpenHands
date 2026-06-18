"""Tests for the central SSL/CA configuration helper used for offline /
SSL-inspection environments."""

import importlib
import ssl
from unittest.mock import patch

import pytest

_ENV_KEYS = (
    'OPENHANDS_DISABLE_SSL_VERIFY',
    'OPENHANDS_CA_BUNDLE',
    'REQUESTS_CA_BUNDLE',
    'SSL_CERT_FILE',
)


@pytest.fixture(autouse=True)
def _restore_module(monkeypatch):
    """Reload the module to a clean (no-env) state after each test so the
    import-time globals don't leak a CA path / disable flag into other tests."""
    yield
    import openhands.app_server.utils.http_session as http_session

    for key in _ENV_KEYS:
        monkeypatch.delenv(key, raising=False)
    importlib.reload(http_session)


def _reload_with_env(monkeypatch, **env):
    """Reload http_session with a controlled environment.

    The disable flag is captured at import time, so the module must be reloaded
    after patching the environment.
    """
    import openhands.app_server.utils.http_session as http_session

    for key in _ENV_KEYS:
        monkeypatch.delenv(key, raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    return importlib.reload(http_session)


def test_default_returns_default_context(monkeypatch):
    http_session = _reload_with_env(monkeypatch)
    result = http_session.httpx_verify_option()
    assert isinstance(result, ssl.SSLContext)
    assert http_session.is_ssl_verify_disabled() is False
    assert http_session.get_ca_bundle_path() is None


@pytest.mark.parametrize('value', ['1', 'true', 'TRUE', 'yes', 'on'])
def test_disable_flag_truthy(monkeypatch, value):
    http_session = _reload_with_env(monkeypatch, OPENHANDS_DISABLE_SSL_VERIFY=value)
    assert http_session.is_ssl_verify_disabled() is True
    assert http_session.httpx_verify_option() is False


@pytest.mark.parametrize('value', ['0', 'false', 'no', ''])
def test_disable_flag_falsy(monkeypatch, value):
    http_session = _reload_with_env(monkeypatch, OPENHANDS_DISABLE_SSL_VERIFY=value)
    assert http_session.is_ssl_verify_disabled() is False
    assert isinstance(http_session.httpx_verify_option(), ssl.SSLContext)


def test_ca_bundle_builds_context_from_path(monkeypatch):
    http_session = _reload_with_env(
        monkeypatch, OPENHANDS_CA_BUNDLE='/etc/ssl/corp-ca.pem'
    )
    assert http_session.get_ca_bundle_path() == '/etc/ssl/corp-ca.pem'
    with patch('ssl.create_default_context') as mock_ctx:
        http_session.httpx_verify_option()
        mock_ctx.assert_called_once_with(cafile='/etc/ssl/corp-ca.pem')


def test_ca_bundle_env_precedence(monkeypatch):
    # OPENHANDS_CA_BUNDLE wins over the standard vars.
    http_session = _reload_with_env(
        monkeypatch,
        OPENHANDS_CA_BUNDLE='/a/openhands.pem',
        REQUESTS_CA_BUNDLE='/b/requests.pem',
        SSL_CERT_FILE='/c/ssl.pem',
    )
    assert http_session.get_ca_bundle_path() == '/a/openhands.pem'

    # Falls back to REQUESTS_CA_BUNDLE, then SSL_CERT_FILE.
    http_session = _reload_with_env(
        monkeypatch,
        REQUESTS_CA_BUNDLE='/b/requests.pem',
        SSL_CERT_FILE='/c/ssl.pem',
    )
    assert http_session.get_ca_bundle_path() == '/b/requests.pem'

    http_session = _reload_with_env(monkeypatch, SSL_CERT_FILE='/c/ssl.pem')
    assert http_session.get_ca_bundle_path() == '/c/ssl.pem'


def test_disable_takes_precedence_over_ca(monkeypatch):
    http_session = _reload_with_env(
        monkeypatch,
        OPENHANDS_DISABLE_SSL_VERIFY='1',
        OPENHANDS_CA_BUNDLE='/etc/ssl/corp-ca.pem',
    )
    assert http_session.httpx_verify_option() is False


def test_configure_litellm_ssl_disable(monkeypatch):
    http_session = _reload_with_env(monkeypatch, OPENHANDS_DISABLE_SSL_VERIFY='1')
    fake_litellm = type('L', (), {'ssl_verify': True, 'ssl_certificate': None})()
    with patch.dict('sys.modules', {'litellm': fake_litellm}):
        http_session.configure_litellm_ssl()
    assert fake_litellm.ssl_verify is False


def test_configure_litellm_ssl_with_ca(monkeypatch):
    http_session = _reload_with_env(
        monkeypatch, OPENHANDS_CA_BUNDLE='/etc/ssl/corp-ca.pem'
    )
    fake_litellm = type('L', (), {'ssl_verify': True, 'ssl_certificate': None})()
    with patch.dict('sys.modules', {'litellm': fake_litellm}):
        http_session.configure_litellm_ssl()
    assert fake_litellm.ssl_certificate == '/etc/ssl/corp-ca.pem'
