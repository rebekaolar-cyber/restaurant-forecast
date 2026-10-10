// Everything the dashboard asks of the database, in one place.
// Reads: restaurants, forecasts, daily_weather, forecast_overrides.
// Writes: forecast_overrides only. Table and column names are the shared contract.
// Row level security decides which rows come back; these calls only work with a login.

import { supabase } from './supabase';
import {
  addDays,
  DAYS_SHOWN,
  ROLES,
  ROLES_BEFORE_ROSTER_COLUMNS,
  type ForecastRow,
  type OverrideAction,
  type OverrideRow,
  type Restaurant,
  type Role,
  type WeatherRow,
} from './forecast-days';

/** Why a request failed, in the three ways the screen treats differently. */
export class DataError extends Error {
  constructor(
    public readonly kind: 'login-ended' | 'offline' | 'refused',
    detail = '',
  ) {
    super(detail || kind);
    this.name = 'DataError';
  }
}

type Failure = { message?: string; code?: string } | null;

function fail(error: Failure, status: number): never {
  // 401: the login is no longer valid. 0 or a fetch error: no connection.
  if (status === 401) throw new DataError('login-ended');
  const message = error?.message ?? '';
  if (status === 0 || /failed to fetch|networkerror|load failed|fetch failed/i.test(message)) {
    throw new DataError('offline', message);
  }
  throw new DataError('refused', message);
}

// The bar, runner and food columns were added to the contract later. Until
// the database has them, asking for them fails with Postgres error 42703
// ("column does not exist"). In that case ask again without them, and the
// dashboard shows only the roles the database knows.
const ROSTER_COLUMNS = 'bar_staff, runners, food_staff';
const COLUMN_MISSING = '42703';

const forecastColumns = (roster: boolean) =>
  `date, shift, predicted_guests, servers, ${roster ? `${ROSTER_COLUMNS}, ` : ''}cooks, model, created_at`;
const overrideColumns = (roster: boolean) =>
  `date, shift, servers, ${roster ? `${ROSTER_COLUMNS}, ` : ''}note, updated_at`;

type Answer = { data: unknown; error: Failure; status: number };

/** Runs a read with the roster columns, and once more without them if the database lacks them. */
async function readWithRoster<Row>(
  run: (roster: boolean) => PromiseLike<Answer>,
): Promise<{ rows: Row[]; roster: boolean }> {
  let roster = true;
  let answer = await run(roster);
  if (answer.error?.code === COLUMN_MISSING) {
    roster = false;
    answer = await run(roster);
  }
  if (answer.error) fail(answer.error, answer.status);
  return { rows: (answer.data ?? []) as Row[], roster };
}

/** The restaurant this login belongs to, or null when it is not linked to one yet. */
export async function fetchRestaurant(): Promise<Restaurant | null> {
  const { data, error, status } = await supabase
    .from('restaurants')
    .select('id, name, timezone')
    .limit(1);
  if (error) fail(error, status);
  return ((data ?? [])[0] as Restaurant | undefined) ?? null;
}

/** Decimal columns can arrive as text ("16.6"); make sure they are numbers. */
function cleanWeather(row: WeatherRow): WeatherRow {
  const number = (value: unknown) => {
    if (value == null || value === '') return null;
    const n = Number(value);
    return Number.isFinite(n) ? n : null;
  };
  return {
    ...row,
    temp_max: number(row.temp_max),
    rain_mm: number(row.rain_mm),
    wind_max: number(row.wind_max),
    sunshine_hours: number(row.sunshine_hours),
  };
}

export type ForecastWindow = {
  forecasts: ForecastRow[];
  weather: WeatherRow[];
  overrides: OverrideRow[];
  /** The roster roles this database can show and store, in roster order. */
  roles: readonly Role[];
};

/**
 * Forecast, weather and overrides from `from` (YYYY-MM-DD) for 14 days plus
 * one. The extra day covers the small hours, when the list may start at
 * either yesterday or today (see firstDayShown).
 */
export async function fetchWindow(restaurantId: string, from: string): Promise<ForecastWindow> {
  const last = addDays(from, DAYS_SHOWN);
  const [forecasts, weather, overrides] = await Promise.all([
    readWithRoster<ForecastRow>((roster) =>
      supabase
        .from('forecasts')
        .select(forecastColumns(roster))
        .eq('restaurant_id', restaurantId)
        .gte('date', from)
        .lte('date', last)
        .order('date'),
    ),
    supabase
      .from('daily_weather')
      .select('date, temp_max, rain_mm, wind_max, sunshine_hours, is_forecast')
      .eq('restaurant_id', restaurantId)
      .gte('date', from)
      .lte('date', last)
      .order('date'),
    readWithRoster<OverrideRow>((roster) =>
      supabase
        .from('forecast_overrides')
        .select(overrideColumns(roster))
        .eq('restaurant_id', restaurantId)
        .gte('date', from)
        .lte('date', last)
        .order('date'),
    ),
  ]);
  if (weather.error) fail(weather.error, weather.status);
  return {
    forecasts: forecasts.rows,
    weather: ((weather.data ?? []) as WeatherRow[]).map(cleanWeather),
    overrides: overrides.rows,
    // Both tables must have the new columns before the dashboard offers them.
    roles: forecasts.roster && overrides.roster ? ROLES : ROLES_BEFORE_ROSTER_COLUMNS,
  };
}

/**
 * Carry out what the manager decided for one day and shift.
 * Returns the stored override, or null when the override was removed.
 * Only restaurant_id, date, shift, the roster roles, cooks and note are sent;
 * the database itself records who changed it and when. `cooks` is always
 * sent empty: the kitchen is a fixed crew and is never overridden from here.
 */
export async function applyOverride(
  restaurantId: string,
  date: string,
  shift: string,
  action: OverrideAction,
  roles: readonly Role[],
): Promise<OverrideRow | null> {
  if (action.kind === 'remove') {
    const { error, status } = await supabase
      .from('forecast_overrides')
      .delete()
      .eq('restaurant_id', restaurantId)
      .eq('date', date)
      .eq('shift', shift);
    if (error) fail(error, status);
    return null;
  }
  const staff: Partial<Record<Role, number | null>> = {};
  for (const role of roles) staff[role] = action.staff[role] ?? null;
  const { data, error, status } = await supabase
    .from('forecast_overrides')
    .upsert(
      { restaurant_id: restaurantId, date, shift, ...staff, cooks: null, note: action.note },
      { onConflict: 'restaurant_id,date,shift' },
    )
    .select(overrideColumns(roles.length > ROLES_BEFORE_ROSTER_COLUMNS.length))
    .single();
  if (error) fail(error, status);
  return data as unknown as OverrideRow;
}
