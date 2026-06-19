"""Unit tests for :class:`Theme` and :class:`ThemeProfiles`.

Settings-integration tests (round-trip through ``Settings``, the
``/api/v1/settings/themes`` endpoints) live in
``tests/unit/app_server/test_themes_api.py``.
"""

import pytest
from pydantic import ValidationError

from openhands.app_server.settings.theme_profiles import (
    MAX_THEMES_PER_USER,
    Theme,
    ThemeAlreadyExistsError,
    ThemeLimitExceededError,
    ThemeNotFoundError,
    ThemeProfiles,
)


def _make_theme(**kwargs) -> Theme:
    return Theme(**kwargs)


# ── Theme validation ─────────────────────────────────────────────


@pytest.mark.parametrize(
    'value',
    [
        '#fff',
        '#FFF0',
        '#abcdef',
        '#AABBCCDD',
        'rgb(0, 0, 0)',
        'rgba(255, 255, 255, 0.5)',
        'rgb(10%, 20%, 30%)',
    ],
)
def test_valid_colors_accepted(value):
    theme = Theme(primary=value)
    assert theme.primary == value


@pytest.mark.parametrize(
    'value',
    [
        'url(javascript:alert(1))',
        'calc(1px + 2px)',
        'red',  # named colors not supported by the simple regex
        'expression(alert(1))',
        '#gggggg',
        '',
    ],
)
def test_invalid_colors_rejected(value):
    if value == '':
        # Empty string normalizes to None rather than raising.
        assert Theme(primary=value).primary is None
        return
    with pytest.raises(ValidationError):
        Theme(primary=value)


def test_color_whitespace_is_stripped():
    assert Theme(primary='  #fff  ').primary == '#fff'


def test_app_name_length_cap():
    Theme(app_name='a' * 64)
    with pytest.raises(ValidationError):
        Theme(app_name='a' * 65)


def test_app_name_blank_normalizes_to_none():
    assert Theme(app_name='   ').app_name is None


@pytest.mark.parametrize(
    'value',
    [
        'https://example.com/logo.png',
        'data:image/png;base64,aGVsbG8=',
        'data:image/svg+xml;base64,PHN2Zz4=',
    ],
)
def test_valid_logo_urls_accepted(value):
    assert Theme(logo_url=value).logo_url == value


@pytest.mark.parametrize(
    'value',
    [
        'http://example.com/logo.png',  # not https
        'javascript:alert(1)',
        'data:text/html;base64,aGVsbG8=',  # not an image mime type
        'ftp://example.com/logo.png',
    ],
)
def test_invalid_logo_urls_rejected(value):
    with pytest.raises(ValidationError):
        Theme(logo_url=value)


def test_logo_url_length_cap():
    huge = 'https://example.com/' + 'a' * 100_000
    with pytest.raises(ValidationError):
        Theme(logo_url=huge)


def test_theme_rejects_unknown_fields():
    with pytest.raises(ValidationError):
        Theme.model_validate({'primary': '#fff', 'totally_made_up_field': 'x'})


# ── Queries ───────────────────────────────────────────────────────


def test_has_reflects_presence():
    profiles = ThemeProfiles()
    assert profiles.has('x') is False
    profiles.save('x', _make_theme(primary='#fff'))
    assert profiles.has('x') is True


def test_require_returns_theme_for_present():
    profiles = ThemeProfiles()
    profiles.save('x', _make_theme(app_name='Acme'))

    theme = profiles.require('x')

    assert isinstance(theme, Theme)
    assert theme.app_name == 'Acme'


def test_require_raises_theme_not_found_with_name():
    profiles = ThemeProfiles()

    with pytest.raises(ThemeNotFoundError) as exc_info:
        profiles.require('missing')

    assert exc_info.value.name == 'missing'
    assert "'missing'" in str(exc_info.value)


def test_summaries_returns_full_config_per_theme():
    profiles = ThemeProfiles()
    profiles.save('p1', _make_theme(primary='#fff', app_name='Acme'))

    summaries = {s['name']: s for s in profiles.summaries()}

    assert summaries['p1']['primary'] == '#fff'
    assert summaries['p1']['app_name'] == 'Acme'


def test_summaries_empty_by_default():
    assert ThemeProfiles().summaries() == []


# ── Mutations ─────────────────────────────────────────────────────


def test_save_overwrites_existing_entry():
    profiles = ThemeProfiles()
    profiles.save('p', _make_theme(primary='#fff'))
    profiles.save('p', _make_theme(primary='#000'))

    assert profiles.get('p').primary == '#000'
    assert len(profiles.profiles) == 1


def test_save_stores_a_copy_not_the_caller_reference():
    profiles = ThemeProfiles()
    original = _make_theme(primary='#fff')

    profiles.save('p', original)

    assert profiles.get('p') is not original


def test_delete_returns_true_then_false():
    profiles = ThemeProfiles()
    profiles.save('p', _make_theme())

    assert profiles.delete('p') is True
    assert profiles.get('p') is None
    assert profiles.delete('p') is False


def test_delete_clears_active_when_active_removed():
    profiles = ThemeProfiles()
    profiles.save('p', _make_theme())
    profiles.active = 'p'

    profiles.delete('p')

    assert profiles.active is None


def test_delete_leaves_active_alone_when_other_removed():
    profiles = ThemeProfiles()
    profiles.save('p1', _make_theme())
    profiles.save('p2', _make_theme())
    profiles.active = 'p1'

    profiles.delete('p2')

    assert profiles.active == 'p1'


# ── Rename ────────────────────────────────────────────────────────


def test_rename_preserves_theme_config():
    profiles = ThemeProfiles()
    profiles.save('old', _make_theme(primary='#fff', app_name='Acme'))

    profiles.rename('old', 'new')

    assert profiles.get('old') is None
    renamed = profiles.get('new')
    assert renamed is not None
    assert renamed.primary == '#fff'
    assert renamed.app_name == 'Acme'


def test_rename_preserves_active_flag_when_renamed_was_active():
    profiles = ThemeProfiles()
    profiles.save('p', _make_theme())
    profiles.active = 'p'

    profiles.rename('p', 'q')

    assert profiles.active == 'q'


def test_rename_leaves_active_alone_when_renaming_other():
    profiles = ThemeProfiles()
    profiles.save('p1', _make_theme())
    profiles.save('p2', _make_theme())
    profiles.active = 'p1'

    profiles.rename('p2', 'p2-renamed')

    assert profiles.active == 'p1'


def test_rename_to_same_name_is_noop():
    profiles = ThemeProfiles()
    profiles.save('p', _make_theme())
    profiles.active = 'p'

    profiles.rename('p', 'p')

    assert profiles.has('p')
    assert profiles.active == 'p'


def test_rename_unknown_raises_theme_not_found():
    profiles = ThemeProfiles()
    with pytest.raises(ThemeNotFoundError, match='ghost'):
        profiles.rename('ghost', 'new')


def test_rename_to_existing_name_raises():
    profiles = ThemeProfiles()
    profiles.save('a', _make_theme())
    profiles.save('b', _make_theme())

    with pytest.raises(ThemeAlreadyExistsError, match='b'):
        profiles.rename('a', 'b')

    assert profiles.has('a')
    assert profiles.has('b')


def test_rename_preserves_insertion_order():
    profiles = ThemeProfiles()
    profiles.save('a', _make_theme())
    profiles.save('b', _make_theme())
    profiles.save('c', _make_theme())

    profiles.rename('b', 'B')

    assert list(profiles.profiles.keys()) == ['a', 'B', 'c']


# ── Invariants ────────────────────────────────────────────────────


def test_active_stays_in_profiles_at_all_entry_points():
    loaded = ThemeProfiles.model_validate(
        {'profiles': {'a': {'primary': '#fff'}}, 'active': 'ghost'}
    )
    assert loaded.active is None

    profiles = ThemeProfiles()
    profiles.save('a', _make_theme())
    profiles.active = 'ghost'
    assert profiles.active is None
    profiles.active = 'a'
    assert profiles.active == 'a'


def test_orphan_active_heals_on_roundtrip():
    profiles = ThemeProfiles()
    profiles.save('real', _make_theme())
    object.__setattr__(profiles, 'active', 'ghost')  # bypass validator

    data = profiles.model_dump(mode='json')
    rehydrated = ThemeProfiles.model_validate(data)

    assert rehydrated.active is None
    assert rehydrated.has('real')


# ── Per-theme best-effort load ────────────────────────────────────


def test_invalid_theme_entry_is_skipped_not_fatal():
    data = {
        'profiles': {
            'ok': {'primary': '#fff'},
            'bad': {'primary': 'url(javascript:alert(1))'},
        },
    }

    profiles = ThemeProfiles.model_validate(data)

    assert list(profiles.profiles) == ['ok']


# ── Count cap ─────────────────────────────────────────────────────


def test_save_fails_past_limit():
    profiles = ThemeProfiles()
    for i in range(MAX_THEMES_PER_USER):
        profiles.save(f'p{i}', _make_theme())

    with pytest.raises(ThemeLimitExceededError) as exc_info:
        profiles.save('one-too-many', _make_theme())

    assert exc_info.value.limit == MAX_THEMES_PER_USER


def test_save_at_limit_can_overwrite_existing():
    profiles = ThemeProfiles()
    for i in range(MAX_THEMES_PER_USER):
        profiles.save(f'p{i}', _make_theme(primary='#fff'))

    profiles.save('p0', _make_theme(primary='#000'))

    assert profiles.get('p0').primary == '#000'
