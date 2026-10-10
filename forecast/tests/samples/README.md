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
