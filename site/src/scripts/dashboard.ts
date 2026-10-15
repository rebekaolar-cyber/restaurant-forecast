// The dashboard's gatekeeper.
//
// Order matters: nothing is shown and no data is asked for until the login
// has been checked with the server. A visitor without a login is sent to the
// login page. The real lock is in the database (row level security): even a
// tampered browser gets no rows without a valid login.

import { supabase, LOGIN_PATH } from '../lib/supabase';
import { isNetworkError } from '../lib/auth-errors';
import { DataError, fetchRestaurant } from '../lib/dashboard-data';
import { mountForecast } from './dashboard-view';
import { show } from './staff-form';

const checking = document.querySelector<HTMLElement>('[data-checking]');
const offline = document.querySelector<HTMLElement>('[data-offline]');
const app = document.querySelector<HTMLElement>('[data-dashboard]');
const logout = document.querySelector<HTMLButtonElement>('[data-logout]');
const restaurantLine = document.querySelector<HTMLElement>('[data-restaurant]');
const forecast = document.querySelector<HTMLElement>('[data-forecast]');

const states = ['loading', 'empty', 'error'] as const;
function state(name: (typeof states)[number] | 'ready'): void {
  states.forEach((s) => show(app?.querySelector(`[data-restaurant-state="${s}"]`), s === name));
}

function toLogin(): void {
  window.location.replace(LOGIN_PATH);
}

async function dropLoginAndLeave(): Promise<void> {
  // Forget the login on this device only, then leave.
  await supabase.auth.signOut({ scope: 'local' });
  toLogin();
}

let mounted = false;

async function loadRestaurant(): Promise<void> {
  state('loading');
  try {
    const restaurant = await fetchRestaurant();
    if (!restaurant) {
      state('empty');
      return;
    }
    if (restaurantLine) {
      restaurantLine.textContent = restaurant.name;
      show(restaurantLine);
    }
    state('ready');
    if (forecast && !mounted) {
      mounted = true;
      show(forecast);
      mountForecast(forecast, restaurant, dropLoginAndLeave);
    }
  } catch (error) {
    // 401 after a checked login means the login ended in the meantime.
    if (error instanceof DataError && error.kind === 'login-ended') return dropLoginAndLeave();
    state('error');
  }
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
