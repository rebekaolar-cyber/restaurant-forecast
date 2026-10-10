// Run with: npm test
import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  addDays,
  buildDays,
  dayLabel,
  firstDayShown,
  guestScale,
  isStale,
  lastUpdated,
  overrideAction,
  rainText,
  readStaff,
  serviceDay,
  temperatureText,
  whenAtRestaurant,
  type ForecastRow,
  type OverrideRow,
  type WeatherRow,
} from './forecast-days.ts';

const TZ = 'Europe/Amsterdam';
const forecast = (date: string, guests: number, servers: number, cooks: number): ForecastRow => ({
  date,
  shift: 'dinner',
  predicted_guests: guests,
  servers,
  cooks,
  model: 'placeholder',
  created_at: '2026-10-10T00:52:19.730666+00:00',
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
  const rows = [forecast('2026-10-10', 190, 10, 7), forecast('2026-10-12', 70, 4, 4)];
  const days = buildDays('2026-10-10', rows, [], []);
  assert.equal(days.length, 14);
  assert.equal(days[0]?.date, '2026-10-10');
  assert.equal(days[13]?.date, '2026-10-23');
  assert.equal(days[0]?.isToday, true);
  assert.equal(days[1]?.isToday, false);
  assert.equal(days[1]?.forecast, null);
  assert.equal(days[1]?.servers, null);
  assert.equal(days[2]?.forecast?.predicted_guests, 70);
  // Mondays start a week, but never the first line.
  assert.deepEqual(days.filter((d) => d.startsWeek).map((d) => d.date), ['2026-10-12', '2026-10-19']);
  assert.equal(buildDays('2026-10-12', rows, [], [])[0]?.startsWeek, false);
});

test('rows outside the fourteen days are ignored', () => {
  const days = buildDays('2026-10-10', [forecast('2026-10-09', 999, 9, 9), forecast('2026-10-24', 999, 9, 9)], [], []);
  assert.ok(days.every((d) => d.forecast === null));
});

test('the manager\'s number wins, per role, and the forecast stays visible', () => {
  const override: OverrideRow = { date: '2026-10-10', shift: 'dinner', servers: 12, cooks: null, note: 'Feest', updated_at: '2026-10-09T19:14:00Z' };
  const day = buildDays('2026-10-10', [forecast('2026-10-10', 190, 10, 7)], [], [override])[0]!;
  assert.equal(day.servers, 12);
  assert.equal(day.serversOverridden, true);
  assert.equal(day.forecast?.servers, 10);
  assert.equal(day.cooks, 7);
  assert.equal(day.cooksOverridden, false);
  assert.equal(day.override?.note, 'Feest');
});

test('an override of zero staff is a real number, not "empty"', () => {
  const override: OverrideRow = { date: '2026-10-10', shift: 'dinner', servers: 0, cooks: null, note: null, updated_at: '2026-10-09T19:14:00Z' };
  const day = buildDays('2026-10-10', [forecast('2026-10-10', 190, 10, 7)], [], [override])[0]!;
  assert.equal(day.servers, 0);
  assert.equal(day.serversOverridden, true);
});

test('weather is matched by date', () => {
  const weather: WeatherRow[] = [{ date: '2026-10-11', temp_max: 16.6, rain_mm: 2.44, wind_max: 28, sunshine_hours: 4, is_forecast: true }];
  const days = buildDays('2026-10-10', [], weather, []);
  assert.equal(days[0]?.weather, null);
  assert.equal(days[1]?.weather?.temp_max, 16.6);
});

test('saving: only a changed number is pinned', () => {
  const f = forecast('2026-10-10', 190, 10, 7);
  assert.deepEqual(overrideAction({ servers: 12, cooks: 7, note: '' }, f), { kind: 'save', servers: 12, cooks: null, note: null });
  assert.deepEqual(overrideAction({ servers: 10, cooks: 5, note: '  Rustig  ' }, f), { kind: 'save', servers: null, cooks: 5, note: 'Rustig' });
  // A note alone is worth keeping.
  assert.deepEqual(overrideAction({ servers: 10, cooks: 7, note: 'Voetbal op tv' }, f), { kind: 'save', servers: null, cooks: null, note: 'Voetbal op tv' });
  // Zero is a number.
  assert.deepEqual(overrideAction({ servers: 0, cooks: null, note: '' }, f), { kind: 'save', servers: 0, cooks: null, note: null });
});

test('saving: nothing changed means there is no override', () => {
  const f = forecast('2026-10-10', 190, 10, 7);
  assert.deepEqual(overrideAction({ servers: 10, cooks: 7, note: '   ' }, f), { kind: 'remove' });
  assert.deepEqual(overrideAction({ servers: null, cooks: null, note: '' }, f), { kind: 'remove' });
  // Without a forecast every number typed is the manager's own.
  assert.deepEqual(overrideAction({ servers: 4, cooks: null, note: '' }, null), { kind: 'save', servers: 4, cooks: null, note: null });
});

test('saving: a long note is cut to the limit', () => {
  const action = overrideAction({ servers: null, cooks: null, note: 'x'.repeat(500) }, null);
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
  const rows = [forecast('2026-10-10', 1, 1, 1), { ...forecast('2026-10-11', 1, 1, 1), created_at: '2026-10-10T01:10:00+00:00' }];
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
  const days = buildDays('2026-10-10', [forecast('2026-10-10', 190, 10, 7), forecast('2026-10-11', 120, 6, 4)], [], []);
  assert.equal(guestScale(days), 200);
  assert.equal(guestScale(buildDays('2026-10-10', [forecast('2026-10-10', 70, 4, 4)], [], [])), 75);
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
