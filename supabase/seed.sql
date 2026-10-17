-- Starting rows for the test project. Fake data only.
-- Safe to run again: it never changes a staffing rule that is already there and never touches a
-- forecast the nightly job has written. It only refreshes its own placeholder forecasts.

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

-- The manager's staffing table, as he gave it. One row per guest level:
--   100 guests: 3W 1B 1R 2F     W = floor (servers), B = bar, R = runner, F = food
--   120 guests: 4W 2B 2R 3F
--   180 guests: 6W 3B 2R 3F
--   250 guests: 6W 3B 3R 4F
--   300 guests: 6W 3B 3R 4F
-- A row applies from its guest number up to the next row; below 100 guests the first row applies.
-- Kitchen (cooks) is not on his roster: the fixed crew of 4 in every row.
insert into public.staffing_rules (restaurant_id, guests_from, servers, bar_staff, runners, food_staff, cooks)
values
  ('35f0d253-0e43-4e2f-8c23-d52b4ca159f7', 100, 3, 1, 1, 2, 4),
  ('35f0d253-0e43-4e2f-8c23-d52b4ca159f7', 120, 4, 2, 2, 3, 4),
  ('35f0d253-0e43-4e2f-8c23-d52b4ca159f7', 180, 6, 3, 2, 3, 4),
  ('35f0d253-0e43-4e2f-8c23-d52b4ca159f7', 250, 6, 3, 3, 4, 4),
  ('35f0d253-0e43-4e2f-8c23-d52b4ca159f7', 300, 6, 3, 3, 4, 4)
on conflict (restaurant_id, guests_from) do nothing;

-- 14 days of placeholder forecasts, starting today in the restaurant's own timezone, so the
-- dashboard has something to show before the nightly job has run. The guest numbers are the
-- manager's own weekly plan. Staff numbers come from the table above, exactly as the real
-- forecast does it. Rows the nightly job has written (model is not 'placeholder') are left alone.
insert into public.forecasts
  (restaurant_id, date, shift, predicted_guests, servers, bar_staff, runners, food_staff, cooks, model)
select
  r.id, d.date, 'dinner', g.guests,
  rule.servers, rule.bar_staff, rule.runners, rule.food_staff, rule.cooks,
  'placeholder'
from public.restaurants r
cross join lateral (
  select (now() at time zone r.timezone)::date + day_offset as date
  from generate_series(0, 13) as day_offset
) d
cross join lateral (
  select case extract(isodow from d.date)::integer
    when 1 then 100   -- Monday
    when 2 then 100
    when 3 then 100
    when 4 then 120
    when 5 then 250   -- Friday
    when 6 then 300   -- Saturday
    else 180          -- Sunday
  end as guests
) g
cross join lateral (
  -- The row with the highest guests_from that is not above the guest number;
  -- if every row is above it, the lowest row.
  select s.*
  from public.staffing_rules s
  where s.restaurant_id = r.id
  order by (s.guests_from <= g.guests) desc, abs(s.guests_from - g.guests)
  limit 1
) rule
where r.id = '35f0d253-0e43-4e2f-8c23-d52b4ca159f7'
on conflict (restaurant_id, date, shift) do update
  set predicted_guests = excluded.predicted_guests,
      servers          = excluded.servers,
      bar_staff        = excluded.bar_staff,
      runners          = excluded.runners,
      food_staff       = excluded.food_staff,
      cooks            = excluded.cooks
  where public.forecasts.model = 'placeholder';
