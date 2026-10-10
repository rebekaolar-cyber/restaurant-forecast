-- Proves the lock. Run it as the database owner (postgres), on Supabase or locally, after
-- every change to the schema.
--
-- It changes nothing: every row it inserts is rolled back before it finishes.
--
-- How it works: it creates two temporary restaurants, A and B, with one row in every table
-- each, and three temporary logins: a member of A, a member of B, and an outsider who is a
-- member of nothing. Then it becomes each kind of visitor in turn, exactly the way the web API
-- does it (same database role, same login token fields), tries to read and write, and records
-- what happened. The last statement prints one line per attempt with PASS or FAIL.

do $test$
declare
  results   jsonb := '[]'::jsonb;
  rest_a    uuid := gen_random_uuid();
  rest_b    uuid := gen_random_uuid();
  member_a  uuid := gen_random_uuid();
  member_b  uuid := gen_random_uuid();
  outsider  uuid := gen_random_uuid();
  tables    text[] := array[
    'restaurants', 'restaurant_members', 'staffing_rules', 'daily_weather',
    'bookings', 'receipts', 'forecasts', 'forecast_overrides'
  ];
  job_only  text[] := array['bookings', 'receipts'];
  persona   record;
  step      record;
  t         text;
  n_all     bigint;
  n_foreign bigint;
  n_changed bigint;
  expected  text;
  got       text;
begin
  -- Fail early if a table exists that this test does not know about.
  select string_agg(c.relname, ', ') into t
  from pg_class c
  where c.relnamespace = 'public'::regnamespace
    and c.relkind in ('r', 'p', 'v', 'm')
    and c.relname <> all (tables);
  if t is not null then
    raise exception 'Not covered by the lock test, add it to rls_lock.sql: %', t;
  end if;

  begin
    -- ---------------------------------------------------------------------------------------
    -- Temporary rows (rolled back at the end of this block)
    -- ---------------------------------------------------------------------------------------
    insert into auth.users (id, instance_id, aud, role)
    values
      (member_a, '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated'),
      (member_b, '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated'),
      (outsider, '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated');

    insert into public.restaurants (id, name, latitude, longitude, timezone, seats)
    values (rest_a, 'Lock test A', 0, 0, 'UTC', 10), (rest_b, 'Lock test B', 0, 0, 'UTC', 10);

    insert into public.restaurant_members (user_id, restaurant_id)
    values (member_a, rest_a), (member_b, rest_b);

    insert into public.staffing_rules (restaurant_id, role, guests_per_staff, min_staff)
    values (rest_a, 'server', 20, 1), (rest_b, 'server', 20, 1);

    insert into public.daily_weather (restaurant_id, date, temp_max)
    values (rest_a, '2099-01-01', 10), (rest_b, '2099-01-01', 10);

    insert into public.bookings (restaurant_id, visit_date, visit_time, party_size, created_at)
    values (rest_a, '2099-01-01', '18:00', 2, now()), (rest_b, '2099-01-01', '18:00', 2, now());

    insert into public.receipts (restaurant_id, opened_at, guests, total)
    values (rest_a, now(), 2, 50), (rest_b, now(), 2, 50);

    insert into public.forecasts (restaurant_id, date, predicted_guests, servers, cooks, model)
    values (rest_a, '2099-01-01', 10, 1, 1, 'lock-test'), (rest_b, '2099-01-01', 10, 1, 1, 'lock-test');

    insert into public.forecast_overrides (restaurant_id, date, servers, cooks)
    values (rest_a, '2099-01-01', 1, 1), (rest_b, '2099-01-01', 1, 1);

    -- ---------------------------------------------------------------------------------------
    -- Part 1: what can each visitor READ, in every table?
    -- ---------------------------------------------------------------------------------------
    for persona in
      select * from (values
        ('1 anonymous visitor',            'anon',          null::uuid, null::uuid),
        ('2 logged in, not a member',      'authenticated', outsider,   null::uuid),
        ('3 member of another restaurant', 'authenticated', member_b,   rest_b),
        ('4 member (control)',             'authenticated', member_a,   rest_a)
      ) as p (who, db_role, user_id, home)
    loop
      perform set_config(
        'request.jwt.claims',
        jsonb_strip_nulls(jsonb_build_object('role', persona.db_role, 'sub', persona.user_id))::text,
        true
      );
      perform set_config('role', persona.db_role, true);

      foreach t in array tables loop
        expected := case
          when persona.db_role = 'anon' then 'no access'
          when t = any (job_only)       then 'no access'
          when persona.home is null     then '0 rows'
          else '1 row, own restaurant only'
        end;
        begin
          execute format(
            'select count(*), count(*) filter (where %I is distinct from $1) from public.%I',
            case when t = 'restaurants' then 'id' else 'restaurant_id' end,
            t
          )
          into n_all, n_foreign
          using persona.home;
          got := case
            when n_all = 0 then '0 rows'
            when n_all = 1 and n_foreign = 0 then '1 row, own restaurant only'
            else format('%s rows, %s of another restaurant', n_all, n_foreign)
          end;
        exception when insufficient_privilege then
          got := 'no access';
        end;
        results := results || jsonb_build_object(
          'who', persona.who, 'attempt', 'read ' || t, 'expected', expected, 'got', got
        );
      end loop;

      perform set_config('role', 'none', true);
    end loop;

    -- ---------------------------------------------------------------------------------------
    -- Part 2: what can each visitor WRITE?
    -- ---------------------------------------------------------------------------------------
    for step in
      select * from (values
        ('1 anonymous visitor', 'anon', null::uuid,
         'add an override',
         format('insert into public.forecast_overrides (restaurant_id, date, servers, cooks) values (%L, ''2099-02-01'', 9, 9)', rest_a),
         'no access'),
        ('1 anonymous visitor', 'anon', null::uuid,
         'change forecasts',
         'update public.forecasts set servers = 99',
         'no access'),

        ('2 logged in, not a member', 'authenticated', outsider,
         'make themselves a member of restaurant A',
         format('insert into public.restaurant_members (user_id, restaurant_id) values (%L, %L)', outsider, rest_a),
         'no access'),
        ('2 logged in, not a member', 'authenticated', outsider,
         'add an override for restaurant A',
         format('insert into public.forecast_overrides (restaurant_id, date, servers, cooks) values (%L, ''2099-02-01'', 9, 9)', rest_a),
         'blocked by row level security'),
        ('2 logged in, not a member', 'authenticated', outsider,
         'change every override',
         'update public.forecast_overrides set servers = 99',
         '0 rows changed'),
        ('2 logged in, not a member', 'authenticated', outsider,
         'delete every override',
         'delete from public.forecast_overrides',
         '0 rows changed'),
        ('2 logged in, not a member', 'authenticated', outsider,
         'change forecasts',
         'update public.forecasts set servers = 99',
         'no access'),

        ('3 member of another restaurant', 'authenticated', member_b,
         'add an override for restaurant A',
         format('insert into public.forecast_overrides (restaurant_id, date, servers, cooks) values (%L, ''2099-02-01'', 9, 9)', rest_a),
         'blocked by row level security'),
        ('3 member of another restaurant', 'authenticated', member_b,
         'change restaurant A''s override',
         format('update public.forecast_overrides set servers = 99 where restaurant_id = %L', rest_a),
         '0 rows changed'),
        ('3 member of another restaurant', 'authenticated', member_b,
         'move their own override to restaurant A',
         format('update public.forecast_overrides set restaurant_id = %L, date = ''2099-03-01'' where restaurant_id = %L', rest_a, rest_b),
         'blocked by row level security'),
        ('3 member of another restaurant', 'authenticated', member_b,
         'delete restaurant A''s override',
         format('delete from public.forecast_overrides where restaurant_id = %L', rest_a),
         '0 rows changed'),

        ('4 member (control)', 'authenticated', member_a,
         'add an override for their own restaurant (pretending to be someone else)',
         format('insert into public.forecast_overrides (restaurant_id, date, servers, cooks, updated_by) values (%L, ''2099-02-01'', 3, 2, %L)', rest_a, member_b),
         '1 row changed'),
        ('4 member (control)', 'authenticated', member_a,
         'change that override, but only if the database recorded the real user',
         format('update public.forecast_overrides set servers = 4 where restaurant_id = %L and date = ''2099-02-01'' and updated_by = %L', rest_a, member_a),
         '1 row changed'),
        ('4 member (control)', 'authenticated', member_a,
         'delete that override',
         format('delete from public.forecast_overrides where restaurant_id = %L and date = ''2099-02-01''', rest_a),
         '1 row changed'),
        ('4 member (control)', 'authenticated', member_a,
         'change forecasts',
         'update public.forecasts set servers = 99',
         'no access'),
        ('4 member (control)', 'authenticated', member_a,
         'change staffing rules',
         'update public.staffing_rules set min_staff = 0',
         'no access'),
        ('4 member (control)', 'authenticated', member_a,
         'add a member to their own restaurant',
         format('insert into public.restaurant_members (user_id, restaurant_id) values (%L, %L)', outsider, rest_a),
         'no access'),

        ('5 nightly job (secret key)', 'service_role', null::uuid,
         'write a forecast',
         format('insert into public.forecasts (restaurant_id, date, predicted_guests, servers, cooks, model) values (%L, ''2099-01-01'', 20, 2, 1, ''lock-test'') on conflict (restaurant_id, date, shift) do update set predicted_guests = excluded.predicted_guests', rest_a),
         '1 row changed'),
        ('5 nightly job (secret key)', 'service_role', null::uuid,
         'write weather',
         format('insert into public.daily_weather (restaurant_id, date, temp_max) values (%L, ''2099-01-01'', 12) on conflict (restaurant_id, date) do update set temp_max = excluded.temp_max', rest_a),
         '1 row changed'),
        ('5 nightly job (secret key)', 'service_role', null::uuid,
         'write a booking',
         format('insert into public.bookings (restaurant_id, visit_date, visit_time, party_size, created_at) values (%L, ''2099-01-02'', ''19:00'', 4, now())', rest_a),
         '1 row changed'),
        ('5 nightly job (secret key)', 'service_role', null::uuid,
         'write a receipt',
         format('insert into public.receipts (restaurant_id, opened_at, guests, total) values (%L, now(), 4, 120)', rest_a),
         '1 row changed'),
        ('5 nightly job (secret key)', 'service_role', null::uuid,
         'change a manager''s override',
         'update public.forecast_overrides set servers = 0',
         'no access'),
        ('5 nightly job (secret key)', 'service_role', null::uuid,
         'add an override',
         format('insert into public.forecast_overrides (restaurant_id, date, servers, cooks) values (%L, ''2099-04-01'', 0, 0)', rest_a),
         'no access'),
        ('5 nightly job (secret key)', 'service_role', null::uuid,
         'delete overrides',
         'delete from public.forecast_overrides',
         'no access'),
        ('5 nightly job (secret key)', 'service_role', null::uuid,
         'change staffing rules',
         'update public.staffing_rules set min_staff = 0',
         'no access')
      ) as s (who, db_role, user_id, attempt, statement, expected)
    loop
      perform set_config(
        'request.jwt.claims',
        jsonb_strip_nulls(jsonb_build_object('role', step.db_role, 'sub', step.user_id))::text,
        true
      );
      perform set_config('role', step.db_role, true);

      begin
        execute step.statement;
        get diagnostics n_changed = row_count;
        got := format('%s row%s changed', n_changed, case when n_changed = 1 then '' else 's' end);
      exception when insufficient_privilege then
        got := case
          when sqlerrm like '%row-level security%' then 'blocked by row level security'
          else 'no access'
        end;
      end;
      results := results || jsonb_build_object(
        'who', step.who, 'attempt', step.attempt, 'expected', step.expected, 'got', got
      );

      perform set_config('role', 'none', true);
    end loop;

    -- Undo everything this block did, including the temporary rows.
    raise exception using errcode = 'LKTST', message = 'lock test finished, rolling back';
  exception when sqlstate 'LKTST' then
    null;
  end;

  -- Hand the results to the SELECT below.
  perform set_config('lock_test.results', results::text, false);
end
$test$;

select
  case when r ->> 'expected' = r ->> 'got' then 'PASS' else 'FAIL' end as result,
  r ->> 'who'      as who,
  r ->> 'attempt'  as attempt,
  r ->> 'expected' as expected,
  r ->> 'got'      as got
from jsonb_array_elements(current_setting('lock_test.results')::jsonb) with ordinality as x (r, n)
order by n;
