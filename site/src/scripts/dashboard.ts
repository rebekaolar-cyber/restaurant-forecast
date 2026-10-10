// The dashboard's gatekeeper.
//
// Order matters: nothing is shown and no data is asked for until the login
// has been checked with the server. A visitor without a login is sent to the
// login page. The real lock is in the database (row level security): even a
// tampered browser gets no rows without a valid login.

import { supabase, LOGIN_PATH } from '../lib/supabase';
import { isNetworkError } from '../lib/auth-errors';
import { staffText } from '../content/nl.staff';
import { show } from './staff-form';

const t = staffText.dashboard;
const checking = document.querySelector<HTMLElement>('[data-checking]');
const offline = document.querySelector<HTMLElement>('[data-offline]');
const app = document.querySelector<HTMLElement>('[data-dashboard]');
const logout = document.querySelector<HTMLButtonElement>('[data-logout]');
const restaurantLine = document.querySelector<HTMLElement>('[data-restaurant]');

const states = ['loading', 'empty', 'error', 'ready'] as const;
function state(name: (typeof states)[number]): void {
  states.forEach((s) => show(app?.querySelector(`[data-state="${s}"]`), s === name));
}

function toLogin(): void {
  window.location.replace(LOGIN_PATH);
}

async function dropLoginAndLeave(): Promise<void> {
  // Forget the login on this device only, then leave.
  await supabase.auth.signOut({ scope: 'local' });
  toLogin();
}

async function loadRestaurant(): Promise<void> {
  state('loading');
  show(restaurantLine, false);
  const { data, error, status } = await supabase.from('restaurants').select('id, name').limit(1);
  if (error) {
    // 401 after a checked login means the login ended in the meantime.
    if (status === 401) return dropLoginAndLeave();
    state('error');
    return;
  }
  const restaurant = data?.[0];
  if (!restaurant) {
    state('empty');
    return;
  }
  if (restaurantLine) {
    restaurantLine.textContent = t.loggedInFor.replace('{restaurant}', String(restaurant.name));
    show(restaurantLine);
  }
  state('ready');
}

async function start(): Promise<void> {
  show(checking);
  show(offline, false);

  // 1. Is there a login on this device at all? (No network needed.)
  const { data: local } = await supabase.auth.getSession();
  if (!local.session) return toLogin();

  // 2. Ask the server whether that login is real and still valid.
  const { data: checked, error } = await supabase.auth.getUser();
  if (error || !checked.user) {
    if (isNetworkError(error)) {
      show(checking, false);
      show(offline);
      return;
    }
    return dropLoginAndLeave();
  }

  // 3. Only now show the dashboard and ask for data.
  show(checking, false);
  show(app);
  show(logout);
  await loadRestaurant();
}

logout?.addEventListener('click', async () => {
  logout.disabled = true;
  await supabase.auth.signOut();
  toLogin();
});

document.querySelectorAll<HTMLButtonElement>('[data-retry]').forEach((button) => {
  button.addEventListener('click', () => (app?.hidden ? start() : loadRestaurant()));
});

// Logged out in another tab, or the login could not be renewed: leave here too.
supabase.auth.onAuthStateChange((event) => {
  if (event === 'SIGNED_OUT') toLogin();
});

start();
