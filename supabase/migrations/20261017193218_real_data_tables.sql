-- Phase 1 of "real data in": three tables that let real, non-personal numbers replace the fake
-- history later. This migration only adds. Nothing the dashboard or the nightly job already
-- uses is renamed, changed or removed.
--
--   covers            TheFork's own aggregate export ("evolution of covers"): how many guests
--                     were booked per period, service, channel and offer. Numbers only.
--   rosters           the manager's planned staff per role per evening. COUNTS ONLY, never names.
--   forecast_reviews  the manager's end-of-day verdict on a forecast ("right", "too many",
--                     "too few", and how many guests really came). Written on the dashboard.
--
-- Same lock as everywhere else: the anonymous role gets nothing, a logged-in member sees only
-- their own restaurant's rows, and the nightly job gets exactly the rights it needs.
--
-- Who writes what:
--   covers and rosters are written by the nightly job's role (the two importers in forecast/).
--   The dashboard reads them.
--   forecast_reviews is written by the manager on the dashboard, like forecast_overrides. The
--   nightly job may read reviews, never write them.

-- ---------------------------------------------------------------------------------------------
-- 1. covers: TheFork's aggregate export, at any period size
-- ---------------------------------------------------------------------------------------------
-- One row per restaurant, period, service, channel and offer, exactly as TheFork exports it.
-- The period size is not fixed: a per-day row has period_start = period_end, a weekly row
-- starts on a Monday and ends on the Sunday, a monthly row starts on the 1st and ends on the
-- last day of the month. Importing the same export twice updates the rows, it never doubles them.
create table public.covers (
  restaurant_id      uuid not null references public.restaurants (id) on delete cascade,
  period_start       date not null,
  period_end         date not null,
  service            text not null default '',
  channel            text not null,
  offer              text not null default '',
  covers             integer not null check (covers >= 0),
  bookings           integer not null check (bookings >= 0),
  no_shows           integer not null check (no_shows >= 0),
  cancellations      integer not null check (cancellations >= 0),
  late_cancellations integer not null check (late_cancellations >= 0),
  source             text not null default 'thefork',
  imported_at        timestamptz not null default now(),
  primary key (restaurant_id, period_start, period_end, service, channel, offer),
  check (period_end >= period_start)
);
comment on table public.covers is
  'TheFork''s "evolution of covers" export: guests booked per period, service, channel and offer. Numbers only, no names.';
comment on column public.covers.period_start is
  'First day of the period. A per-day row has period_start = period_end; weekly rows start on a Monday; monthly rows start on the 1st.';
comment on column public.covers.period_end is 'Last day of the period (included).';
comment on column public.covers.service is
  'TheFork''s service label as exported, for example Di-zo, maandag or Maandag vanaf 10 augustus. Empty when the export leaves it empty.';
comment on column public.covers.channel is
  'Where the booking came from, as exported: Restaurant widgets, Offline, TheFork Network, TheFork Partners, TripAdvisor, ...';
comment on column public.covers.offer is 'The offer booked, for example Kerstmenu. Empty when the export says 0 (no offer).';
comment on column public.covers.covers is 'Guests booked in this period (TheFork calls a guest a cover).';
comment on column public.covers.bookings is 'Number of bookings in this period.';
comment on column public.covers.no_shows is 'Bookings whose guests never came.';
comment on column public.covers.cancellations is 'Bookings that were cancelled.';
comment on column public.covers.late_cancellations is 'Bookings cancelled shortly before the visit.';
comment on column public.covers.source is 'Which system the row came from. thefork for TheFork exports.';
comment on column public.covers.imported_at is 'When the importer wrote the row.';

-- ---------------------------------------------------------------------------------------------
-- 2. rosters: the manager's planned staff per role per evening, counts only
-- ---------------------------------------------------------------------------------------------
-- The role words are the same as the staff columns of forecasts, so a roster row and a forecast
-- row can be laid next to each other: W floor = servers, B bar = bar_staff, R runner = runners,
-- F food = food_staff, kitchen = cooks. A row says how many people were planned, never who.
create table public.rosters (
  restaurant_id uuid not null references public.restaurants (id) on delete cascade,
  date          date not null,
  shift         text not null default 'dinner' check (shift = 'dinner'),
  role          text not null check (role in ('servers', 'bar_staff', 'runners', 'food_staff', 'cooks')),
  planned_count integer not null check (planned_count >= 0),
  source        text not null default 'manual',
  imported_at   timestamptz not null default now(),
  primary key (restaurant_id, date, shift, role)
);
comment on table public.rosters is
  'The manager''s planned staff per role per evening. Counts only: never a name, never who worked.';
comment on column public.rosters.role is
  'Same words as the forecasts columns: servers (W floor), bar_staff (B bar), runners (R runner), food_staff (F food), cooks (kitchen).';
comment on column public.rosters.planned_count is 'How many people were planned for this role that evening.';
comment on column public.rosters.source is 'Where the row came from: manual for a hand-made file.';
comment on column public.rosters.imported_at is 'When the importer wrote the row.';

-- ---------------------------------------------------------------------------------------------
-- 3. forecast_reviews: the manager's end-of-day verdict on a forecast
-- ---------------------------------------------------------------------------------------------
-- One row per restaurant, evening, shift and role. The 'all' row is the verdict on the evening
-- as a whole and is where actual_guests is meaningful; a role row is a verdict on one role.
-- Written by the manager on the dashboard, read by the nightly job to learn from later.
create table public.forecast_reviews (
  restaurant_id uuid not null references public.restaurants (id) on delete cascade,
  date          date not null,
  shift         text not null default 'dinner' check (shift = 'dinner'),
  role          text not null default 'all'
                check (role in ('all', 'servers', 'bar_staff', 'runners', 'food_staff', 'cooks')),
  actual_guests integer check (actual_guests >= 0),
  verdict       text check (verdict in ('right', 'too_many', 'too_few')),
  note          text,
  reviewed_by   uuid references auth.users (id) on delete set null,
  reviewed_at   timestamptz not null default now(),
  primary key (restaurant_id, date, shift, role)
);
create index forecast_reviews_reviewed_by_idx on public.forecast_reviews (reviewed_by);
comment on table public.forecast_reviews is
  'The manager''s verdict on a forecast after the evening: right, too many or too few staff, and how many guests came. The nightly job can read it, never write it.';
comment on column public.forecast_reviews.role is
  'all = the evening as a whole, or one of servers, bar_staff, runners, food_staff, cooks.';
comment on column public.forecast_reviews.actual_guests is 'How many guests really came. Meaningful on the all row. Empty means not counted.';
comment on column public.forecast_reviews.verdict is 'right, too_many or too_few staff. Empty means no verdict yet.';
comment on column public.forecast_reviews.note is 'A free remark about the evening. Never names: not of guests, not of staff.';
comment on column public.forecast_reviews.reviewed_by is 'Filled by the database with the id of the logged-in user.';
comment on column public.forecast_reviews.reviewed_at is 'Filled by the database with the moment of the last change.';

-- The database, not the browser, records who reviewed and when. Same as stamp_forecast_override.
create function public.stamp_forecast_review()
returns trigger
language plpgsql
security invoker
set search_path = ''
as $$
begin
  new.reviewed_by := (select auth.uid());
  new.reviewed_at := now();
  return new;
end;
$$;
revoke all on function public.stamp_forecast_review() from public, anon, authenticated, service_role;

create trigger forecast_reviews_stamp
  before insert or update on public.forecast_reviews
  for each row execute function public.stamp_forecast_review();

-- ---------------------------------------------------------------------------------------------
-- 4. Rights: start from nothing, then give each role exactly what it needs
-- ---------------------------------------------------------------------------------------------

revoke all on table
  public.covers,
  public.rosters,
  public.forecast_reviews
from public, anon, authenticated, service_role;

-- anon (a visitor who is not logged in): nothing.

-- authenticated (a logged-in dashboard user). Row level security below narrows this further
-- to the user's own restaurant.
grant select on table public.covers, public.rosters to authenticated;
grant select, insert, update, delete on table public.forecast_reviews to authenticated;

-- service_role (the nightly job and the importers, which use the secret key).
grant select, insert, update, delete on table public.covers, public.rosters to service_role;
-- Read only: the nightly job can learn from reviews but can never change one.
grant select on table public.forecast_reviews to service_role;

-- ---------------------------------------------------------------------------------------------
-- 5. Row level security on every table
-- ---------------------------------------------------------------------------------------------

alter table public.covers           enable row level security;
alter table public.rosters          enable row level security;
alter table public.forecast_reviews enable row level security;

create policy "members read their restaurant's covers"
  on public.covers
  for select
  to authenticated
  using (
    restaurant_id in (
      select m.restaurant_id from public.restaurant_members m
      where m.user_id = (select auth.uid())
    )
  );

create policy "members read their restaurant's rosters"
  on public.rosters
  for select
  to authenticated
  using (
    restaurant_id in (
      select m.restaurant_id from public.restaurant_members m
      where m.user_id = (select auth.uid())
    )
  );

-- Same shape as forecast_overrides: "using" decides which rows a member may read, change or
-- delete, "with check" decides which rows a member may write, so a review can never be saved
-- for, or moved to, someone else's restaurant.
create policy "members read and write their restaurant's reviews"
  on public.forecast_reviews
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
