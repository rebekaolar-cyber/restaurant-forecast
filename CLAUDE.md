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
  **Mondays only since 10 August 2026** (confirmed by Rebeka, 10 Oct 2026; TheFork shows it as the
  service "Maandag vanaf 10 augustus"). Before that Mondays were closed: a closed evening is never
  "0 guests". `forecast/opening.py` holds this; the fake history, forecast and backtest use it.
  Mon-Thu 17:00-23:00, Fri-Sat 17:00-01:00, Sun 16:00-23:00. Friday and Saturday run past
  midnight: everything until closing belongs to the day the shift started.
- **Fixed crew** on every open day, whatever the forecast says: 4 kitchen staff from 14:00 and
  2 service staff from one hour before opening. The forecast only decides how many extra people
  come on top, and it never goes below this crew.
- **The roster** (from the restaurant's real rosters, 10 Oct 2026) has four roles:
  W = floor staff, B = bar, R = runner, F = food. Kitchen staff are not on this roster: they stay
  the fixed 4 from 14:00.
- **The manager's staffing rule** is a table by guest number, not a ratio:

  | Guests | W floor | B bar | R runner | F food |
  |--------|---------|-------|----------|--------|
  | 100    | 3       | 1     | 1        | 2      |
  | 120    | 4       | 2     | 2        | 3      |
  | 180    | 6       | 3     | 2        | 3      |
  | 250    | 6       | 3     | 3        | 4      |
  | 300    | 6       | 3     | 3        | 4      |

  Read as: a row applies from its guest number up to the next row, below 100 guests the first row
  applies, and the numbers are totals (the 2 fixed service staff included). **Rebeka has not
  confirmed this reading yet.** It only changes the rows in `staffing_rules`, not the contract.
- **The manager's weekly plan**: the same guests per weekday, every week: Mon 100, Tue 100,
  Wed 100, Thu 120, Fri 250, Sat 300, Sun 180. This is the benchmark in every backtest. Our
  forecast has to beat it. It lives in `forecast/manager_plan.py`.
- **One real number**: on Friday 9 October 2026 the reservation book held 47 reservations for
  174 people, walk-ins included. The fake history is tuned so a normal Friday lands there.

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
- `staffing_rules(restaurant_id, guests_from, servers, bar_staff, runners, food_staff, cooks)`,
  one row per guest level
- `daily_weather(restaurant_id, date, temp_max, rain_mm, wind_max, sunshine_hours, is_forecast)`
- `bookings(id, restaurant_id, visit_date, visit_time, party_size, table_no, created_at, status)`
- `receipts(id, restaurant_id, opened_at, closed_at, table_no, guests, total)`
- `forecasts(restaurant_id, date, shift, predicted_guests, servers, bar_staff, runners,
  food_staff, cooks, model, created_at)`, one row per restaurant, date and shift
- `forecast_overrides(restaurant_id, date, shift, servers, bar_staff, runners, food_staff, cooks,
  note, updated_by, updated_at)`
- `covers(restaurant_id, period_start, period_end, service, channel, offer, covers, bookings,
  no_shows, cancellations, late_cancellations, source, imported_at)`, TheFork's aggregate
  export, one row per restaurant, period, service, channel and offer
- `rosters(restaurant_id, date, shift, role, planned_count, source, imported_at)`, the manager's
  planned staff per role per evening, counts only, one row per restaurant, date, shift and role
- `forecast_reviews(restaurant_id, date, shift, role, actual_guests, verdict, note, reviewed_by,
  reviewed_at)`, the manager's end-of-day verdict, one row per restaurant, date, shift and role

The server writes `forecasts`. The dashboard reads `forecasts` and `daily_weather` and writes
`forecast_overrides`. **Nothing else crosses between the two halves.** If the contract has to
change, stop and tell Rebeka, so she can pass it to the other conversation.

Contract change of 10 Oct 2026 (migration `20261010133957`), made because the real roster has
four roles and a staffing table by guest bands. It only adds; nothing the dashboard used was
renamed or removed:

- `forecasts` and `forecast_overrides` gained `bar_staff`, `runners` and `food_staff`.
- `servers` now means floor staff (W). `cooks` means kitchen and is always the fixed 4.
- `staffing_rules` changed from one row per role (`role, guests_per_staff, min_staff`) to one
  row per guest level. The dashboard does not read it.
- The old rule table still exists as `staffing_rules_retired`, closed to everyone. It is used by
  nothing. Deleting it needs Rebeka's own confirmation in the Supabase connector.

Contract change of 17 Oct 2026 (migration `20261017193218`), phase 1 of "real data in": the
tables that let real, non-personal numbers replace the fake history. It only adds; nothing the
dashboard used was renamed or removed:

- New tables `covers`, `rosters` and `forecast_reviews` (columns above).
- The dashboard may read `covers`, `rosters` and `forecast_reviews`, and writes
  `forecast_reviews` exactly as it writes `forecast_overrides`: a member inserts, updates and
  deletes their own restaurant's rows, and the database fills `reviewed_by` and `reviewed_at`.
- The nightly job writes `covers` and `rosters` through the two importers
  (`forecast/import_covers.py`, `forecast/import_rosters.py`) and only reads
  `forecast_reviews`. It has no right to write a review.
- `rosters.role` and `forecast_reviews.role` use the same words as the `forecasts` columns:
  `servers`, `bar_staff`, `runners`, `food_staff`, `cooks`; `forecast_reviews.role` also knows
  `all` (the evening as a whole, where `actual_guests` belongs). `verdict` is `right`,
  `too_many` or `too_few`. `shift` is `dinner`.
- `covers`: a per-day row has `period_start = period_end`, a weekly row starts on a Monday and
  ends on the Sunday, a monthly row starts on the 1st and ends on the last day of the month.
  `service`, `channel` and `offer` are TheFork's labels as exported; `''` means empty or, for
  `offer`, no offer. `covers` means guests booked.

Details the contract leaves open, as built in `supabase/migrations/`:

- Ids are `uuid`. Dates are `date`, timestamps are `timestamptz` (UTC).
- `shift` is always `'dinner'`.
- Roster letter to column: W = `servers`, B = `bar_staff`, R = `runners`, F = `food_staff`.
  Kitchen = `cooks`.
- Staff for a guest number = the `staffing_rules` row with the highest `guests_from` that is not
  above it; below the first row, the first row. `forecast/staffing.py` does this.
- `forecasts.model` is `'placeholder'` (seed rows) or `'baseline'`. `created_at` is the moment
  the forecast was made.
- Weather units: `temp_max` in °C, `rain_mm` in mm, `wind_max` in km/h, `sunshine_hours` in hours.
  `rain_mm` is all precipitation of the day (Open-Meteo `precipitation_sum`). Today and later
  have `is_forecast = true`; a day becomes `false` once it has passed and was loaded again.
- `bookings.status` is `'booked'`, `'completed'`, `'no_show'` or `'cancelled'`.
  `visit_date` is the service day (the day the shift started). The book includes walk-ins, as
  the restaurant's own book does: a walk-in is a booking made at the moment the party arrives.
- A receipt belongs to the evening it was opened on; anything before 06:00 counts for the evening
  before.
- Every staff column in `forecast_overrides` may be null, meaning "keep the forecast's number".
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
- Logged-in members read `covers` and `rosters` (own restaurant only) and cannot write them;
  the nightly job (the importers) reads and writes them.
- `forecast_reviews` is locked like `forecast_overrides`: members read and write their own
  restaurant's rows, the database stamps `reviewed_by` and `reviewed_at`, and the nightly job
  can only read.
- `staffing_rules_retired` is closed to everyone, the nightly job included.
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
- `python -m forecast.fake_history` is the **fake booking system**: it fills `bookings` and
  `receipts` with made-up evenings built on the real weather, from a fixed seed. The same evening
  always comes out the same. Run a day later, it adds what "happened" since. An evening that has
  receipts is never changed again. `--rebuild` deletes the restaurant's bookings and receipts
  first. **Fake data only: take it out of the nightly job before real bookings are imported.**
- `forecast/baseline.py` is the baseline forecast: the average of the same weekday over the last
  6 weeks, plus the difference between the guests already booked and what was booked at the same
  distance for those 6 evenings (kept within half the average).
- `python -m forecast.predict` writes the next 14 evenings to `forecasts`: guests from the
  baseline, staff from `staffing_rules`.
- `python -m forecast.backtest` replays the last 3 months at 1, 3, 7 and 14 days ahead and
  compares our forecast with the manager's plan. With `--offline WEATHER_CSV --report-dir
  forecast/reports` it needs no database and writes `forecast/reports/baseline_backtest.md` and
  `.json`. A test fails if the saved report is not what the code produces.
- `python -m forecast.nightly --fake-feed` is the nightly job: weather, fake bookings, forecast,
  in that order. It stops at the first failing step and exits with an error.
- `python -m forecast.import_covers FILE [FILE ...]` loads TheFork's "evolution of covers" CSV
  export (Reports > Evolution of covers > export) into `covers`. The header must be exactly
  `restaurantName,period,service,channel,offer,covers,bookings,no shows,cancellations,late
  cancellations`; any other file is refused, which is the guard against exports that carry
  guest names. The period size is read from the dates (`--period day|week|month` overrides it;
  a file with one row dated the 1st looks like a month). Safe to run again. `--sql` prints the
  insert-or-update statements instead of writing, with no file name in them, so a real export
  can be loaded through the Supabase connector without the file entering the repo.
- `python -m forecast.import_rosters FILE` loads our own roster file, header exactly
  `date,role,planned_count` (optionally `,source`), counts only, into `rosters`. `role` is one
  of the five words or the roster letter (W B R F K). With more than one restaurant in the
  database, `--restaurant NAME` says which. Safe to run again. `--sql` as above.
- Both importers check the whole file first and write nothing if any row is wrong. Neither is
  part of the nightly job: they are run by hand when a new export is there.
- **Days ahead** are counted as the nightly job writes them: day 1 is the evening of the day the
  job runs (it runs in the night), day 14 is thirteen days later.
- The backtest numbers are on fake history. The fake evenings sit about 30% below the manager's
  plan on every weekday, because the one real Friday (174 guests against 250 planned) says so.
  That is an assumption for the other days. Say this whenever the benchmark comparison is shown.

Workflows:

- `nightly.yml` ("Nightly forecast"): the nightly job at 01:00 UTC, with a "Run workflow"
  button. When started by hand or by a pull request it also runs a second time (must add no
  rows) and runs the backtest on the database.
- `forecast-tests.yml`: the tests, plus one job that asks the real Open-Meteo (no keys).
- `weather.yml` ("Load weather"): loads the full two years of weather. By hand only.
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
