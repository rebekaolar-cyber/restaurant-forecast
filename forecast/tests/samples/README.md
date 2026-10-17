# Saved answers from the weather service

Real answers from Open-Meteo for the restaurant's coordinates (52.2066, 6.8914), fetched on
10 October 2026 by a GitHub Actions run and saved exactly as received. The tests run against
these files, so they need no network.

| File | What was asked |
|---|---|
| `open_meteo_archive_2026-09-30_to_2026-10-09.json` | measured weather for the last 10 days |
| `open_meteo_forecast_on_2026-10-10.json` | the last 10 days plus a 14-day forecast, asked on 10 October |
| `open_meteo_archive_2024-10-08_to_2024-10-10.json` | measured weather two years back |
| `open_meteo_error.json` | what the service answers (HTTP 400) to a wrong question |

Daily values asked for: `temperature_2m_max`, `precipitation_sum`, `wind_speed_10m_max`,
`sunshine_duration`, with `timezone=Europe/Amsterdam`.

# Made-up import files

Synthetic files for the importer tests. **Every number in them is invented**; none comes from
the restaurant's real exports. They only copy the *shape* of the real files: the header, the
date format, the service labels (`Di-zo`, `maandag`, `Maandag vanaf 10 augustus`, `2e paasdag`,
empty), the channels and the way an offer is written (`0` for none).

| File | What it stands for |
|---|---|
| `thefork_covers_month.csv` | TheFork "evolution of covers", exported per month |
| `thefork_covers_week.csv` | the same, exported per week (Mondays) |
| `thefork_covers_day.csv` | the same, exported per day |
| `thefork_covers_with_guest_name.csv` | a file with one column too many: must be refused |
| `roster_counts.csv` | our own roster format, `date,role,planned_count`, letters and words mixed |
| `roster_unknown_role.csv` | a role that does not exist: must be refused |
| `roster_with_names.csv` | a roster with a name column: must be refused |
