# Restaurant site: website + staffing forecast

A three-day working demo for one restaurant in the Netherlands. Test project, **fake data only**.

1. **Public website**: menu, opening hours, contact, a link to the restaurant's booking system.
2. **Staffing forecast**: every night it predicts guests per shift for the next 14 days from
   bookings, weather and the calendar, turns guests into staff per role with the manager's own
   rules, and shows the result on a dashboard behind a login.

The owner (Rebeka) reads code but is not an experienced developer. Explain choices in plain
language. When something has to be done by hand, say exactly where to click and what to enter.

## Who works where

Two conversations work in this repo at the same time. Stay in your own folders.

| Conversation | Branch   | Folders                                           |
|--------------|----------|---------------------------------------------------|
| SERVER       | `server` | `forecast/`, `supabase/`, `.github/workflows/`    |
| SITE         | its own  | `site/`                                           |

Small commits on your own branch, and a pull request at the end of each stage.

## Restaurant facts

- Restaurant Habibi, Wethouder Beversstraat 185, 7543 BK Enschede.
  Website https://habibienschede.nl, bookings https://habibienschede.nl/reserveren/
- 254 seats at 58 tables: indoors 120 seats at 30 tables, Binnentuin (courtyard garden)
  134 seats at 28 tables. The Binnentuin is usable all year.
- Open every day, dinner only, so there is **one shift per day, called `dinner`**.
  Mon-Thu 17:00-23:00, Fri-Sat 17:00-01:00, Sun 16:00-23:00. Friday and Saturday run past
  midnight: everything until closing belongs to the day the shift started.
- **Fixed crew** on every open day, whatever the forecast says: 4 kitchen staff from 14:00 and
  2 service staff from one hour before opening. The forecast only decides how many extra people
  come on top, and it never goes below this crew.

## Stack (decided; ask before changing it)

- One private GitHub repo: `forecast/` (Python), `site/` (website), `supabase/` (database
  migrations), `.github/workflows/` (nightly job).
- Database: Supabase Postgres in an EU region. Test project `restaurant-forecast-test`
  (ref `wuyqodgnnjoefaxepkiz`, region eu-central-1, URL `https://wuyqodgnnjoefaxepkiz.supabase.co`).
- Forecast: Python. A simple baseline first, then LightGBM. **The model predicts guests.
  Staff numbers always come from rules, never from the model.**
- Nightly job: GitHub Actions. Weather: Open-Meteo (free tier, prototype only).
- Website: static build on Cloudflare Pages. The dashboard is a page behind a Supabase login.

## The shared contract (both conversations depend on it)

Every table has `restaurant_id` (in `restaurants` it is the `id` column).

- `restaurants(id, name, latitude, longitude, timezone, seats)`
- `restaurant_members(user_id, restaurant_id)`
- `staffing_rules(restaurant_id, role, guests_per_staff, min_staff)`
- `daily_weather(restaurant_id, date, temp_max, rain_mm, wind_max, sunshine_hours, is_forecast)`
- `bookings(id, restaurant_id, visit_date, visit_time, party_size, table_no, created_at, status)`
- `receipts(id, restaurant_id, opened_at, closed_at, table_no, guests, total)`
- `forecasts(restaurant_id, date, shift, predicted_guests, servers, cooks, model, created_at)`,
  one row per restaurant, date and shift
- `forecast_overrides(restaurant_id, date, shift, servers, cooks, note, updated_by, updated_at)`

The server writes `forecasts`. The dashboard reads `forecasts` and `daily_weather` and writes
`forecast_overrides`. **Nothing else crosses between the two halves.** If the contract has to
change, stop and tell Rebeka, so she can pass it to the other conversation.

Details the contract leaves open, as built in `supabase/migrations/`:

- Ids are `uuid`. Dates are `date`, timestamps are `timestamptz` (UTC).
- `role` is `'server'` or `'cook'`. `shift` is always `'dinner'`.
- Staff = the larger of `min_staff` and guests / `guests_per_staff` rounded up.
- Weather units: `temp_max` in °C, `rain_mm` in mm, `wind_max` in km/h, `sunshine_hours` in hours.
  `rain_mm` is all precipitation of the day (Open-Meteo `precipitation_sum`). Today and later
  have `is_forecast = true`; a day becomes `false` once it has passed and was loaded again.
- `bookings.status` is `'booked'`, `'completed'`, `'no_show'` or `'cancelled'`.
  `visit_date` is the service day (the day the shift started).
- `forecast_overrides.servers` / `cooks` may be null, meaning "keep the forecast's number".
  The database fills `updated_by` and `updated_at` itself on every insert and update.

## Never traded for speed

- **No personal data anywhere**: no guest names, phone numbers, emails, staff names or salaries.
  Not in tables, fake data, code, logs or chat.
- **Row level security on every table.** A logged-in member reads only their own restaurant's
  rows. `bookings` and `receipts` are for the nightly job only.
- **Public sign-up is off.** Users are invited.
- **Secret keys never appear in chat, code or commits.** They live in GitHub Secrets and Rebeka
  adds them by hand. Never ask her to paste one.
- **The website code holds only the project URL and the public (publishable) key.**

How the lock is built (keep it this way when adding tables):

- The anonymous role has no rights on any table.
- Logged-in users may read `restaurants`, `restaurant_members`, `staffing_rules`,
  `daily_weather` and `forecasts`, and read and write `forecast_overrides`, and only the rows of
  a restaurant they are a member of.
- Nobody but the nightly job (secret key) can touch `bookings` and `receipts`.
- The nightly job can read `forecast_overrides` but has no right to write it, so it can never
  overwrite a manager's override.
- New tables get no rights automatically. Every new table needs RLS, policies and explicit grants
  in its migration, and a matching check in `supabase/tests/rls_lock.sql`.

## How to work

- Work in stages. At the end of each stage, stop and report: what works, how it was checked, and
  what Rebeka has to do by hand.
- Check your own work before reporting: run the tests, open the page, query the table.
- Ask first if something costs money, touches the restaurant's real systems, or can't be undone.
- The cloud sandbox usually cannot reach Supabase or the weather service. Change the database
  through the Supabase connector, and run anything that needs the secret key as a GitHub Actions
  workflow that can be started by hand. Test logic locally against saved sample responses.

## Database commands

- Migrations live in `supabase/migrations/` and are applied through the Supabase connector.
  The file name's timestamp must match the version recorded in the database.
- `supabase/seed.sql` holds the starting rows (safe to run again).
- `supabase/tests/rls_lock.sql` proves the lock. Run it after every schema change; it changes
  nothing (everything it inserts is rolled back). Locally:
  `supabase/tests/run_local.sh` starts a throwaway Postgres, applies migrations and seed, and
  runs the test. No network or keys needed.
- `supabase/tests/check_public_api.py tables` asks the real project over the web what a visitor
  without a login gets (must be nothing), and `... signup` checks that public sign-up is off.
  They need only the project URL and the public key.
- `.github/workflows/lock-check.yml` runs all three on every pull request that touches
  `supabase/`, and has a "Run workflow" button.

## Forecast code (`forecast/`)

Run everything from the repo root. `pip install -r forecast/requirements-dev.txt` first.

- `python -m pytest forecast -q` runs the tests. They use real saved answers from Open-Meteo
  (`forecast/tests/samples/`) and a throwaway Postgres with the real migrations and seed, used
  as the nightly job's own database role, so rights are tested too. No network, no keys.
- `forecast/db.py` is the only way forecast code talks to the database: read, count and
  insert-or-update over the Supabase web API. In tests `LocalDatabase` (in
  `forecast/tests/conftest.py`) stands in for it.
- `forecast/report.py`: use `report.result` and `report.failure` for anything worth seeing on a
  workflow run page. Never pass keys or personal data to them.
- `python -m forecast.weather` loads two years of history and the 14-day forecast from
  Open-Meteo into `daily_weather` for every restaurant. `--history-days N` loads less,
  `--expect-unchanged` fails if the run added rows. Safe to run again: it inserts-or-updates on
  `restaurant_id, date`.

Workflows:

- `forecast-tests.yml`: the tests, plus one job that asks the real Open-Meteo (no keys).
- `weather.yml` ("Load weather"): the real load, run twice; the second run must add nothing.
  Has a "Run workflow" button and also runs on pull requests that change the weather code.
- `lock-check.yml`: see Database commands.

Good to know when working from the cloud sandbox:

- Workflow logs cannot be downloaded there. Results printed with `forecast/report.py` can be
  read with `gh api repos/OWNER/REPO/check-runs/JOB_ID/annotations`.
- Path filters on `pull_request` look at the whole pull request, so every push to an open pull
  request runs every workflow whose paths the pull request touches.
- The "Run workflow" button only exists for workflows that are on `main`. A failed run can be
  started again with `gh api -X POST repos/OWNER/REPO/actions/runs/RUN_ID/rerun-failed-jobs`.

## GitHub Secrets (added by Rebeka by hand, never pasted in chat)

- `SUPABASE_URL`: the project URL above.
- `SUPABASE_SECRET_KEY`: the secret key (`sb_secret_...`) from Supabase > Project Settings >
  API Keys. Only the nightly job uses it.
