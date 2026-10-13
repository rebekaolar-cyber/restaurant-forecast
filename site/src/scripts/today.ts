// Marks today in the opening-hours list and fills in the "open today" line.
// Runs in the visitor's browser, reads the same hours as the pages, and sends
// nothing anywhere. Without JavaScript the pages simply show the full week.

import { week, clock, DAY_ROLLOVER } from '../content/hours';

// The sentences come from the page itself (data attributes on the line), so the
// same script works in every language.
type Templates = { opensToday: string; openNow: string; closedOpensToday: string; closedOpensTomorrow: string };

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
  const line = document.querySelector<HTMLElement>('[data-today-line]');
  if (!line) return;
  const tpl = line.dataset as unknown as Templates;
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
  if (minutes < evening.open) {
    text = fill(tpl.opensToday, evening.open, evening.close);
  } else if (minutes < evening.close) {
    text = fill(tpl.openNow, evening.open, evening.close);
  } else if (minutes >= 1440) {
    // Closed, after midnight: the next opening is later today.
    text = fill(tpl.closedOpensToday, next.open, next.close);
    currentDay = (day + 1) % 7;
  } else {
    text = fill(tpl.closedOpensTomorrow, next.open, next.close);
  }

  document.querySelectorAll<HTMLElement>('[data-today-line]').forEach((el) => {
    el.textContent = text;
  });
  document.querySelectorAll('[data-day]').forEach((el) => {
    if (el.getAttribute('data-day') === String(currentDay)) el.setAttribute('aria-current', 'date');
    else el.removeAttribute('aria-current');
  });
}

update();
// Keep it right for a page left open through opening or closing time.
setInterval(update, 60_000);
