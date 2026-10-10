// Everything the dashboard asks of the database, in one place.
// Reads: restaurants, forecasts, daily_weather, forecast_overrides.
// Writes: forecast_overrides only. Table and column names are the shared contract.
// Row level security decides which rows come back; these calls only work with a login.

import { supabase } from './supabase';
import {
  addDays,
  DAYS_SHOWN,
  type ForecastRow,
  type OverrideAction,
  type OverrideRow,
  type Restaurant,
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

const OVERRIDE_COLUMNS = 'date, shift, servers, cooks, note, updated_at';

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
};

/**
 * Forecast, weather and overrides from `from` (YYYY-MM-DD) for 14 days plus
 * one. The extra day covers the small hours, when the list may start at
 * either yesterday or today (see firstDayShown).
 */
export async function fetchWindow(restaurantId: string, from: string): Promise<ForecastWindow> {
  const last = addDays(from, DAYS_SHOWN);
  const [forecasts, weather, overrides] = await Promise.all([
    supabase
      .from('forecasts')
      .select('date, shift, predicted_guests, servers, cooks, model, created_at')
      .eq('restaurant_id', restaurantId)
      .gte('date', from)
      .lte('date', last)
      .order('date'),
    supabase
      .from('daily_weather')
      .select('date, temp_max, rain_mm, wind_max, sunshine_hours, is_forecast')
      .eq('restaurant_id', restaurantId)
      .gte('date', from)
      .lte('date', last)
      .order('date'),
    supabase
      .from('forecast_overrides')
      .select(OVERRIDE_COLUMNS)
      .eq('restaurant_id', restaurantId)
      .gte('date', from)
      .lte('date', last)
      .order('date'),
  ]);
  for (const result of [forecasts, weather, overrides]) {
    if (result.error) fail(result.error, result.status);
  }
  return {
    forecasts: (forecasts.data ?? []) as ForecastRow[],
    weather: ((weather.data ?? []) as WeatherRow[]).map(cleanWeather),
    overrides: (overrides.data ?? []) as OverrideRow[],
  };
}

/**
 * Carry out what the manager decided for one day and shift.
 * Returns the stored override, or null when the override was removed.
 * Only restaurant_id, date, shift, servers, cooks and note are sent; the
 * database itself records who changed it and when.
 */
export async function applyOverride(
  restaurantId: string,
  date: string,
  shift: string,
  action: OverrideAction,
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
  const { data, error, status } = await supabase
    .from('forecast_overrides')
    .upsert(
      {
        restaurant_id: restaurantId,
        date,
        shift,
        servers: action.servers,
        cooks: action.cooks,
        note: action.note,
      },
      { onConflict: 'restaurant_id,date,shift' },
    )
    .select(OVERRIDE_COLUMNS)
    .single();
  if (error) fail(error, status);
  return data as OverrideRow;
}
