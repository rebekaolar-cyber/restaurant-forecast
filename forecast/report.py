"""Says what happened, in the log and, on GitHub, on the run's summary page.

Never pass personal data or keys to these functions: everything said here is stored in logs.
"""

from __future__ import annotations

import os


def _on_github() -> bool:
    return os.environ.get("GITHUB_ACTIONS") == "true"


def _one_line(text: str) -> str:
    # GitHub reads these three characters as commands, so they have to be written differently.
    return text.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def _title(text: str) -> str:
    # In a title GitHub also treats a comma and a colon as separators.
    return _one_line(text).replace(":", "%3A").replace(",", "%2C")


def _summary(line: str) -> None:
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if path:
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(line + "\n")


def say(text: str) -> None:
    """An ordinary progress line."""
    print(text, flush=True)


def result(title: str, text: str) -> None:
    """A result worth seeing without opening the log."""
    print(f"{title}: {text}", flush=True)
    if _on_github():
        print(f"::notice title={_title(title)}::{_one_line(text)}", flush=True)
        _summary(f"- ✅ **{title}**: {text}")


def failure(title: str, text: str) -> None:
    """Something went wrong. The caller is expected to stop with a non-zero exit code."""
    print(f"FAILED: {title}: {text}", flush=True)
    if _on_github():
        print(f"::error title={_title(title)}::{_one_line(text)}", flush=True)
        _summary(f"- ❌ **{title}**: {text}")
