// Marks today in the opening-hours list and fills in the "open today" line.
// Runs in the visitor's browser, reads the same hours as the pages, and sends
// nothing anywhere. Without JavaScript the pages simply show the full week.

import { week, clock, DAY_ROLLOVER } from '../content/hours';
import { statusText } from '../content/nl.status';

const WEEKDAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

function amsterdamNow(): { day: number; minutes: number } {
  // The restaurant's clock, wherever the visitor is.
  const parts = new Intl.DateTimeFormat('en-GB', {
    timeZone: 'Europe/Amsterdam',
    weekday: 'short',
    hour: '2-digit',
    minute: '2-digit',
    hourCycle: 'h23',
  }).formatToParts(new Date());
  const get = (type: string) => parts.find((p) => p.type === type)?.value ?? '';
  return {
    day: WEEKDAYS.indexOf(get('weekday')),
    minutes: Number(get('hour')) * 60 + Number(get('minute')),
  };
}

function fill(template: string, open: number, close: number): string {
  return template.replace('{open}', clock(open)).replace('{close}', clock(close));
}

function update(): void {
  let { day, minutes } = amsterdamNow();
  if (day < 0 || Number.isNaN(minutes)) return;

  // Shortly after midnight the evening that started yesterday is still going.
  if (minutes < DAY_ROLLOVER) {
    day = (day + 6) % 7;
    minutes += 1440;
  }

  const evening = week[day];
  const next = week[(day + 1) % 7];
  if (!evening || !next) return;

  let text: string;
  let currentDay = day;
  let marker: string = statusText.rowToday;
  if (minutes < evening.open) {
    text = fill(statusText.opensToday, evening.open, evening.close);
  } else if (minutes < evening.close) {
    text = fill(statusText.openNow, evening.open, evening.close);
    // After midnight on a late evening the open row is yesterday's, so say
    // "open now" instead of "today".
    marker = statusText.rowOpen;
  } else if (minutes >= 1440) {
    // Closed, after midnight: the next opening is later today.
    text = fill(statusText.closedOpensToday, next.open, next.close);
    currentDay = (day + 1) % 7;
  } else {
    text = fill(statusText.closedOpensTomorrow, next.open, next.close);
  }

  document.querySelectorAll('[data-today-line]').forEach((el) => {
    el.textContent = text;
  });
  document.querySelectorAll('[data-day]').forEach((el) => {
    const isCurrent = el.getAttribute('data-day') === String(currentDay);
    if (isCurrent) el.setAttribute('aria-current', 'date');
    else el.removeAttribute('aria-current');
    const now = el.querySelector('[data-now]');
    if (now) now.textContent = isCurrent ? `(${marker})` : '';
  });
}

update();
// Keep it right for a page left open through opening or closing time.
setInterval(update, 60_000);
