#!/usr/bin/env python3
"""Asks the real project, over the public web API, what a visitor without a login gets.

It uses only the project URL and the PUBLIC (publishable) key: the same two values the website
ships to every visitor. It only reads. It never writes anything and never prints row contents.

    python3 supabase/tests/check_public_api.py tables     every table must give nothing
    python3 supabase/tests/check_public_api.py signup     public sign-up must be off
    python3 supabase/tests/check_public_api.py selftest   checks the judging logic, no network

Needs SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY in the environment (not for selftest).
"""

from __future__ import annotations

import base64
import json
import os
import sys
import urllib.error
import urllib.request

# Every table of the shared contract. Add new tables here when a migration adds one.
TABLES = [
    "restaurants",
    "restaurant_members",
    "staffing_rules",
    "daily_weather",
    "bookings",
    "receipts",
    "forecasts",
    "forecast_overrides",
    "staffing_rules_retired",
    "covers",
    "rosters",
    "forecast_reviews",
]


def judge_table(status: int, body: str) -> tuple[bool, str]:
    """Decide whether an anonymous read of one table gave nothing."""
    if status in (401, 403) and ("42501" in body or "permission denied" in body):
        return True, f"refused (HTTP {status}, permission denied)"
    if status == 200:
        try:
            rows = json.loads(body)
        except json.JSONDecodeError:
            return False, "HTTP 200 with an answer that is not JSON"
        if rows == []:
            return True, "empty list (HTTP 200, 0 rows)"
        count = len(rows) if isinstance(rows, list) else 1
        return False, f"LEAK: returned {count} row(s)"
    return False, f"unexpected answer (HTTP {status}): {body[:200]}"


def judge_signup(status: int, body: str) -> tuple[bool, str]:
    """Decide whether public sign-up is switched off, from the auth settings answer."""
    if status != 200:
        return False, f"unexpected answer (HTTP {status}): {body[:200]}"
    try:
        settings = json.loads(body)
    except json.JSONDecodeError:
        return False, "answer is not JSON"
    if settings.get("disable_signup") is True:
        return True, "public sign-up is off"
    return False, "public sign-up is ON"


def looks_secret(key: str) -> bool:
    """True if the key is a secret key. This check must never be given one."""
    if key.startswith("sb_secret_"):
        return True
    parts = key.split(".")
    if len(parts) == 3:  # an old-style key: read its role without verifying it
        try:
            padded = parts[1] + "=" * (-len(parts[1]) % 4)
            payload = json.loads(base64.urlsafe_b64decode(padded))
            return payload.get("role") != "anon"
        except (ValueError, json.JSONDecodeError):
            return False
    return False


def fetch(url: str, key: str) -> tuple[int, str]:
    request = urllib.request.Request(url, headers={"apikey": key, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return response.status, response.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode("utf-8", "replace")


def report(ok: bool, text: str) -> None:
    """Prints one result. On GitHub it also shows up on the run's summary page."""
    verdict = "PASS" if ok else "FAIL"
    print(f"{verdict}  {text}")
    if os.environ.get("GITHUB_ACTIONS") == "true":
        print(f"::{'notice' if ok else 'error'} title={verdict}::{text}")
        summary_file = os.environ.get("GITHUB_STEP_SUMMARY")
        if summary_file:
            with open(summary_file, "a", encoding="utf-8") as handle:
                handle.write(f"- {'✅' if ok else '❌'} **{verdict}** {text}\n")


def settings_from_env() -> tuple[str, str]:
    url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    key = os.environ.get("SUPABASE_PUBLISHABLE_KEY", "")
    if not url or not key:
        sys.exit("Set SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY first.")
    if looks_secret(key):
        sys.exit("Refusing to run: this looks like a SECRET key. Use the public key here.")
    return url, key


def check_tables() -> int:
    url, key = settings_from_env()
    failures = 0
    for table in TABLES:
        status, body = fetch(f"{url}/rest/v1/{table}?select=*", key)
        ok, summary = judge_table(status, body)
        failures += 0 if ok else 1
        report(ok, f"anonymous read of {table}: {summary}")
    print(f"\n{len(TABLES) - failures} passed, {failures} failed")
    return 1 if failures else 0


def check_signup() -> int:
    url, key = settings_from_env()
    status, body = fetch(f"{url}/auth/v1/settings", key)
    ok, summary = judge_signup(status, body)
    if not ok:
        summary += (
            ". To fix: Supabase dashboard > Authentication > Sign In / Providers > "
            "switch off 'Allow new users to sign up' > Save. Then run this check again."
        )
    report(ok, summary)
    return 0 if ok else 1


def selftest() -> int:
    """Runs the judging logic against saved answers of each kind. No network."""
    denied = '{"code":"42501","details":null,"hint":null,"message":"permission denied for table forecasts"}'
    cases = [
        (judge_table(401, denied)[0], True, "refused for a visitor"),
        (judge_table(403, denied)[0], True, "refused for a logged-in user"),
        (judge_table(200, "[]")[0], True, "empty list"),
        (judge_table(200, '[{"date":"2026-10-10"}]')[0], False, "rows came back"),
        (judge_table(200, "<html>")[0], False, "not JSON"),
        (judge_table(500, "boom")[0], False, "server error is not proof"),
        (judge_table(404, '{"code":"PGRST205"}')[0], False, "unknown table is not proof"),
        (judge_signup(200, '{"disable_signup":true}')[0], True, "sign-up off"),
        (judge_signup(200, '{"disable_signup":false}')[0], False, "sign-up on"),
        (judge_signup(200, "{}")[0], False, "setting missing"),
        (judge_signup(401, "{}")[0], False, "settings refused"),
        (looks_secret("sb_secret_abc"), True, "new secret key"),
        (looks_secret("sb_publishable_abc"), False, "new public key"),
        (looks_secret("x." + base64.urlsafe_b64encode(b'{"role":"service_role"}').decode() + ".y"), True, "old secret key"),
        (looks_secret("x." + base64.urlsafe_b64encode(b'{"role":"anon"}').decode() + ".y"), False, "old public key"),
    ]
    failures = [name for got, want, name in cases if got != want]
    for name in failures:
        print(f"FAIL  {name}")
    print(f"{len(cases) - len(failures)} passed, {len(failures)} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    commands = {"tables": check_tables, "signup": check_signup, "selftest": selftest}
    if len(sys.argv) != 2 or sys.argv[1] not in commands:
        sys.exit(__doc__)
    sys.exit(commands[sys.argv[1]]())
