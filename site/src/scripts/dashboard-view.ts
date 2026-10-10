// Draws the 14-day forecast and lets the manager set their own staff numbers.
//
// Every piece of text from the database (the note, the restaurant's name, the
// model's name) is put on the page as plain text, never as HTML, so nothing
// typed into a note can turn into code.

import { staffText } from '../content/nl.staff';
import { applyOverride, DataError, fetchWindow, type ForecastWindow } from '../lib/dashboard-data';
import {
  buildDays,
  dayLabel,
  dayLabelLong,
  firstDayShown,
  guestScale,
  isStale,
  lastUpdated,
  MAX_STAFF,
  NOTE_MAX,
  overrideAction,
  rainText,
  readStaff,
  serviceDay,
  temperatureText,
  whenAtRestaurant,
  type DayShift,
  type Restaurant,
} from '../lib/forecast-days';
import { show } from './staff-form';

const t = staffText.dashboard;
const REFRESH_AFTER_MS = 5 * 60 * 1000;

const fill = (template: string, values: Record<string, string | number>): string =>
  template.replace(/\{(\w+)\}/g, (_, key: string) => String(values[key] ?? ''));

function el<K extends keyof HTMLElementTagNameMap>(
  tag: K,
  className = '',
  text = '',
): HTMLElementTagNameMap[K] {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text) node.textContent = text;
  return node;
}

const hiddenText = (text: string) => el('span', 'visually-hidden', text);
const comma = (n: number) => String(Math.round(n * 10) / 10).replace('.', ',');

export function mountForecast(
  root: HTMLElement,
  restaurant: Restaurant,
  onLoginEnded: () => void,
): void {
  const find = <T extends HTMLElement>(selector: string) => root.querySelector<T>(selector);
  const list = find<HTMLUListElement>('[data-list]');
  const head = find('[data-list-head]');
  const updated = find('[data-updated]');
  const refresh = find<HTMLButtonElement>('[data-refresh]');
  const states = ['loading', 'error', 'offline'] as const;
  const notes = {
    placeholder: find('[data-note="placeholder"]'),
    stale: find('[data-note="stale"]'),
    empty: find('[data-note="empty"]'),
    weather: find('[data-note="weather"]'),
    hint: find('[data-note="hint"]'),
  };
  if (!list) return;

  let rows: ForecastWindow = { forecasts: [], weather: [], overrides: [] };
  let days: DayShift[] = [];
  let scale = 50;
  let openKey: string | null = null;
  let loadedAt = 0;
  let hasLoaded = false;

  const state = (name: (typeof states)[number] | 'ready') =>
    states.forEach((s) => show(find(`[data-state="${s}"]`), s === name));
  const dayOf = (key: string) => days.find((d) => d.key === key);
  const rowOf = (key: string) =>
    list?.querySelector<HTMLButtonElement>(`.day__row[data-key="${key}"]`) ?? null;
  const panelId = (key: string) => `dag-${key.replace(/[^0-9a-z]/gi, '-')}`;

  // ---------- One line of the list ----------

  function staffCell(
    role: 'servers' | 'cooks',
    value: number | null,
    changed: boolean,
    forecast?: number,
  ) {
    const label = t.columns[role];
    const cell = el('span', `day__staff day__staff--${role}${changed ? ' day__staff--changed' : ''}`);
    cell.append(hiddenText(`${label} `), el('span', 'day__n', value == null ? '–' : String(value)));
    if (changed && forecast != null) {
      cell.append(' ', el('span', 'day__was', fill(t.forecastWas, { n: forecast })));
    }
    cell.append(hiddenText('. '));
    return cell;
  }

  function fillRow(button: HTMLButtonElement, day: DayShift): void {
    button.replaceChildren();

    const date = el('span', 'day__date');
    const short = el('span', '', dayLabel(day.date));
    short.setAttribute('aria-hidden', 'true');
    date.append(hiddenText(dayLabelLong(day.date)), short);
    if (day.isToday) date.append(' ', el('span', 'day__today', t.today));
    date.append(hiddenText('. '));

    const weather = el('span', 'day__weather');
    const temp = temperatureText(day.weather?.temp_max ?? null);
    const rain = rainText(day.weather?.rain_mm ?? null, t.weather.dry);
    if (temp || rain) {
      weather.append(hiddenText(`${t.columns.weather}: `));
      if (temp) weather.append(el('span', 'day__temp', temp));
      if (rain) weather.append(' ', el('span', 'day__rain', rain));
      weather.append(hiddenText('. '));
    }

    const guests = el('span', 'day__guests');
    if (day.forecast) {
      const bar = el('span', 'day__bar');
      // The bar's length is the share of the busiest evening shown.
      bar.style.setProperty('--share', String(Math.min(1, day.forecast.predicted_guests / scale)));
      bar.setAttribute('aria-hidden', 'true');
      guests.append(
        bar,
        el('span', 'day__n', String(day.forecast.predicted_guests)),
        hiddenText(` ${t.guests}. `),
      );
    } else {
      guests.append(el('span', 'day__none', t.noForecast), hiddenText('. '));
    }

    const chevron = el('span', 'day__chevron');
    chevron.setAttribute('aria-hidden', 'true');

    button.append(
      date,
      weather,
      guests,
      staffCell('servers', day.servers, day.serversOverridden, day.forecast?.servers),
      staffCell('cooks', day.cooks, day.cooksOverridden, day.forecast?.cooks),
      chevron,
    );
    if (day.override?.note) {
      const note = el('span', 'day__note');
      note.append(hiddenText(`${t.noteLabel} `), day.override.note);
      button.append(note);
    }
  }

  // ---------- The edit panel of one day ----------

  function weatherSentence(day: DayShift): string {
    const w = day.weather;
    if (!w) return t.weather.unknown;
    const parts: string[] = [];
    if (w.temp_max != null) parts.push(fill(t.weather.max, { n: Math.round(w.temp_max) }));
    const rain = rainText(w.rain_mm, t.weather.dry);
    if (rain) parts.push(rain === t.weather.dry ? rain : fill(t.weather.rain, { n: rain }));
    if (w.wind_max != null) parts.push(fill(t.weather.wind, { n: Math.round(w.wind_max) }));
    if (w.sunshine_hours != null) parts.push(fill(t.weather.sun, { n: comma(w.sunshine_hours) }));
    if (parts.length === 0) return t.weather.unknown;
    return `${w.is_forecast ? t.weather.forecast : t.weather.measured}: ${parts.join(', ')}.`;
  }

  function stepper(name: 'servers' | 'cooks', key: string) {
    const label = t.editor[name];
    const id = `${panelId(key)}-${name}`;
    const wrap = el('div', 'stepper');
    const caption = el('label', 'stepper__label', label);
    caption.htmlFor = id;
    const input = el('input', 'input stepper__input');
    input.id = id;
    input.name = name;
    input.inputMode = 'numeric';
    input.pattern = '[0-9]*';
    input.maxLength = 2;
    input.autocomplete = 'off';
    input.setAttribute('aria-describedby', `${id}-hint`);
    const hint = el('p', 'stepper__hint small muted');
    hint.id = `${id}-hint`;

    const step = (by: number) => {
      const day = dayOf(key);
      const typed = readStaff(input.value);
      const from = typed.ok && typed.value != null ? typed.value : (day?.forecast?.[name] ?? 0);
      input.value = String(Math.max(0, Math.min(MAX_STAFF, from + by)));
    };
    const less = el('button', 'stepper__button', '−');
    less.type = 'button';
    less.setAttribute('aria-label', `${label}: ${t.editor.less}`);
    less.addEventListener('click', () => step(-1));
    const more = el('button', 'stepper__button', '+');
    more.type = 'button';
    more.setAttribute('aria-label', `${label}: ${t.editor.more}`);
    more.addEventListener('click', () => step(1));

    const controls = el('div', 'stepper__controls');
    controls.append(less, input, more);
    wrap.append(caption, controls, hint);
    return { wrap, input, hint };
  }

  function buildPanel(key: string): HTMLElement {
    const panel = el('div', 'day__panel');
    panel.id = panelId(key);
    const weather = el('p', 'small muted');
    const form = el('form', 'editor');
    form.noValidate = true;
    const title = el('h2', 'editor__title');
    const servers = stepper('servers', key);
    const cooks = stepper('cooks', key);
    const fields = el('div', 'editor__fields');
    fields.append(servers.wrap, cooks.wrap);

    const noteId = `${panelId(key)}-note`;
    const noteWrap = el('div', 'field');
    const noteLabel = el('label', '', t.editor.note);
    noteLabel.htmlFor = noteId;
    const note = el('textarea', 'input editor__note');
    note.id = noteId;
    note.name = 'note';
    note.rows = 2;
    note.maxLength = NOTE_MAX;
    note.setAttribute('aria-describedby', `${noteId}-hint`);
    const noteHint = el('p', 'small muted', t.editor.noteHint);
    noteHint.id = `${noteId}-hint`;
    noteWrap.append(noteLabel, note, noteHint);

    const problem = el('p', 'notice');
    problem.setAttribute('role', 'alert');
    problem.hidden = true;
    const done = el('p', 'editor__done');
    done.setAttribute('role', 'status');

    const save = el('button', 'button', t.editor.save);
    save.type = 'submit';
    const remove = el('button', 'button button--quiet', t.editor.remove);
    remove.type = 'button';
    const actions = el('div', 'editor__actions');
    actions.append(save, remove);
    const changed = el('p', 'small muted');

    form.append(title, fields, noteWrap, problem, actions, done, changed);
    panel.append(weather, form);

    /** Put the stored values into the fields. */
    function sync(): void {
      const day = dayOf(key);
      if (!day) return;
      title.textContent = fill(t.editor.title, { day: dayLabelLong(day.date) });
      weather.textContent = weatherSentence(day);
      servers.input.value = day.servers == null ? '' : String(day.servers);
      cooks.input.value = day.cooks == null ? '' : String(day.cooks);
      const hintFor = (n: number | undefined) =>
        n == null ? t.editor.noForecastHint : fill(t.editor.forecastHint, { n });
      servers.hint.textContent = hintFor(day.forecast?.servers);
      cooks.hint.textContent = hintFor(day.forecast?.cooks);
      note.value = day.override?.note ?? '';
      remove.hidden = !day.override;
      if (day.override) {
        const when = whenAtRestaurant(day.override.updated_at, new Date(), restaurant.timezone);
        const text =
          when.day === 'today'
            ? fill(t.editor.whenToday, when)
            : when.day === 'yesterday'
              ? fill(t.editor.whenYesterday, when)
              : fill(t.editor.whenOther, { day: when.dayText, time: when.time });
        changed.textContent = fill(t.editor.changedAt, { when: text });
      } else {
        changed.textContent = '';
      }
    }

    function busy(on: boolean): void {
      save.disabled = on;
      remove.disabled = on;
      save.textContent = on ? t.editor.saving : t.editor.save;
      form.setAttribute('aria-busy', String(on));
    }

    async function run(action: ReturnType<typeof overrideAction>, doneText: string) {
      const day = dayOf(key);
      if (!day) return;
      problem.hidden = true;
      done.textContent = '';
      busy(true);
      try {
        const stored = await applyOverride(restaurant.id, day.date, day.shift, action);
        rows.overrides = rows.overrides.filter(
          (o) => !(o.date === day.date && o.shift === day.shift),
        );
        if (stored) rows.overrides.push(stored);
        rebuild();
        const row = rowOf(key);
        const fresh = dayOf(key);
        if (row && fresh) {
          fillRow(row, fresh);
          row.parentElement?.classList.toggle('day--changed', !!fresh.override);
        }
        sync();
        done.textContent = doneText;
      } catch (error) {
        if (error instanceof DataError && error.kind === 'login-ended') return onLoginEnded();
        problem.textContent =
          error instanceof DataError && error.kind === 'offline'
            ? t.editor.saveOffline
            : t.editor.saveFailed;
        problem.hidden = false;
      } finally {
        busy(false);
      }
    }

    form.addEventListener('submit', (event) => {
      event.preventDefault();
      const day = dayOf(key);
      if (!day) return;
      const s = readStaff(servers.input.value);
      const c = readStaff(cooks.input.value);
      if (!s.ok || !c.ok) {
        done.textContent = '';
        problem.textContent = t.editor.invalid;
        problem.hidden = false;
        (s.ok ? cooks.input : servers.input).focus();
        return;
      }
      const action = overrideAction(
        { servers: s.value, cooks: c.value, note: note.value },
        day.forecast,
      );
      if (action.kind === 'remove' && !day.override) {
        problem.hidden = true;
        sync();
        done.textContent = t.editor.nothingToSave;
        return;
      }
      run(action, action.kind === 'remove' ? t.editor.removed : t.editor.saved);
    });
    remove.addEventListener('click', () => run({ kind: 'remove' }, t.editor.removed));

    sync();
    return panel;
  }

  function toggle(key: string, button: HTMLButtonElement): void {
    const item = button.parentElement;
    if (!item) return;
    const wasOpen = openKey === key;
    // One day open at a time.
    list?.querySelectorAll<HTMLElement>('.day__panel').forEach((panel) => panel.remove());
    list?.querySelectorAll('[aria-expanded="true"]').forEach((b) => {
      b.setAttribute('aria-expanded', 'false');
      b.removeAttribute('aria-controls');
    });
    openKey = null;
    if (wasOpen) return;
    const panel = buildPanel(key);
    item.append(panel);
    button.setAttribute('aria-expanded', 'true');
    button.setAttribute('aria-controls', panel.id);
    openKey = key;
    panel.scrollIntoView({ block: 'nearest' });
  }

  // ---------- The whole list ----------

  function rebuild(): void {
    const today = firstDayShown(new Date(), restaurant.timezone, rows.forecasts);
    days = buildDays(today, rows.forecasts, rows.weather, rows.overrides);
    scale = guestScale(days);
  }

  function render(): void {
    rebuild();
    openKey = null;
    list?.replaceChildren(
      ...days.map((day) => {
        const item = el('li', 'day');
        item.classList.toggle('day--today', day.isToday);
        item.classList.toggle('day--week', day.startsWeek);
        item.classList.toggle('day--changed', !!day.override);
        const button = el('button', 'day__row');
        button.type = 'button';
        button.setAttribute('aria-expanded', 'false');
        button.dataset.key = day.key;
        fillRow(button, day);
        button.addEventListener('click', () => toggle(day.key, button));
        item.append(button);
        return item;
      }),
    );

    // Only the days on screen count for the notes above the list.
    const shown = days.flatMap((d) => (d.forecast ? [d.forecast] : []));
    const newest = lastUpdated(shown);
    if (updated) {
      if (newest) {
        const when = whenAtRestaurant(newest, new Date(), restaurant.timezone);
        const line =
          when.day === 'today'
            ? fill(t.updatedToday, when)
            : when.day === 'yesterday'
              ? fill(t.updatedYesterday, when)
              : fill(t.updatedOther, { day: when.dayText, time: when.time });
        const models = [...new Set(shown.map((f) => f.model))].join(', ');
        updated.textContent = `${line} ${fill(t.model, { model: models })}`;
      } else {
        updated.textContent = '';
      }
      show(updated, !!newest);
    }
    show(notes.placeholder, shown.some((f) => f.model === 'placeholder'));
    show(notes.stale, isStale(newest, new Date()));
    show(notes.empty, shown.length === 0);
    show(notes.weather, shown.length > 0 && !days.some((d) => d.weather));
    show(notes.hint);
    show(head);
    show(list);
    show(refresh);
  }

  async function load(): Promise<void> {
    if (hasLoaded) {
      // Keep what is on screen while new numbers come in.
      list?.setAttribute('aria-busy', 'true');
      if (refresh) {
        refresh.disabled = true;
        refresh.textContent = t.refreshing;
      }
    } else {
      state('loading');
    }
    try {
      rows = await fetchWindow(restaurant.id, serviceDay(new Date(), restaurant.timezone));
      loadedAt = Date.now();
      hasLoaded = true;
      state('ready');
      render();
    } catch (error) {
      if (error instanceof DataError && error.kind === 'login-ended') return onLoginEnded();
      state(error instanceof DataError && error.kind === 'offline' ? 'offline' : 'error');
    } finally {
      list?.removeAttribute('aria-busy');
      if (refresh) {
        refresh.disabled = false;
        refresh.textContent = t.refresh;
      }
    }
  }

  refresh?.addEventListener('click', () => load());
  root
    .querySelectorAll<HTMLButtonElement>('[data-retry-forecast]')
    .forEach((button) => button.addEventListener('click', () => load()));

  // Escape closes the open day and puts the cursor back on its line.
  list.addEventListener('keydown', (event) => {
    if (event.key !== 'Escape' || !openKey) return;
    const button = rowOf(openKey);
    if (button) {
      toggle(openKey, button);
      button.focus();
    }
  });

  // Coming back to the tab after a while: fetch fresh numbers, unless a day is
  // open for editing (never pull the form out from under someone typing).
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState !== 'visible' || openKey || !hasLoaded) return;
    if (Date.now() - loadedAt > REFRESH_AFTER_MS) load();
  });

  load();
}
