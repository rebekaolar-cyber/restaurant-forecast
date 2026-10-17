-- Contract change: the manager's real roster has four roles and a staffing rule by guest bands.
--
-- The roster:  W = floor staff, B = bar, R = runner, F = food. Kitchen is not on the roster.
-- In the database:
--   W floor   -> servers      (already there)
--   B bar     -> bar_staff    (new)
--   R runner  -> runners      (new)
--   F food    -> food_staff   (new)
--   kitchen   -> cooks        (already there; always the fixed kitchen crew)
--
-- For the dashboard this change only adds: nothing it reads or writes is renamed or removed.
-- This migration removes nothing at all. The old staffing rule table is set aside under a new
-- name instead of deleted, because deleting needs Rebeka's own confirmation.

-- ---------------------------------------------------------------------------------------------
-- 1. forecasts: three more roles
-- ---------------------------------------------------------------------------------------------
alter table public.forecasts
  add column bar_staff  integer check (bar_staff >= 0),
  add column runners    integer check (runners >= 0),
  add column food_staff integer check (food_staff >= 0);

-- Rows that are already there (the placeholders) get 0 for now; the seed rewrites them.
update public.forecasts
  set bar_staff = 0, runners = 0, food_staff = 0
  where bar_staff is null or runners is null or food_staff is null;

-- From here on a forecast that forgets a role is refused instead of saved half empty.
alter table public.forecasts
  alter column bar_staff  set not null,
  alter column runners    set not null,
  alter column food_staff set not null;

comment on column public.forecasts.servers is 'Floor staff (W on the roster).';
comment on column public.forecasts.bar_staff is 'Bar staff (B on the roster).';
comment on column public.forecasts.runners is 'Runners (R on the roster).';
comment on column public.forecasts.food_staff is 'Food staff (F on the roster).';
comment on column public.forecasts.cooks is 'Kitchen staff. Not on the roster: always the fixed kitchen crew from staffing_rules.';

-- ---------------------------------------------------------------------------------------------
-- 2. forecast_overrides: the same three, each may stay empty
-- ---------------------------------------------------------------------------------------------
alter table public.forecast_overrides
  add column bar_staff  integer check (bar_staff >= 0),
  add column runners    integer check (runners >= 0),
  add column food_staff integer check (food_staff >= 0);

comment on column public.forecast_overrides.bar_staff is 'Empty means: keep the forecast''s number.';
comment on column public.forecast_overrides.runners is 'Empty means: keep the forecast''s number.';
comment on column public.forecast_overrides.food_staff is 'Empty means: keep the forecast''s number.';

-- ---------------------------------------------------------------------------------------------
-- 3. staffing_rules: from "guests per staff member" to the manager's table by guest number
-- ---------------------------------------------------------------------------------------------
-- Set the old table aside. It held two default rows that were never the manager's own.
-- Nobody but the database owner can reach it any more.
alter table public.staffing_rules rename to staffing_rules_retired;
alter table public.staffing_rules_retired rename constraint staffing_rules_pkey to staffing_rules_retired_pkey;
revoke all on table public.staffing_rules_retired from public, anon, authenticated, service_role;
comment on table public.staffing_rules_retired is
  'Retired on 10 Oct 2026: the old "guests per staff member" rule. Used by nothing. Safe to delete.';

-- The new table: one row per guest level. A row applies from its guest number up to the next
-- row. With fewer guests than the first row, the first row applies: it is the smallest roster.
create table public.staffing_rules (
  restaurant_id uuid not null references public.restaurants (id) on delete cascade,
  guests_from   integer not null check (guests_from >= 0),
  servers       integer not null check (servers >= 0),
  bar_staff     integer not null check (bar_staff >= 0),
  runners       integer not null check (runners >= 0),
  food_staff    integer not null check (food_staff >= 0),
  cooks         integer not null check (cooks >= 0),
  primary key (restaurant_id, guests_from)
);
comment on table public.staffing_rules is 'The manager''s staffing table: one row per guest level, staff per role.';
comment on column public.staffing_rules.guests_from is 'The row applies from this many guests up to the next row.';
comment on column public.staffing_rules.cooks is 'Kitchen staff. The same fixed crew in every row.';

-- Same lock as before: nothing for visitors, members read their own restaurant's rows,
-- the nightly job reads.
revoke all on table public.staffing_rules from public, anon, authenticated, service_role;
grant select on table public.staffing_rules to authenticated;
grant select on table public.staffing_rules to service_role;

alter table public.staffing_rules enable row level security;

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
