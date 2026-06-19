from __future__ import annotations

import re
from typing import Any, Final

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

from openhands.app_server.utils.logger import openhands_logger as logger

# Soft cap — mirrors MAX_PROFILES_PER_USER in llm_profiles.py. Keeps the
# Settings payload bounded and blocks per-user storage blow-ups.
MAX_THEMES_PER_USER: Final[int] = 10

# Hex (#rgb, #rrggbb, #rrggbbaa) or rgb()/rgba() only. This is the injection
# guardrail: these strings are written directly into
# `style.setProperty(cssVar, value)` on the frontend, so arbitrary CSS
# (url(...), calc(...), expression(...), etc.) must be rejected.
_COLOR_PATTERN = re.compile(
    r'^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$'
    r'|^rgba?\(\s*\d{1,3}%?\s*,\s*\d{1,3}%?\s*,\s*\d{1,3}%?\s*(?:,\s*[\d.]+\s*)?\)$'
)

# https:// URLs or base64 data URIs for raster/vector images only.
_LOGO_URL_PATTERN = re.compile(
    r'^https://\S+$|^data:image/(?:png|jpe?g|gif|webp|svg\+xml);base64,[A-Za-z0-9+/=]+$'
)

# Keeps a custom logo from bloating the Settings payload (which is persisted
# as a whole JSON blob per user).
_MAX_LOGO_URL_LENGTH: Final[int] = 100_000

_MAX_APP_NAME_LENGTH: Final[int] = 64


class ThemeNotFoundError(LookupError):
    """Raised when a theme lookup or activation references an unknown name."""

    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f"Theme '{name}' not found")


class ThemeLimitExceededError(ValueError):
    """Raised when saving a new theme would exceed :data:`MAX_THEMES_PER_USER`."""

    def __init__(self, limit: int) -> None:
        self.limit = limit
        super().__init__(
            f'Theme limit reached ({limit}). Delete a theme before saving a new one.'
        )


class ThemeAlreadyExistsError(ValueError):
    """Raised when a rename target collides with an existing theme."""

    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f"Theme '{name}' already exists")


class Theme(BaseModel):
    """A simple custom theme: a few core colors plus basic branding.

    Deliberately small — only the tokens with the broadest visual footprint
    (brand accent, app background, secondary panel background, primary text)
    are exposed. Semantic colors (danger/success) and fine-grained tokens are
    out of scope. All fields are optional; an unset field falls back to the
    application's built-in default.
    """

    model_config = ConfigDict(extra='forbid')

    primary: str | None = None
    base: str | None = None
    base_secondary: str | None = None
    content: str | None = None
    app_name: str | None = None
    logo_url: str | None = None

    @field_validator('primary', 'base', 'base_secondary', 'content')
    @classmethod
    def _validate_color(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            return None
        if not _COLOR_PATTERN.match(value):
            raise ValueError(
                f'Invalid color {value!r}: expected a hex color (#rgb, #rrggbb, '
                '#rrggbbaa) or rgb()/rgba()'
            )
        return value

    @field_validator('app_name')
    @classmethod
    def _validate_app_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            return None
        if len(value) > _MAX_APP_NAME_LENGTH:
            raise ValueError(
                f'app_name must be at most {_MAX_APP_NAME_LENGTH} characters'
            )
        return value

    @field_validator('logo_url')
    @classmethod
    def _validate_logo_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            return None
        if len(value) > _MAX_LOGO_URL_LENGTH:
            raise ValueError(
                f'logo_url must be at most {_MAX_LOGO_URL_LENGTH} characters'
            )
        if not _LOGO_URL_PATTERN.match(value):
            raise ValueError(
                'logo_url must be an https:// URL or a data:image/... base64 URI'
            )
        return value


class ThemeProfiles(BaseModel):
    """Container for saved custom themes.

    Stores a named collection of :class:`Theme` configs plus the name of the
    currently active one (if any). Structurally mirrors ``LLMProfiles`` —
    same invariants, same best-effort load behaviour — but carries no
    secrets, so there's no key-masking serializer to worry about.

    Invariants (enforced on validate + assignment):
    - ``active`` is either ``None`` or a key of ``profiles``.
    - Individual themes that fail to parse (schema drift) are dropped with
      a warning rather than failing the whole ``Settings`` load.
    """

    model_config = ConfigDict(validate_assignment=True)

    profiles: dict[str, Theme] = Field(default_factory=dict)
    active: str | None = None

    # ── Validation ─────────────────────────────────────────────────

    @field_validator('profiles', mode='before')
    @classmethod
    def _skip_invalid_themes(cls, value: Any) -> Any:
        """Best-effort per-theme load: skip entries that fail to validate."""
        if not isinstance(value, dict):
            return value
        valid: dict[str, Any] = {}
        for name, raw in value.items():
            if isinstance(raw, Theme):
                valid[name] = raw
                continue
            try:
                valid[name] = Theme.model_validate(raw)
            except ValidationError as exc:
                logger.warning('Skipping invalid theme %r: %s', name, exc)
        return valid

    @model_validator(mode='after')
    def _reconcile_active(self) -> ThemeProfiles:
        if self.active is not None and self.active not in self.profiles:
            object.__setattr__(self, 'active', None)
        return self

    # ── Queries ────────────────────────────────────────────────────

    def get(self, name: str) -> Theme | None:
        """Return the named theme or ``None`` if it doesn't exist."""
        return self.profiles.get(name)

    def require(self, name: str) -> Theme:
        """Return the named theme or raise :class:`ThemeNotFoundError`."""
        theme = self.profiles.get(name)
        if theme is None:
            raise ThemeNotFoundError(name)
        return theme

    def has(self, name: str) -> bool:
        return name in self.profiles

    def summaries(self) -> list[dict[str, Any]]:
        """Return a ``{name, ...theme fields}`` dict per saved theme.

        Nothing here is sensitive, so unlike LLM profile summaries this
        returns the full config rather than a masked subset.
        """
        return [
            {'name': name, **theme.model_dump(mode='json')}
            for name, theme in self.profiles.items()
        ]

    # ── Mutations ──────────────────────────────────────────────────

    def save(self, name: str, theme: Theme) -> None:
        """Save ``theme`` under ``name``. Overwrites if the name exists.

        Raises :class:`ThemeLimitExceededError` if saving a *new* theme would
        push the count past :data:`MAX_THEMES_PER_USER`.
        """
        if name not in self.profiles and len(self.profiles) >= MAX_THEMES_PER_USER:
            raise ThemeLimitExceededError(MAX_THEMES_PER_USER)
        self.profiles[name] = theme.model_copy()

    def rename(self, old_name: str, new_name: str) -> None:
        """Rename a theme, preserving its config, insertion order, and the
        active flag (if the renamed theme was active).

        Raises :class:`ThemeNotFoundError` if ``old_name`` doesn't exist, or
        :class:`ThemeAlreadyExistsError` if ``new_name`` is already taken by
        a different theme.
        """
        if old_name not in self.profiles:
            raise ThemeNotFoundError(old_name)
        if new_name == old_name:
            return
        if new_name in self.profiles:
            raise ThemeAlreadyExistsError(new_name)

        was_active = self.active == old_name

        renamed: dict[str, Theme] = {
            (new_name if key == old_name else key): theme
            for key, theme in self.profiles.items()
        }
        self.profiles = renamed
        if was_active:
            object.__setattr__(self, 'active', new_name)

    def delete(self, name: str) -> bool:
        """Delete a theme. Returns True if the theme existed.

        Clears ``active`` if the deleted theme was active.
        """
        if name not in self.profiles:
            return False
        del self.profiles[name]
        if self.active == name:
            object.__setattr__(self, 'active', None)
        return True
