// The thinking part of the dashboard, kept free of the page and the database
// so it can be tested on its own (see forecast-days.test.ts).
//
// It answers: which 14 days do we show, what belongs to each day, which staff
// numbers count (the manager's or the forecast's), and what do we send to the
// database when the manager saves.

export const DAYS_SHOWN = 14;
/** Before this hour of the night we still count as yesterday's evening. */
export const ROLLOVER_HOUR = 4;
/** Older than this many hours and the nightly run has probably failed. */
export const STALE_AFTER_HOURS = 36;
export const MAX_STAFF = 99;
export const NOTE_MAX = 300;
const FALLBACK_TIMEZONE = 'Europe/Amsterdam';

// ---------- The roster ----------

/**
 * The roles on the manager's roster, in roster order: W, B, R, F.
 * The names are the column names in `forecasts` and `forecast_overrides`.
 * The kitchen (`cooks`) is not here: it is a fixed crew, shown but never
 * overridden from the dashboard.
 */
export const ROLES = ['servers', 'bar_staff', 'runners', 'food_staff'] as const;
export type Role = (typeof ROLES)[number];
/** What a database from before the bar, runner and food columns can offer. */
export const ROLES_BEFORE_ROSTER_COLUMNS: readonly Role[] = ['servers'];

// ---------- Rows as the database gives them (names are the shared contract) ----------

export type Restaurant = { id: string; name: string; timezone: string };

export type ForecastRow = {
  date: string;
  shift: string;
  predicted_guests: number;
  servers: number;
  bar_staff?: number | null;
  runners?: number | null;
  food_staff?: number | null;
  /** Kitchen: a fixed crew. */
  cooks: number;
  model: string;
  created_at: string;
};

export type WeatherRow = {
  date: string;
  temp_max: number | null;
  rain_mm: number | null;
  wind_max: number | null;
  sunshine_hours: number | null;
  is_forecast: boolean;
};

export type OverrideRow = {
  date: string;
  shift: string;
  servers: number | null;
  bar_staff?: number | null;
  runners?: number | null;
  food_staff?: number | null;
  note: string | null;
  updated_at: string;
};

/** One role on one day: the number that counts and where it came from. */
export type StaffCell = {
  /** The manager's number if set, otherwise the forecast's. */
  value: number | null;
  forecast: number | null;
  overridden: boolean;
};

/** One line on the dashboard: a day and a shift, with everything known about it. */
export type DayShift = {
  key: string;
  date: string;
  shift: string;
  isToday: boolean;
  /** True on a Monday (except the first line), to set weeks apart. */
  startsWeek: boolean;
  forecast: ForecastRow | null;
  weather: WeatherRow | null;
  override: OverrideRow | null;
  staff: Record<Role, StaffCell>;
  /** Kitchen crew from the forecast. Fixed: the dashboard never overrides it. */
  kitchen: number | null;
};

// ---------- Dates ----------

function safeTimeZone(timeZone: string): string {
  try {
    new Intl.DateTimeFormat('en', { timeZone });
    return timeZone;
  } catch {
    return FALLBACK_TIMEZONE;
  }
}

function toUtc(date: string): number {
  const [y, m, d] = date.split('-').map(Number);
  return Date.UTC(y ?? 1970, (m ?? 1) - 1, d ?? 1);
}

export function addDays(date: string, days: number): string {
  return new Date(toUtc(date) + days * 86_400_000).toISOString().slice(0, 10);
}

/** Calendar date and hour at the restaurant, wherever the browser is. */
function localParts(at: Date, timeZone: string): { date: string; hour: number } {
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: safeTimeZone(timeZone),
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    hourCycle: 'h23',
  }).formatToParts(at);
  const get = (type: string) => parts.find((p) => p.type === type)?.value ?? '';
  return { date: `${get('year')}-${get('month')}-${get('day')}`, hour: Number(get('hour')) };
}

/**
 * The day whose evening is "today" for the restaurant. Until 04:00 that is
 * still yesterday: a Friday that runs until 01:00 belongs to Friday.
 */
export function serviceDay(now: Date, timeZone: string): string {
  const { date, hour } = localParts(now, timeZone);
  return hour < ROLLOVER_HOUR ? addDays(date, -1) : date;
}

/** The plain calendar date at the restaurant. */
export function calendarDay(now: Date, timeZone: string): string {
  return localParts(now, timeZone).date;
}

/**
 * The first of the 14 days to show. Normally the service day. In the small
 * hours that is still yesterday, which is right while yesterday's evening has
 * a forecast line. Once the nightly run has replaced the forecast, yesterday
 * has nothing left to show, so the list starts at the new day instead.
 */
export function firstDayShown(now: Date, timeZone: string, forecasts: { date: string }[]): string {
  const service = serviceDay(now, timeZone);
  const calendar = calendarDay(now, timeZone);
  if (service !== calendar && !forecasts.some((f) => f.date === service)) return calendar;
  return service;
}

/** "Za 10 okt" */
export function dayLabel(date: string, locale = 'nl-NL'): string {
  const text = new Intl.DateTimeFormat(locale, {
    timeZone: 'UTC',
    weekday: 'short',
    day: 'numeric',
    month: 'short',
  })
    .format(new Date(toUtc(date)))
    .replace(/\./g, '');
  return text.charAt(0).toUpperCase() + text.slice(1);
}

/** "zaterdag 10 oktober", for screen readers and the edit panel. */
export function dayLabelLong(date: string, locale = 'nl-NL'): string {
  return new Intl.DateTimeFormat(locale, {
    timeZone: 'UTC',
    weekday: 'long',
    day: 'numeric',
    month: 'long',
  }).format(new Date(toUtc(date)));
}

/** Monday = 1 ... Sunday = 7 */
function weekday(date: string): number {
  return new Date(toUtc(date)).getUTCDay() || 7;
}

/**
 * When something happened, in the restaurant's own time:
 * { day: 'today' | 'yesterday' | 'other', dayText: 'wo 7 okt', time: '02:52' }
 */
export function whenAtRestaurant(
  timestamp: string,
  now: Date,
  timeZone: string,
  locale = 'nl-NL',
): { day: 'today' | 'yesterday' | 'other'; dayText: string; time: string } {
  const at = new Date(timestamp);
  const zone = safeTimeZone(timeZone);
  const date = localParts(at, zone).date;
  const today = localParts(now, zone).date;
  const time = new Intl.DateTimeFormat(locale, {
    timeZone: zone,
    hour: '2-digit',
    minute: '2-digit',
    hourCycle: 'h23',
  }).format(at);
  const day = date === today ? 'today' : date === addDays(today, -1) ? 'yesterday' : 'other';
  return { day, dayText: dayLabel(date, locale).toLowerCase(), time };
}

// ---------- Putting the days together ----------

/** Newest "created_at" among the forecast rows shown, or null when there are none. */
export function lastUpdated(forecasts: ForecastRow[]): string | null {
  return forecasts.reduce<string | null>(
    (latest, row) => (latest === null || row.created_at > latest ? row.created_at : latest),
    null,
  );
}

export function isStale(updatedAt: string | null, now: Date): boolean {
  if (!updatedAt) return false;
  return now.getTime() - new Date(updatedAt).getTime() > STALE_AFTER_HOURS * 3_600_000;
}

function merge(
  date: string,
  shift: string,
  today: string,
  first: boolean,
  forecast: ForecastRow | null,
  weather: WeatherRow | null,
  override: OverrideRow | null,
): DayShift {
  const staff = {} as Record<Role, StaffCell>;
  for (const role of ROLES) {
    const fromForecast = forecast?.[role] ?? null;
    const fromManager = override?.[role] ?? null;
    staff[role] = {
      value: fromManager ?? fromForecast,
      forecast: fromForecast,
      overridden: fromManager != null,
    };
  }
  return {
    key: `${date}|${shift}`,
    date,
    shift,
    isToday: date === today,
    startsWeek: !first && weekday(date) === 1,
    forecast,
    weather,
    override,
    staff,
    kitchen: forecast?.cooks ?? null,
  };
}

/**
 * The 14 days from today, each with its forecast, weather and override.
 * A day without a forecast still gets a line, so a gap is visible instead of
 * silently missing. Today the only shift is "dinner"; more shifts on a day
 * would each get their own line.
 */
export function buildDays(
  today: string,
  forecasts: ForecastRow[],
  weather: WeatherRow[],
  overrides: OverrideRow[],
  defaultShift = 'dinner',
): DayShift[] {
  const lines: DayShift[] = [];
  for (let i = 0; i < DAYS_SHOWN; i++) {
    const date = addDays(today, i);
    const dayWeather = weather.find((w) => w.date === date) ?? null;
    const shifts = new Set<string>();
    forecasts.filter((f) => f.date === date).forEach((f) => shifts.add(f.shift));
    overrides.filter((o) => o.date === date).forEach((o) => shifts.add(o.shift));
    if (shifts.size === 0) shifts.add(defaultShift);
    [...shifts].sort().forEach((shift) => {
      lines.push(
        merge(
          date,
          shift,
          today,
          lines.length === 0,
          forecasts.find((f) => f.date === date && f.shift === shift) ?? null,
          dayWeather,
          overrides.find((o) => o.date === date && o.shift === shift) ?? null,
        ),
      );
    });
  }
  return lines;
}

/**
 * The kitchen crew when it is the same on every day shown (the fixed crew),
 * or null when days differ or nothing is known.
 */
export function fixedKitchen(days: DayShift[]): number | null {
  const sizes = new Set(days.flatMap((d) => (d.kitchen == null ? [] : [d.kitchen])));
  return sizes.size === 1 ? [...sizes][0]! : null;
}

/** Top of the guests scale: the busiest evening shown, rounded up to a round number. */
export function guestScale(days: DayShift[]): number {
  const most = Math.max(0, ...days.map((d) => d.forecast?.predicted_guests ?? 0));
  if (most <= 0) return 50;
  const step = most <= 100 ? 25 : 50;
  return Math.ceil(most / step) * step;
}

// ---------- Saving ----------

export type StaffInput = { ok: true; value: number | null } | { ok: false };

/** Reads what was typed in a staff field: empty, or a whole number from 0 to 99. */
export function readStaff(text: string): StaffInput {
  const trimmed = text.trim();
  if (trimmed === '') return { ok: true, value: null };
  if (!/^\d{1,2}$/.test(trimmed)) return { ok: false };
  return { ok: true, value: Number(trimmed) };
}

export type StaffNumbers = Partial<Record<Role, number | null>>;
export type OverrideDraft = { staff: StaffNumbers; note: string };

export type OverrideAction =
  | { kind: 'remove' }
  | { kind: 'save'; staff: StaffNumbers; note: string | null };

/**
 * What to do with the manager's input, for the roles the database knows.
 * - A number equal to the forecast's is stored as "empty", which the database
 *   reads as "keep the forecast's number". Tomorrow's forecast can then move
 *   it again; only a number the manager really changed is pinned.
 * - Nothing changed and no note: there is no override, so remove the row.
 */
export function overrideAction(
  draft: OverrideDraft,
  forecast: ForecastRow | null,
  roles: readonly Role[] = ROLES,
): OverrideAction {
  const staff: StaffNumbers = {};
  let pinned = false;
  for (const role of roles) {
    const typed = draft.staff[role] ?? null;
    const changed = typed !== null && typed !== (forecast?.[role] ?? null);
    staff[role] = changed ? typed : null;
    pinned ||= changed;
  }
  const note = draft.note.trim().slice(0, NOTE_MAX) || null;
  if (!pinned && note === null) return { kind: 'remove' };
  return { kind: 'save', staff, note };
}

// ---------- Weather in words ----------

const comma = (n: number, digits: number) => n.toFixed(digits).replace('.', ',');

export function temperatureText(value: number | null): string | null {
  return value == null ? null : `${Math.round(value)}°`;
}

/** null = unknown, "droog" = no rain to speak of, otherwise millimetres. */
export function rainText(mm: number | null, dry = 'droog'): string | null {
  if (mm == null) return null;
  if (mm < 0.05) return dry;
  return `${mm < 10 ? comma(mm, 1) : String(Math.round(mm))} mm`;
}
