-- Contract tables for the Restaurant site project.
-- The table and column names are the shared contract in CLAUDE.md. Do not rename anything here
-- without telling Rebeka first, because the website conversation depends on them.
--
-- The lock has three layers, so one mistake alone cannot open the data:
--   1. Rights (GRANT): the anonymous role gets nothing. Logged-in users get only the rights the
--      dashboard needs. The nightly job gets only the rights the forecast needs.
--   2. Row level security on every table: a logged-in member sees only rows of a restaurant
--      they are a member of.
--   3. bookings and receipts have no rights and no policies for anyone but the nightly job.

-- ---------------------------------------------------------------------------------------------
-- 0. New tables are private until a migration says otherwise
-- ---------------------------------------------------------------------------------------------
-- Supabase used to hand every new table in "public" to the web roles automatically. Switch that
-- off, so a table that someone forgets to lock is unreachable instead of wide open.
alter default privileges for role postgres in schema public
  revoke all on tables from anon, authenticated, service_role;
alter default privileges for role postgres in schema public
  revoke all on sequences from anon, authenticated, service_role;
alter default privileges for role postgres in schema public
  revoke execute on functions from anon, authenticated, service_role;

-- ---------------------------------------------------------------------------------------------
-- 1. Tables
-- ---------------------------------------------------------------------------------------------

create table public.restaurants (
  id        uuid primary key default gen_random_uuid(),
  name      text not null,
  latitude  double precision not null check (latitude between -90 and 90),
  longitude double precision not null check (longitude between -180 and 180),
  timezone  text not null,
  seats     integer not null check (seats > 0)
);
comment on table public.restaurants is 'One row per restaurant. Its id is the restaurant_id used in every other table.';
comment on column public.restaurants.timezone is 'IANA name, for example Europe/Amsterdam.';

-- Who may see which restaurant. Rows are added by hand when a user is invited.
create table public.restaurant_members (
  user_id       uuid not null references auth.users (id) on delete cascade,
  restaurant_id uuid not null references public.restaurants (id) on delete cascade,
  primary key (user_id, restaurant_id)
);
create index restaurant_members_restaurant_id_idx on public.restaurant_members (restaurant_id);
comment on table public.restaurant_members is 'Links a login to a restaurant. Holds ids only, never names or emails.';

-- The manager's own rules that turn guests into staff.
-- Staff for a role = the larger of min_staff and guests / guests_per_staff, rounded up.
create table public.staffing_rules (
  restaurant_id    uuid not null references public.restaurants (id) on delete cascade,
  role             text not null check (role in ('server', 'cook')),
  guests_per_staff integer not null check (guests_per_staff > 0),
  min_staff        integer not null default 1 check (min_staff >= 0),
  primary key (restaurant_id, role)
);
comment on table public.staffing_rules is 'Guests per staff member and the minimum crew, per role.';
comment on column public.staffing_rules.min_staff is 'The crew that is always there, whatever the forecast says.';

-- One row per restaurant and day. The primary key is what makes loading the same day twice
-- an update instead of a duplicate.
create table public.daily_weather (
  restaurant_id  uuid not null references public.restaurants (id) on delete cascade,
  date           date not null,
  temp_max       numeric(4, 1),
  rain_mm        numeric(5, 1) check (rain_mm >= 0),
  wind_max       numeric(5, 1) check (wind_max >= 0),
  sunshine_hours numeric(4, 1) check (sunshine_hours between 0 and 24),
  is_forecast    boolean not null default false,
  primary key (restaurant_id, date)
);
comment on table public.daily_weather is 'Daily weather at the restaurant: measured history and the forecast for the coming days.';
comment on column public.daily_weather.temp_max is 'Highest temperature of the day in degrees Celsius.';
comment on column public.daily_weather.rain_mm is 'Total precipitation of the day in millimetres.';
comment on column public.daily_weather.wind_max is 'Highest wind speed of the day in km/h.';
comment on column public.daily_weather.sunshine_hours is 'Hours of sunshine that day.';
comment on column public.daily_weather.is_forecast is 'true = a forecast that will still change, false = measured.';

-- Nightly job only. No names, phone numbers or emails: a booking is a time, a size and a table.
create table public.bookings (
  id            uuid primary key default gen_random_uuid(),
  restaurant_id uuid not null references public.restaurants (id) on delete cascade,
  visit_date    date not null,
  visit_time    time not null,
  party_size    integer not null check (party_size > 0),
  table_no      text,
  created_at    timestamptz not null,
  status        text not null default 'booked'
                check (status in ('booked', 'completed', 'no_show', 'cancelled'))
);
create index bookings_restaurant_visit_date_idx on public.bookings (restaurant_id, visit_date);
comment on table public.bookings is 'Reservations. Nightly job only. Never store who booked.';
comment on column public.bookings.id is 'Importers set this from the source row, so importing the same file twice does not create duplicates.';
comment on column public.bookings.visit_date is 'The service day: the day the shift started, also for arrivals after midnight.';
comment on column public.bookings.visit_time is 'Local time at the restaurant.';
comment on column public.bookings.created_at is 'When the booking was made. The forecast uses it to know what was already booked N days ahead.';

-- Nightly job only. What actually happened: one row per paid table.
create table public.receipts (
  id            uuid primary key default gen_random_uuid(),
  restaurant_id uuid not null references public.restaurants (id) on delete cascade,
  opened_at     timestamptz not null,
  closed_at     timestamptz,
  table_no      text,
  guests        integer not null check (guests >= 0),
  total         numeric(10, 2) not null,
  check (closed_at is null or closed_at >= opened_at)
);
create index receipts_restaurant_opened_at_idx on public.receipts (restaurant_id, opened_at);
comment on table public.receipts is 'Till receipts. Nightly job only. Never store who paid or who served.';
comment on column public.receipts.total is 'Amount in euros.';

-- Written by the nightly job, read by the dashboard.
create table public.forecasts (
  restaurant_id    uuid not null references public.restaurants (id) on delete cascade,
  date             date not null,
  shift            text not null default 'dinner' check (shift = 'dinner'),
  predicted_guests integer not null check (predicted_guests >= 0),
  servers          integer not null check (servers >= 0),
  cooks            integer not null check (cooks >= 0),
  model            text not null,
  created_at       timestamptz not null default now(),
  primary key (restaurant_id, date, shift)
);
comment on table public.forecasts is 'One row per restaurant, date and shift. The nightly job replaces it every night.';
comment on column public.forecasts.model is 'Which method produced the row, for example placeholder, baseline or lightgbm.';

-- Written by the manager on the dashboard. The nightly job has no right to write here.
create table public.forecast_overrides (
  restaurant_id uuid not null references public.restaurants (id) on delete cascade,
  date          date not null,
  shift         text not null default 'dinner' check (shift = 'dinner'),
  servers       integer check (servers >= 0),
  cooks         integer check (cooks >= 0),
  note          text,
  updated_by    uuid references auth.users (id) on delete set null,
  updated_at    timestamptz not null default now(),
  primary key (restaurant_id, date, shift)
);
create index forecast_overrides_updated_by_idx on public.forecast_overrides (updated_by);
comment on table public.forecast_overrides is 'The manager''s own staff numbers for a day. They win over the forecast and the nightly job never touches them.';
comment on column public.forecast_overrides.servers is 'Empty means: keep the forecast''s number.';
comment on column public.forecast_overrides.cooks is 'Empty means: keep the forecast''s number.';
comment on column public.forecast_overrides.updated_by is 'Filled by the database with the id of the logged-in user.';

-- The database, not the browser, records who changed an override and when.
create function public.stamp_forecast_override()
returns trigger
language plpgsql
security invoker
set search_path = ''
as $$
begin
  new.updated_by := (select auth.uid());
  new.updated_at := now();
  return new;
end;
$$;
revoke all on function public.stamp_forecast_override() from public, anon, authenticated, service_role;

create trigger forecast_overrides_stamp
  before insert or update on public.forecast_overrides
  for each row execute function public.stamp_forecast_override();

-- ---------------------------------------------------------------------------------------------
-- 2. Rights: start from nothing, then give each role exactly what it needs
-- ---------------------------------------------------------------------------------------------

revoke all on table
  public.restaurants,
  public.restaurant_members,
  public.staffing_rules,
  public.daily_weather,
  public.bookings,
  public.receipts,
  public.forecasts,
  public.forecast_overrides
from public, anon, authenticated, service_role;

-- anon (a visitor who is not logged in): nothing. The public website needs no table.

-- authenticated (a logged-in dashboard user). Row level security below narrows this further
-- to the user's own restaurant.
grant select on table
  public.restaurants,
  public.restaurant_members,
  public.staffing_rules,
  public.daily_weather,
  public.forecasts
to authenticated;
grant select, insert, update, delete on table public.forecast_overrides to authenticated;

-- service_role (the nightly job, which uses the secret key).
grant select on table
  public.restaurants,
  public.staffing_rules
to service_role;
grant select, insert, update, delete on table
  public.daily_weather,
  public.bookings,
  public.receipts,
  public.forecasts
to service_role;
-- Read only: the nightly job can look at overrides but can never overwrite one.
grant select on table public.forecast_overrides to service_role;

-- ---------------------------------------------------------------------------------------------
-- 3. Row level security on every table
-- ---------------------------------------------------------------------------------------------

alter table public.restaurants        enable row level security;
alter table public.restaurant_members enable row level security;
alter table public.staffing_rules     enable row level security;
alter table public.daily_weather      enable row level security;
alter table public.bookings           enable row level security;
alter table public.receipts           enable row level security;
alter table public.forecasts          enable row level security;
alter table public.forecast_overrides enable row level security;

-- A user sees only their own membership rows. Every other policy asks this table
-- "which restaurants is the logged-in user a member of?".
create policy "users read their own memberships"
  on public.restaurant_members
  for select
  to authenticated
  using (user_id = (select auth.uid()));

create policy "members read their own restaurant"
  on public.restaurants
  for select
  to authenticated
  using (
    id in (
      select m.restaurant_id from public.restaurant_members m
      where m.user_id = (select auth.uid())
    )
  );

create policy "members read their restaurant's staffing rules"
  on public.staffing_rules
  for select
  to authenticated
  using (
    restaurant_id in (
      select m.restaurant_id from public.restaurant_members m
      where m.user_id = (select auth.uid())
    )
  );

create policy "members read their restaurant's weather"
  on public.daily_weather
  for select
  to authenticated
  using (
    restaurant_id in (
      select m.restaurant_id from public.restaurant_members m
      where m.user_id = (select auth.uid())
    )
  );

create policy "members read their restaurant's forecasts"
  on public.forecasts
  for select
  to authenticated
  using (
    restaurant_id in (
      select m.restaurant_id from public.restaurant_members m
      where m.user_id = (select auth.uid())
    )
  );

-- "using" decides which existing rows a member may read, change or delete.
-- "with check" decides which rows a member may write, so an override can never be
-- saved for, or moved to, someone else's restaurant.
create policy "members read and write their restaurant's overrides"
  on public.forecast_overrides
  for all
  to authenticated
  using (
    restaurant_id in (
      select m.restaurant_id from public.restaurant_members m
      where m.user_id = (select auth.uid())
    )
  )
  with check (
    restaurant_id in (
      select m.restaurant_id from public.restaurant_members m
      where m.user_id = (select auth.uid())
    )
  );

-- bookings and receipts: row level security is on and there is deliberately no policy.
-- With no rights and no policy, only the nightly job (service_role) can reach them.
