"""Tests for reading the settings: wrong or missing keys must stop the job with a clear message."""

from __future__ import annotations

import base64

import pytest

from forecast import weather
from forecast.settings import SettingsError, key_role, load_settings

URL = "https://example.supabase.co"
SECRET = "sb_secret_TESTONLY-not-a-real-key"


def old_style_key(role: str) -> str:
    payload = base64.urlsafe_b64encode(('{"role":"%s"}' % role).encode()).decode().rstrip("=")
    return f"header.{payload}.signature"


def test_reads_both_values():
    settings = load_settings({"SUPABASE_URL": URL + "/", "SUPABASE_SECRET_KEY": f" {SECRET}\n"})
    assert settings.supabase_url == URL
    assert settings.supabase_secret_key == SECRET


def test_the_key_never_shows_when_settings_are_printed():
    settings = load_settings({"SUPABASE_URL": URL, "SUPABASE_SECRET_KEY": SECRET})
    assert SECRET not in repr(settings) and SECRET not in str(settings)


@pytest.mark.parametrize(
    "env, message",
    [
        ({}, "Missing: SUPABASE_URL and SUPABASE_SECRET_KEY"),
        ({"SUPABASE_URL": URL}, "Missing: SUPABASE_SECRET_KEY"),
        ({"SUPABASE_URL": URL, "SUPABASE_SECRET_KEY": "   "}, "Missing: SUPABASE_SECRET_KEY"),
        ({"SUPABASE_URL": "http://example.supabase.co", "SUPABASE_SECRET_KEY": SECRET}, "must start with https://"),
        ({"SUPABASE_URL": URL, "SUPABASE_SECRET_KEY": "sb_publishable_abc"}, "holds the public key"),
        ({"SUPABASE_URL": URL, "SUPABASE_SECRET_KEY": old_style_key("anon")}, "holds the public key"),
        ({"SUPABASE_URL": URL, "SUPABASE_SECRET_KEY": "hunter2"}, "does not look like a Supabase key"),
    ],
)
def test_refuses_missing_or_wrong_settings(env, message):
    with pytest.raises(SettingsError, match=message) as caught:
        load_settings(env)
    key = env.get("SUPABASE_SECRET_KEY", "").strip()
    if key:
        assert key not in str(caught.value)  # an error message never repeats the key


def test_recognises_each_kind_of_key():
    assert key_role(SECRET) == "secret"
    assert key_role("sb_publishable_abc") == "public"
    assert key_role(old_style_key("service_role")) == "secret"
    assert key_role(old_style_key("anon")) == "public"
    assert key_role("a.b.c") is None
    assert key_role("") is None


def test_the_job_exits_with_an_error_when_settings_are_missing(monkeypatch, capsys):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SECRET_KEY", raising=False)
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    assert weather.main([]) == 1
    output = capsys.readouterr().out
    assert "FAILED: Weather: Missing: SUPABASE_URL and SUPABASE_SECRET_KEY" in output
    assert "::error title=Weather::Missing: SUPABASE_URL and SUPABASE_SECRET_KEY" in output
