-- Starting rows for the test project. Fake data only.
-- Safe to run again: existing rows are left alone, so it never undoes corrected staffing
-- rules and never replaces a forecast the nightly job has written.

-- The one restaurant. The id is fixed so that tests and the importer can rely on it.
insert into public.restaurants (id, name, latitude, longitude, timezone, seats)
values (
  '35f0d253-0e43-4e2f-8c23-d52b4ca159f7',
  'Restaurant Habibi',
  52.2066,   -- Wethouder Beversstraat 185, Enschede
  6.8914,
  'Europe/Amsterdam',
  254
)
on conflict (id) do nothing;

-- Default staffing rules, to be corrected by the manager later.
-- 1 server per 20 guests, 1 cook per 30 guests.
-- min_staff is the fixed crew from CLAUDE.md: 2 service staff and 4 kitchen staff are there
-- on every open day, and the forecast never goes below that.
insert into public.staffing_rules (restaurant_id, role, guests_per_staff, min_staff)
values
  ('35f0d253-0e43-4e2f-8c23-d52b4ca159f7', 'server', 20, 2),
  ('35f0d253-0e43-4e2f-8c23-d52b4ca159f7', 'cook',   30, 4)
on conflict (restaurant_id, role) do nothing;

-- 14 days of placeholder forecasts, starting today in the restaurant's own timezone, so the
-- dashboard has something to show before the real forecast exists. The guest numbers are made
-- up per weekday. Staff numbers come from the rules above, exactly as the real forecast will
-- do it: the larger of min_staff and guests / guests_per_staff rounded up.
insert into public.forecasts (restaurant_id, date, shift, predicted_guests, servers, cooks, model)
select
  r.id,
  d.date,
  'dinner',
  g.guests,
  greatest(s.min_staff, ceil(g.guests::numeric / s.guests_per_staff))::integer,
  greatest(c.min_staff, ceil(g.guests::numeric / c.guests_per_staff))::integer,
  'placeholder'
from public.restaurants r
cross join lateral (
  select (now() at time zone r.timezone)::date + day_offset as date
  from generate_series(0, 13) as day_offset
) d
cross join lateral (
  select case extract(isodow from d.date)::integer
    when 1 then 70    -- Monday
    when 2 then 75
    when 3 then 85
    when 4 then 100
    when 5 then 170   -- Friday
    when 6 then 190   -- Saturday
    else 120          -- Sunday
  end as guests
) g
join public.staffing_rules s on s.restaurant_id = r.id and s.role = 'server'
join public.staffing_rules c on c.restaurant_id = r.id and c.role = 'cook'
where r.id = '35f0d253-0e43-4e2f-8c23-d52b4ca159f7'
on conflict (restaurant_id, date, shift) do nothing;
