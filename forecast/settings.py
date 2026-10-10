"""Reads the two values the nightly job needs. They come from GitHub Secrets, never from code."""

from __future__ import annotations

import base64
import json
import os
from collections.abc import Mapping
from dataclasses import dataclass, field


class SettingsError(RuntimeError):
    """A needed setting is missing or is the wrong kind of key."""


@dataclass(frozen=True)
class Settings:
    supabase_url: str
    # repr=False keeps the key out of logs and error messages.
    supabase_secret_key: str = field(repr=False)


def key_role(key: str) -> str | None:
    """What kind of Supabase key this is: 'secret', 'public', or None if it is neither."""
    if key.startswith("sb_secret_"):
        return "secret"
    if key.startswith("sb_publishable_"):
        return "public"
    parts = key.split(".")
    if len(parts) == 3:  # an old-style key: its role is written inside it
        try:
            padded = parts[1] + "=" * (-len(parts[1]) % 4)
            role = json.loads(base64.urlsafe_b64decode(padded)).get("role")
        except (ValueError, json.JSONDecodeError, AttributeError):
            return None
        return {"service_role": "secret", "anon": "public"}.get(role)
    return None


def load_settings(env: Mapping[str, str] | None = None) -> Settings:
    env = os.environ if env is None else env
    url = env.get("SUPABASE_URL", "").strip().rstrip("/")
    key = env.get("SUPABASE_SECRET_KEY", "").strip()

    missing = [name for name, value in (("SUPABASE_URL", url), ("SUPABASE_SECRET_KEY", key)) if not value]
    if missing:
        raise SettingsError(
            f"Missing: {' and '.join(missing)}. Add them in GitHub: the repo > Settings > "
            "Secrets and variables > Actions > New repository secret."
        )
    if not url.startswith("https://"):
        raise SettingsError("SUPABASE_URL must start with https://")

    role = key_role(key)
    if role == "public":
        raise SettingsError(
            "SUPABASE_SECRET_KEY holds the public key. The nightly job needs the secret key "
            "(it starts with sb_secret_), from Supabase > Project Settings > API Keys."
        )
    if role is None:
        raise SettingsError(
            "SUPABASE_SECRET_KEY does not look like a Supabase key. Copy the secret key "
            "(it starts with sb_secret_) from Supabase > Project Settings > API Keys."
        )
    return Settings(supabase_url=url, supabase_secret_key=key)
