// Run with: npm test
import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  addDays,
  buildDays,
  dayLabel,
  firstDayShown,
  fixedKitchen,
  guestScale,
  isStale,
  lastUpdated,
  overrideAction,
  rainText,
  readStaff,
  ROLES,
  ROLES_BEFORE_ROSTER_COLUMNS,
  serviceDay,
  temperatureText,
  whenAtRestaurant,
  type ForecastRow,
  type OverrideRow,
  type WeatherRow,
} from './forecast-days.ts';

const TZ = 'Europe/Amsterdam';
// A forecast row with the roster roles: W servers, B bar, R runners, F food. Kitchen is 4.
const forecast = (
  date: string,
  guests: number,
  servers: number,
  bar_staff = 2,
  runners = 3,
  food_staff = 1,
): ForecastRow => ({
  date,
  shift: 'dinner',
  predicted_guests: guests,
  servers,
  bar_staff,
  runners,
  food_staff,
  cooks: 4,
  model: 'placeholder',
  created_at: '2026-10-10T00:52:19.730666+00:00',
});
const override = (date: string, values: Partial<OverrideRow>): OverrideRow => ({
  date,
  shift: 'dinner',
  servers: null,
  bar_staff: null,
  runners: null,
  food_staff: null,
  note: null,
  updated_at: '2026-10-09T19:14:00Z',
  ...values,
});

test('service day: the evening belongs to the day it started', () => {
  assert.equal(serviceDay(new Date('2026-10-10T12:00:00+02:00'), TZ), '2026-10-10');
  assert.equal(serviceDay(new Date('2026-10-10T23:59:00+02:00'), TZ), '2026-10-10');
  // Saturday 00:30: Friday's evening is still running.
  assert.equal(serviceDay(new Date('2026-10-10T00:30:00+02:00'), TZ), '2026-10-09');
  assert.equal(serviceDay(new Date('2026-10-10T03:59:00+02:00'), TZ), '2026-10-09');
  assert.equal(serviceDay(new Date('2026-10-10T04:00:00+02:00'), TZ), '2026-10-10');
});

test('service day: uses the restaurant clock, not the browser clock', () => {
  // 23:30 UTC on the 10th is already 01:30 on the 11th in Enschede: still the 10th's evening.
  assert.equal(serviceDay(new Date('2026-10-10T23:30:00Z'), TZ), '2026-10-10');
  // 03:00 UTC on the 11th is 05:00 in Enschede: the 11th.
  assert.equal(serviceDay(new Date('2026-10-11T03:00:00Z'), TZ), '2026-10-11');
  // Winter time and a month end.
  assert.equal(serviceDay(new Date('2026-12-01T00:30:00+01:00'), TZ), '2026-11-30');
  // A timezone the browser does not know falls back instead of crashing.
  assert.equal(serviceDay(new Date('2026-10-10T12:00:00+02:00'), 'Not/AZone'), '2026-10-10');
});

test('first day shown: yesterday only while its evening still has a forecast', () => {
  const friday = [{ date: '2026-10-09' }, { date: '2026-10-10' }];
  const afterNightlyRun = [{ date: '2026-10-10' }, { date: '2026-10-11' }];
  // Saturday 00:30, Friday's forecast still there: Friday is "today".
  assert.equal(firstDayShown(new Date('2026-10-10T00:30:00+02:00'), TZ, friday), '2026-10-09');
  // Saturday 03:10, the nightly run has replaced the forecast: start at Saturday.
  assert.equal(firstDayShown(new Date('2026-10-10T03:10:00+02:00'), TZ, afterNightlyRun), '2026-10-10');
  // During the day it is simply the day itself, with or without a forecast.
  assert.equal(firstDayShown(new Date('2026-10-10T12:00:00+02:00'), TZ, afterNightlyRun), '2026-10-10');
  assert.equal(firstDayShown(new Date('2026-10-10T12:00:00+02:00'), TZ, []), '2026-10-10');
  assert.equal(firstDayShown(new Date('2026-10-10T03:10:00+02:00'), TZ, []), '2026-10-10');
});

test('dates: adding days crosses months, years and the clock change', () => {
  assert.equal(addDays('2026-10-23', 1), '2026-10-24');
  assert.equal(addDays('2026-10-25', 1), '2026-10-26'); // the night the clocks go back
  assert.equal(addDays('2026-12-31', 1), '2027-01-01');
  assert.equal(addDays('2026-03-01', -1), '2026-02-28');
  assert.equal(dayLabel('2026-10-10'), 'Za 10 okt');
  assert.equal(dayLabel('2026-10-12'), 'Ma 12 okt');
});

test('fourteen days are always shown, also where a forecast is missing', () => {
  const rows = [forecast('2026-10-10', 300, 10), forecast('2026-10-12', 100, 4)];
  const days = buildDays('2026-10-10', rows, [], []);
  assert.equal(days.length, 14);
  assert.equal(days[0]?.date, '2026-10-10');
  assert.equal(days[13]?.date, '2026-10-23');
  assert.equal(days[0]?.isToday, true);
  assert.equal(days[1]?.isToday, false);
  assert.equal(days[1]?.forecast, null);
  assert.equal(days[1]?.staff.servers.value, null);
  assert.equal(days[1]?.kitchen, null);
  assert.equal(days[2]?.forecast?.predicted_guests, 100);
  // Mondays start a week, but never the first line.
  assert.deepEqual(days.filter((d) => d.startsWeek).map((d) => d.date), ['2026-10-12', '2026-10-19']);
  assert.equal(buildDays('2026-10-12', rows, [], [])[0]?.startsWeek, false);
});

test('rows outside the fourteen days are ignored', () => {
  const days = buildDays('2026-10-10', [forecast('2026-10-09', 999, 9), forecast('2026-10-24', 999, 9)], [], []);
  assert.ok(days.every((d) => d.forecast === null));
});

test('the four roster roles come out in roster order: W, B, R, F', () => {
  assert.deepEqual([...ROLES], ['servers', 'bar_staff', 'runners', 'food_staff']);
  const day = buildDays('2026-10-10', [forecast('2026-10-10', 300, 11, 3, 4, 2)], [], [])[0]!;
  assert.deepEqual(
    ROLES.map((role) => day.staff[role].value),
    [11, 3, 4, 2],
  );
  assert.ok(ROLES.every((role) => !day.staff[role].overridden));
});

test('the manager\'s number wins, per role, and the forecast stays visible', () => {
  const mine = override('2026-10-10', { servers: 12, runners: 5, note: 'Feest' });
  const day = buildDays('2026-10-10', [forecast('2026-10-10', 300, 10, 3, 4, 2)], [], [mine])[0]!;
  assert.deepEqual(day.staff.servers, { value: 12, forecast: 10, overridden: true });
  assert.deepEqual(day.staff.bar_staff, { value: 3, forecast: 3, overridden: false });
  assert.deepEqual(day.staff.runners, { value: 5, forecast: 4, overridden: true });
  assert.deepEqual(day.staff.food_staff, { value: 2, forecast: 2, overridden: false });
  assert.equal(day.override?.note, 'Feest');
});

test('an override of zero staff is a real number, not "empty"', () => {
  const day = buildDays('2026-10-10', [forecast('2026-10-10', 300, 10)], [], [override('2026-10-10', { bar_staff: 0 })])[0]!;
  assert.deepEqual(day.staff.bar_staff, { value: 0, forecast: 2, overridden: true });
});

test('the kitchen is the forecast\'s fixed crew and is never overridden', () => {
  const days = buildDays('2026-10-10', [forecast('2026-10-10', 300, 10), forecast('2026-10-11', 180, 7)], [], []);
  assert.equal(days[0]?.kitchen, 4);
  assert.equal(fixedKitchen(days), 4);
  // Different sizes on different days: there is no single fixed number to announce.
  const mixed = buildDays('2026-10-10', [forecast('2026-10-10', 300, 10), { ...forecast('2026-10-11', 180, 7), cooks: 6 }], [], []);
  assert.equal(fixedKitchen(mixed), null);
  assert.equal(fixedKitchen(buildDays('2026-10-10', [], [], [])), null);
});

test('a database without the bar, runner and food columns still works', () => {
  const old = { date: '2026-10-10', shift: 'dinner', predicted_guests: 190, servers: 10, cooks: 7, model: 'placeholder', created_at: '2026-10-10T00:52:19Z' };
  const day = buildDays('2026-10-10', [old], [], [])[0]!;
  assert.equal(day.staff.servers.value, 10);
  assert.equal(day.staff.bar_staff.value, null);
  assert.equal(day.kitchen, 7);
  // Only the roles the database knows are sent.
  assert.deepEqual(overrideAction({ staff: { servers: 12 }, note: '' }, old, ROLES_BEFORE_ROSTER_COLUMNS), { kind: 'save', staff: { servers: 12 }, note: null });
});

test('weather is matched by date', () => {
  const weather: WeatherRow[] = [{ date: '2026-10-11', temp_max: 16.6, rain_mm: 2.44, wind_max: 28, sunshine_hours: 4, is_forecast: true }];
  const days = buildDays('2026-10-10', [], weather, []);
  assert.equal(days[0]?.weather, null);
  assert.equal(days[1]?.weather?.temp_max, 16.6);
});

test('saving: only a changed number is pinned', () => {
  const f = forecast('2026-10-10', 300, 10, 3, 4, 2);
  const typed = { servers: 10, bar_staff: 3, runners: 4, food_staff: 2 };
  const empty = { servers: null, bar_staff: null, runners: null, food_staff: null };
  assert.deepEqual(overrideAction({ staff: { ...typed, servers: 12 }, note: '' }, f), { kind: 'save', staff: { ...empty, servers: 12 }, note: null });
  assert.deepEqual(overrideAction({ staff: { ...typed, bar_staff: 4, food_staff: 1 }, note: '  Rustig  ' }, f), { kind: 'save', staff: { ...empty, bar_staff: 4, food_staff: 1 }, note: 'Rustig' });
  // A note alone is worth keeping.
  assert.deepEqual(overrideAction({ staff: typed, note: 'Voetbal op tv' }, f), { kind: 'save', staff: empty, note: 'Voetbal op tv' });
  // Zero is a number.
  assert.deepEqual(overrideAction({ staff: { ...typed, runners: 0 }, note: '' }, f), { kind: 'save', staff: { ...empty, runners: 0 }, note: null });
});

test('saving: nothing changed means there is no override', () => {
  const f = forecast('2026-10-10', 300, 10, 3, 4, 2);
  assert.deepEqual(overrideAction({ staff: { servers: 10, bar_staff: 3, runners: 4, food_staff: 2 }, note: '   ' }, f), { kind: 'remove' });
  assert.deepEqual(overrideAction({ staff: {}, note: '' }, f), { kind: 'remove' });
  // Without a forecast every number typed is the manager's own.
  assert.deepEqual(overrideAction({ staff: { servers: 4 }, note: '' }, null), { kind: 'save', staff: { servers: 4, bar_staff: null, runners: null, food_staff: null }, note: null });
});

test('saving: a long note is cut to the limit', () => {
  const action = overrideAction({ staff: {}, note: 'x'.repeat(500) }, null);
  assert.equal(action.kind === 'save' && action.note?.length, 300);
});

test('staff field: empty, whole numbers 0 to 99, nothing else', () => {
  assert.deepEqual(readStaff(''), { ok: true, value: null });
  assert.deepEqual(readStaff('  '), { ok: true, value: null });
  assert.deepEqual(readStaff('0'), { ok: true, value: 0 });
  assert.deepEqual(readStaff(' 12 '), { ok: true, value: 12 });
  assert.deepEqual(readStaff('99'), { ok: true, value: 99 });
  for (const bad of ['100', '-1', '2.5', '2,5', 'twee', '1e1', '+3']) assert.deepEqual(readStaff(bad), { ok: false }, bad);
});

test('last update and staleness', () => {
  const rows = [forecast('2026-10-10', 1, 1), { ...forecast('2026-10-11', 1, 1), created_at: '2026-10-10T01:10:00+00:00' }];
  assert.equal(lastUpdated(rows), '2026-10-10T01:10:00+00:00');
  assert.equal(lastUpdated([]), null);
  assert.equal(isStale('2026-10-10T01:00:00Z', new Date('2026-10-11T12:00:00Z')), false); // 35 hours
  assert.equal(isStale('2026-10-10T01:00:00Z', new Date('2026-10-11T14:00:00Z')), true); // 37 hours
  assert.equal(isStale(null, new Date()), false);
});

test('"when" is told in the restaurant\'s time', () => {
  const now = new Date('2026-10-10T12:00:00+02:00');
  assert.deepEqual(whenAtRestaurant('2026-10-10T00:52:19Z', now, TZ), { day: 'today', dayText: 'za 10 okt', time: '02:52' });
  assert.equal(whenAtRestaurant('2026-10-09T01:00:00Z', now, TZ).day, 'yesterday');
  // 22:30 UTC on the 8th is 00:30 on the 9th in Enschede.
  assert.deepEqual(whenAtRestaurant('2026-10-08T22:30:00Z', now, TZ), { day: 'yesterday', dayText: 'vr 9 okt', time: '00:30' });
  assert.equal(whenAtRestaurant('2026-10-07T01:00:00Z', now, TZ).day, 'other');
});

test('guest scale and weather words', () => {
  const days = buildDays('2026-10-10', [forecast('2026-10-10', 190, 10), forecast('2026-10-11', 120, 6)], [], []);
  assert.equal(guestScale(days), 200);
  assert.equal(guestScale(buildDays('2026-10-10', [forecast('2026-10-10', 300, 11)], [], [])), 300);
  assert.equal(guestScale(buildDays('2026-10-10', [forecast('2026-10-10', 70, 4)], [], [])), 75);
  assert.equal(guestScale(buildDays('2026-10-10', [], [], [])), 50);
  assert.equal(temperatureText(16.6), '17°');
  assert.equal(temperatureText(-0.4), '0°');
  assert.equal(temperatureText(-3.6), '-4°');
  assert.equal(temperatureText(null), null);
  assert.equal(rainText(0), 'droog');
  assert.equal(rainText(0.04), 'droog');
  assert.equal(rainText(2.44), '2,4 mm');
  assert.equal(rainText(12.6), '13 mm');
  assert.equal(rainText(null), null);
});
