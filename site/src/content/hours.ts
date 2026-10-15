// Opening hours, Monday first. Times are minutes after 00:00 on the day the
// evening starts, so a Friday that runs until 01:00 closes at 25 * 60.
// The public pages and the "open today" line both read from this one list.

export type DayHours = { open: number; close: number };

const h = (hours: number, minutes = 0) => hours * 60 + minutes;

export const week: DayHours[] = [
  { open: h(17), close: h(23) }, // maandag
  { open: h(17), close: h(23) }, // dinsdag
  { open: h(17), close: h(23) }, // woensdag
  { open: h(17), close: h(23) }, // donderdag
  { open: h(17), close: h(25) }, // vrijdag, tot 01:00
  { open: h(17), close: h(25) }, // zaterdag, tot 01:00
  { open: h(16), close: h(23) }, // zondag
];

/** Before this time of night we still count as "yesterday evening". */
export const DAY_ROLLOVER = h(4);

/** 1500 -> "01:00" */
export function clock(minutes: number): string {
  const m = ((minutes % 1440) + 1440) % 1440;
  const hh = String(Math.floor(m / 60)).padStart(2, '0');
  const mm = String(m % 60).padStart(2, '0');
  return `${hh}:${mm}`;
}

export function range(day: DayHours): string {
  return `${clock(day.open)} – ${clock(day.close)}`;
}

/** Axis for the hours strip: whole two-hour steps around the opening times. */
export function axis(step = 120) {
  const start = Math.floor(Math.min(...week.map((d) => d.open)) / step) * step;
  const end = Math.ceil(Math.max(...week.map((d) => d.close)) / step) * step;
  const ticks: number[] = [];
  for (let t = start; t <= end; t += step) ticks.push(t);
  return { start, end, ticks };
}

/** Runs of days with the same hours, for the short list in the footer. */
export function grouped(): { from: number; to: number; hours: DayHours }[] {
  const groups: { from: number; to: number; hours: DayHours }[] = [];
  week.forEach((day, i) => {
    const last = groups[groups.length - 1];
    if (last && last.hours.open === day.open && last.hours.close === day.close) last.to = i;
    else groups.push({ from: i, to: i, hours: day });
  });
  return groups;
}
