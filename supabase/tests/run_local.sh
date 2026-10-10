#!/usr/bin/env bash
# Starts a throwaway Postgres, applies every migration and the seed, and runs the lock test.
# Needs no network and no keys. Exits with an error if any check fails.
#
#   supabase/tests/run_local.sh
#
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
supabase_dir="$(cd "$here/.." && pwd)"

pg_bin="${PG_BIN:-$(ls -d /usr/lib/postgresql/*/bin 2>/dev/null | sort -V | tail -1)}"
if [ -z "$pg_bin" ] || [ ! -x "$pg_bin/initdb" ]; then
  echo "Postgres server programs not found. Set PG_BIN to the folder that holds initdb." >&2
  exit 1
fi

work="$(mktemp -d)"
port="${PGTEST_PORT:-54329}"

# Postgres refuses to run as root, so in a root shell the server runs as the postgres user.
as_server=()
if [ "$(id -u)" = "0" ]; then
  chown postgres "$work"
  as_server=(runuser -u postgres --)
fi

cleanup() {
  "${as_server[@]}" "$pg_bin/pg_ctl" -D "$work/data" -m immediate stop >/dev/null 2>&1 || true
  rm -rf "$work"
}
trap cleanup EXIT

"${as_server[@]}" "$pg_bin/initdb" -D "$work/data" -U postgres -A trust -E UTF8 >/dev/null
"${as_server[@]}" "$pg_bin/pg_ctl" -D "$work/data" -l "$work/server.log" -w \
  -o "-p $port -k $work -c listen_addresses=''" start >/dev/null

run_sql() {
  psql -X -q -v ON_ERROR_STOP=1 -h "$work" -p "$port" -U postgres -d postgres "$@"
}

echo "== stand-in for Supabase roles and auth"
run_sql -f "$here/local_stub.sql"

for migration in "$supabase_dir"/migrations/*.sql; do
  echo "== migration $(basename "$migration")"
  run_sql -f "$migration"
done

echo "== seed (twice, to prove it is safe to run again)"
run_sql -f "$supabase_dir/seed.sql"
run_sql -f "$supabase_dir/seed.sql"

echo "== starting rows"
run_sql -c "select (select count(*) from public.restaurants) as restaurants,
                   (select count(*) from public.staffing_rules) as staffing_rules,
                   (select count(*) from public.forecasts) as forecasts"

echo "== every table has row level security switched on"
unlocked="$(run_sql -At -c "select coalesce(string_agg(relname, ', '), '') from pg_class
  where relnamespace = 'public'::regnamespace and relkind in ('r', 'p') and not relrowsecurity")"
if [ -n "$unlocked" ]; then
  echo "FAIL: row level security is off on: $unlocked" >&2
  exit 1
fi
echo "ok"

echo "== lock test"
out="$(run_sql -f "$here/rls_lock.sql")"
echo "$out"

echo "== the lock test left nothing behind"
left="$(run_sql -At -c "select (select count(*) from public.restaurants) || ' restaurant, '
  || (select count(*) from public.forecasts) || ' forecasts, '
  || (select count(*) from public.forecast_overrides) || ' overrides, '
  || (select count(*) from auth.users) || ' users'")"
echo "$left"
if [ "$left" != "1 restaurant, 14 forecasts, 0 overrides, 0 users" ]; then
  echo "FAIL: the lock test changed the data" >&2
  exit 1
fi

passes="$(grep -c '^ PASS' <<<"$out" || true)"
fails="$(grep -c '^ FAIL' <<<"$out" || true)"
echo
echo "$passes passed, $fails failed"
if [ "$fails" != "0" ] || [ "$passes" = "0" ]; then
  exit 1
fi
