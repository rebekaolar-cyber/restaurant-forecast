"""Tests for the lines that end up on a workflow run page."""

from __future__ import annotations

from forecast import report


def test_plain_output_outside_github(monkeypatch, capsys):
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    report.result("Weather", "745 days written")
    report.failure("Weather", "no weather for 1 day(s)")
    assert capsys.readouterr().out == "Weather: 745 days written\nFAILED: Weather: no weather for 1 day(s)\n"


def test_on_github_a_result_shows_on_the_run_page(monkeypatch, capsys, tmp_path):
    summary = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))

    report.result("Weather, repeat run: Restaurant Habibi", "100% the same\nnothing added")
    report.failure("Weather", "HTTP 503: busy")

    lines = capsys.readouterr().out.splitlines()
    # A comma or colon in the title, and a % or line break anywhere, would cut the text short.
    assert "::notice title=Weather%2C repeat run%3A Restaurant Habibi::100%25 the same%0Anothing added" in lines
    assert "::error title=Weather::HTTP 503: busy" in lines
    assert summary.read_text(encoding="utf-8").splitlines() == [
        "- ✅ **Weather, repeat run: Restaurant Habibi**: 100% the same",
        "nothing added",
        "- ❌ **Weather**: HTTP 503: busy",
    ]
