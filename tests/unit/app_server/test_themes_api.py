"""Integration tests for the theme endpoints in the settings router.

Covers every endpoint under ``/api/v1/settings/themes``:
- list / get / save / delete / activate / rename — happy paths and 404s/409s.
- 422 on malformed theme payload (Pydantic validates the request body).
- ``theme_profiles`` round-trips through ``GET /api/v1/settings``.
"""

import os
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import Request
from fastapi.testclient import TestClient
from pydantic import SecretStr

from openhands.app_server.app import app
from openhands.app_server.file_store import get_file_store
from openhands.app_server.integrations.provider import ProviderToken, ProviderType
from openhands.app_server.integrations.service_types import UserGitInfo
from openhands.app_server.secrets.secrets_models import Secrets
from openhands.app_server.secrets.secrets_store import SecretsStore
from openhands.app_server.settings.file_settings_store import FileSettingsStore
from openhands.app_server.settings.settings_models import Settings
from openhands.app_server.settings.settings_router import _user_theme_locks
from openhands.app_server.settings.settings_store import SettingsStore
from openhands.app_server.settings.theme_profiles import MAX_THEMES_PER_USER, Theme
from openhands.app_server.user_auth.user_auth import UserAuth


@pytest.fixture(autouse=True)
def _reset_theme_locks():
    """Locks bind to the event loop that first awaited them; FastAPI TestClient
    spins a fresh loop per test, so any stale Lock carried over from a previous
    test would be attached to a dead loop. Clearing between tests fixes it."""
    _user_theme_locks.clear()
    yield
    _user_theme_locks.clear()


class _MockUserAuth(UserAuth):
    def __init__(self, settings_store: SettingsStore) -> None:
        self._settings = None
        self._settings_store = settings_store

    async def get_user_id(self) -> str | None:
        return 'test-user'

    async def get_user_email(self) -> str | None:
        return 'test-email@example.com'

    async def get_access_token(self) -> SecretStr | None:
        return SecretStr('test-token')

    async def get_provider_tokens(
        self,
    ) -> dict[ProviderType, ProviderToken] | None:
        return None

    async def get_user_settings_store(self) -> SettingsStore | None:
        return self._settings_store

    async def get_secrets_store(self) -> SecretsStore | None:
        return None

    async def get_secrets(self) -> Secrets | None:
        return None

    async def get_mcp_api_key(self) -> str | None:
        return None

    async def get_user_git_info(self) -> UserGitInfo | None:
        return None

    @classmethod
    async def get_instance(cls, request: Request) -> UserAuth:
        raise NotImplementedError  # patched per-test

    @classmethod
    async def get_for_user(cls, user_id: str) -> UserAuth:
        raise NotImplementedError  # patched per-test


@pytest.fixture
def settings_store(tmp_path: Path) -> FileSettingsStore:
    return FileSettingsStore(get_file_store('local', str(tmp_path)))


@pytest.fixture
def test_client(settings_store):
    """TestClient wired to an in-memory settings store the test can seed directly."""
    auth = _MockUserAuth(settings_store)
    with (
        patch.dict(
            os.environ,
            {'SESSION_API_KEY': '', 'ALLOW_SHORT_CONTEXT_WINDOWS': 'true'},
            clear=False,
        ),
        patch('openhands.app_server.utils.dependencies._SESSION_API_KEY', None),
        patch(
            'openhands.app_server.user_auth.user_auth.UserAuth.get_instance',
            return_value=auth,
        ),
        patch(
            'openhands.app_server.settings.file_settings_store.FileSettingsStore.get_instance',
            AsyncMock(return_value=settings_store),
        ),
    ):
        yield TestClient(app)


def _base_settings() -> Settings:
    return Settings()


async def _seed(store: FileSettingsStore, settings: Settings) -> None:
    await store.store(settings)


@contextmanager
def _client_for_user(user_id: str, store: FileSettingsStore):
    """Yield a TestClient scoped to a specific user_id + settings store.

    Used by multi-user isolation tests; the module-level ``test_client``
    fixture is pinned to a single mock user.
    """

    class _Scoped(_MockUserAuth):
        async def get_user_id(self) -> str | None:  # type: ignore[override]
            return user_id

    auth = _Scoped(store)
    with (
        patch.dict(
            os.environ,
            {'SESSION_API_KEY': '', 'ALLOW_SHORT_CONTEXT_WINDOWS': 'true'},
            clear=False,
        ),
        patch('openhands.app_server.utils.dependencies._SESSION_API_KEY', None),
        patch(
            'openhands.app_server.user_auth.user_auth.UserAuth.get_instance',
            return_value=auth,
        ),
        patch(
            'openhands.app_server.settings.file_settings_store.FileSettingsStore.get_instance',
            AsyncMock(return_value=store),
        ),
    ):
        yield TestClient(app)


# ── GET /themes ───────────────────────────────────────────────────


def test_list_themes_returns_empty_when_no_settings(test_client):
    response = test_client.get('/api/v1/settings/themes')

    assert response.status_code == 200
    assert response.json() == {'themes': [], 'active_theme': None}


@pytest.mark.asyncio
async def test_list_themes_returns_saved_themes(test_client, settings_store):
    settings = _base_settings()
    settings.theme_profiles.save('dark', Theme(primary='#fff'))
    settings.theme_profiles.save('light', Theme(primary='#000'))
    settings.theme_profiles.active = 'light'
    await _seed(settings_store, settings)

    response = test_client.get('/api/v1/settings/themes')

    assert response.status_code == 200
    body = response.json()
    assert body['active_theme'] == 'light'
    names = {t['name'] for t in body['themes']}
    assert names == {'dark', 'light'}


# ── GET /themes/{name} ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_theme_returns_full_config(test_client, settings_store):
    settings = _base_settings()
    settings.theme_profiles.save(
        'p', Theme(primary='#fff', app_name='Acme', logo_url='https://x.test/l.png')
    )
    await _seed(settings_store, settings)

    response = test_client.get('/api/v1/settings/themes/p')

    assert response.status_code == 200
    body = response.json()
    assert body['name'] == 'p'
    assert body['config']['primary'] == '#fff'
    assert body['config']['app_name'] == 'Acme'
    assert body['config']['logo_url'] == 'https://x.test/l.png'


def test_get_theme_returns_404_when_unknown(test_client):
    response = test_client.get('/api/v1/settings/themes/nope')

    assert response.status_code == 404
    assert "'nope'" in response.json()['detail']


# ── POST /themes/{name} ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_save_theme_with_explicit_config_persists(test_client, settings_store):
    await _seed(settings_store, _base_settings())

    response = test_client.post(
        '/api/v1/settings/themes/my-theme',
        json={'theme': {'primary': '#abcdef', 'app_name': 'Acme'}},
    )

    assert response.status_code == 201
    assert response.json()['name'] == 'my-theme'

    stored = await settings_store.load()
    assert stored.theme_profiles.has('my-theme')
    saved = stored.theme_profiles.get('my-theme')
    assert saved.primary == '#abcdef'
    assert saved.app_name == 'Acme'


@pytest.mark.asyncio
async def test_save_theme_with_no_body_saves_blank_theme(test_client, settings_store):
    await _seed(settings_store, _base_settings())

    response = test_client.post('/api/v1/settings/themes/blank')

    assert response.status_code == 201
    stored = await settings_store.load()
    saved = stored.theme_profiles.get('blank')
    assert saved is not None
    assert saved.primary is None


@pytest.mark.asyncio
async def test_save_theme_overwrites_existing(test_client, settings_store):
    settings = _base_settings()
    settings.theme_profiles.save('p', Theme(primary='#fff'))
    await _seed(settings_store, settings)

    response = test_client.post(
        '/api/v1/settings/themes/p',
        json={'theme': {'primary': '#000'}},
    )

    assert response.status_code == 201
    stored = await settings_store.load()
    assert stored.theme_profiles.get('p').primary == '#000'


@pytest.mark.asyncio
async def test_save_theme_rejects_invalid_color_with_422(test_client, settings_store):
    await _seed(settings_store, _base_settings())

    response = test_client.post(
        '/api/v1/settings/themes/bad',
        json={'theme': {'primary': 'url(javascript:alert(1))'}},
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_save_theme_rejects_unknown_field(test_client, settings_store):
    """Theme forbids extras → typo returns 422 instead of a silent 201."""
    await _seed(settings_store, _base_settings())

    response = test_client.post(
        '/api/v1/settings/themes/typo',
        json={'theme': {'primary': '#fff', 'colour': '#fff'}},
    )

    assert response.status_code == 422


# ── DELETE /themes/{name} ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_delete_theme_removes_it(test_client, settings_store):
    settings = _base_settings()
    settings.theme_profiles.save('p', Theme(primary='#fff'))
    await _seed(settings_store, settings)

    response = test_client.delete('/api/v1/settings/themes/p')

    assert response.status_code == 200
    stored = await settings_store.load()
    assert not stored.theme_profiles.has('p')


@pytest.mark.asyncio
async def test_delete_theme_is_idempotent(test_client, settings_store):
    await _seed(settings_store, _base_settings())

    response = test_client.delete('/api/v1/settings/themes/never-existed')

    assert response.status_code == 200
    assert response.json()['name'] == 'never-existed'


# ── POST /themes/{name}/activate ──────────────────────────────────


@pytest.mark.asyncio
async def test_activate_theme_sets_active(test_client, settings_store):
    settings = _base_settings()
    settings.theme_profiles.save('dark', Theme(primary='#fff'))
    await _seed(settings_store, settings)

    response = test_client.post('/api/v1/settings/themes/dark/activate')

    assert response.status_code == 200
    body = response.json()
    assert body['name'] == 'dark'

    stored = await settings_store.load()
    assert stored.theme_profiles.active == 'dark'


def test_activate_theme_returns_404_when_unknown(test_client):
    response = test_client.post('/api/v1/settings/themes/ghost/activate')

    assert response.status_code == 404
    assert "'ghost'" in response.json()['detail']


# ── POST /themes/{name}/rename ────────────────────────────────────


@pytest.mark.asyncio
async def test_rename_theme_renames_and_preserves_config(test_client, settings_store):
    settings = _base_settings()
    settings.theme_profiles.save('old', Theme(primary='#fff', app_name='Acme'))
    await _seed(settings_store, settings)

    response = test_client.post(
        '/api/v1/settings/themes/old/rename',
        json={'new_name': 'new'},
    )

    assert response.status_code == 200
    body = response.json()
    assert body['name'] == 'new'

    stored = await settings_store.load()
    assert stored.theme_profiles.get('old') is None
    renamed = stored.theme_profiles.get('new')
    assert renamed is not None
    assert renamed.app_name == 'Acme'


@pytest.mark.asyncio
async def test_rename_theme_preserves_active_flag(test_client, settings_store):
    settings = _base_settings()
    settings.theme_profiles.save('p', Theme(primary='#fff'))
    settings.theme_profiles.active = 'p'
    await _seed(settings_store, settings)

    response = test_client.post(
        '/api/v1/settings/themes/p/rename',
        json={'new_name': 'q'},
    )
    assert response.status_code == 200

    stored = await settings_store.load()
    assert stored.theme_profiles.active == 'q'


@pytest.mark.asyncio
async def test_rename_theme_returns_404_when_unknown(test_client, settings_store):
    await _seed(settings_store, _base_settings())

    response = test_client.post(
        '/api/v1/settings/themes/ghost/rename',
        json={'new_name': 'new'},
    )

    assert response.status_code == 404
    assert "'ghost'" in response.json()['detail']


@pytest.mark.asyncio
async def test_rename_theme_returns_409_when_target_exists(test_client, settings_store):
    settings = _base_settings()
    settings.theme_profiles.save('a', Theme(primary='#fff'))
    settings.theme_profiles.save('b', Theme(primary='#000'))
    await _seed(settings_store, settings)

    response = test_client.post(
        '/api/v1/settings/themes/a/rename',
        json={'new_name': 'b'},
    )

    assert response.status_code == 409
    assert "'b'" in response.json()['detail']

    stored = await settings_store.load()
    assert stored.theme_profiles.has('a')
    assert stored.theme_profiles.has('b')


@pytest.mark.asyncio
async def test_rename_theme_rejects_invalid_new_name(test_client, settings_store):
    settings = _base_settings()
    settings.theme_profiles.save('p', Theme(primary='#fff'))
    await _seed(settings_store, settings)

    response = test_client.post(
        '/api/v1/settings/themes/p/rename',
        json={'new_name': 'has space'},
    )

    assert response.status_code == 422


# ── Name validation ────────────────────────────────────────────────


@pytest.mark.parametrize(
    'bad_name',
    [
        'a' * 65,  # too long
        'with space',  # disallowed char
        'weird$chars',  # disallowed char
    ],
)
def test_save_theme_rejects_invalid_name(test_client, bad_name):
    response = test_client.post(
        f'/api/v1/settings/themes/{bad_name}',
        json={'theme': {'primary': '#fff'}},
    )
    assert response.status_code in (404, 405, 422)


# ── Theme count cap ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_save_theme_returns_409_past_limit(test_client, settings_store):
    settings = _base_settings()
    for i in range(MAX_THEMES_PER_USER):
        settings.theme_profiles.save(f'p{i}', Theme(primary='#fff'))
    await _seed(settings_store, settings)

    response = test_client.post(
        '/api/v1/settings/themes/one-too-many',
        json={'theme': {'primary': '#fff'}},
    )

    assert response.status_code == 409
    assert 'limit' in response.json()['detail'].lower()


@pytest.mark.asyncio
async def test_save_theme_at_limit_can_still_overwrite(test_client, settings_store):
    settings = _base_settings()
    for i in range(MAX_THEMES_PER_USER):
        settings.theme_profiles.save(f'p{i}', Theme(primary='#fff'))
    await _seed(settings_store, settings)

    response = test_client.post(
        '/api/v1/settings/themes/p0',
        json={'theme': {'primary': '#000'}},
    )

    assert response.status_code == 201
    stored = await settings_store.load()
    assert stored.theme_profiles.get('p0').primary == '#000'


@pytest.mark.asyncio
async def test_cap_frees_after_delete(test_client, settings_store):
    settings = _base_settings()
    for i in range(MAX_THEMES_PER_USER):
        settings.theme_profiles.save(f'p{i}', Theme(primary='#fff'))
    await _seed(settings_store, settings)

    assert (
        test_client.post(
            '/api/v1/settings/themes/over',
            json={'theme': {'primary': '#fff'}},
        ).status_code
        == 409
    )

    test_client.delete('/api/v1/settings/themes/p0')

    assert (
        test_client.post(
            '/api/v1/settings/themes/over',
            json={'theme': {'primary': '#fff'}},
        ).status_code
        == 201
    )


# ── Orphan active auto-heals ───────────────────────────────────────


@pytest.mark.asyncio
async def test_list_themes_clears_orphan_active(test_client, settings_store):
    settings = _base_settings()
    settings.theme_profiles.save('real', Theme(primary='#fff'))
    object.__setattr__(settings.theme_profiles, 'active', 'ghost')
    await _seed(settings_store, settings)

    response = test_client.get('/api/v1/settings/themes')

    assert response.status_code == 200
    assert response.json()['active_theme'] is None


# ── Main settings endpoint cannot mutate themes ───────────────────


@pytest.mark.asyncio
async def test_main_settings_endpoint_ignores_theme_profiles_payload(
    test_client, settings_store
):
    """A malicious or buggy client might stuff ``theme_profiles`` into a
    ``POST /api/v1/settings`` body to bypass the dedicated theme endpoints
    (which enforce name rules, the count cap, and the per-user lock). The
    server must silently drop the key, keeping all theme state untouched.
    """
    await _seed(settings_store, _base_settings())

    resp = test_client.post(
        '/api/v1/settings',
        json={
            'theme_profiles': {
                'profiles': {'ATTACKER': {'primary': '#fff'}},
                'active': 'ATTACKER',
            },
        },
    )

    assert resp.status_code == 200  # silently ignored, not crashed
    listing = test_client.get('/api/v1/settings/themes').json()
    assert 'ATTACKER' not in {t['name'] for t in listing['themes']}


# ── theme_profiles round-trips through GET /api/v1/settings ──────


@pytest.mark.asyncio
async def test_theme_profiles_round_trips_through_main_settings(
    test_client, settings_store
):
    settings = _base_settings()
    settings.theme_profiles.save('dark', Theme(primary='#fff', app_name='Acme'))
    settings.theme_profiles.active = 'dark'
    await _seed(settings_store, settings)

    body = test_client.get('/api/v1/settings').json()

    assert body['theme_profiles']['active'] == 'dark'
    assert body['theme_profiles']['profiles']['dark']['primary'] == '#fff'
    assert body['theme_profiles']['profiles']['dark']['app_name'] == 'Acme'


# ── Isolation between users ───────────────────────────────────────


@pytest.mark.asyncio
async def test_themes_are_isolated_between_users(tmp_path_factory):
    store_a = FileSettingsStore(
        get_file_store('local', str(tmp_path_factory.mktemp('alice')))
    )
    store_b = FileSettingsStore(
        get_file_store('local', str(tmp_path_factory.mktemp('bob')))
    )
    await store_a.store(_base_settings())
    await store_b.store(_base_settings())

    with _client_for_user('alice', store_a) as ca:
        assert (
            ca.post(
                '/api/v1/settings/themes/alice-only',
                json={'theme': {'primary': '#fff'}},
            ).status_code
            == 201
        )

    with _client_for_user('bob', store_b) as cb:
        body = cb.get('/api/v1/settings/themes').json()
        assert 'alice-only' not in {t['name'] for t in body['themes']}
