// The login page: sign in with e-mail and password, or ask for a reset link.
// There is no sign-up here. Accounts exist only by invitation.

import { supabase, DASHBOARD_PATH, SET_PASSWORD_PATH } from '../lib/supabase';
import { explain } from '../lib/auth-errors';
import { staffText } from '../content/nl.staff';
import { setBusy, setMessage, show, wirePasswordToggles } from './staff-form';

const views = {
  login: document.querySelector<HTMLElement>('[data-view="login"]'),
  reset: document.querySelector<HTMLElement>('[data-view="reset"]'),
  sent: document.querySelector<HTMLElement>('[data-view="sent"]'),
};

function open(name: keyof typeof views): void {
  (Object.keys(views) as (keyof typeof views)[]).forEach((key) => show(views[key], key === name));
  views[name]?.querySelector<HTMLElement>('h1')?.focus();
}

async function start(): Promise<void> {
  // Already logged in on this device: go straight to the dashboard.
  const { data } = await supabase.auth.getSession();
  if (data.session) {
    window.location.replace(DASHBOARD_PATH);
    return;
  }
  show(views.login);
  wirePasswordToggles();

  const loginForm = document.querySelector<HTMLFormElement>('[data-login]');
  loginForm?.addEventListener('submit', async (event) => {
    event.preventDefault();
    const fields = new FormData(loginForm);
    setMessage(loginForm, null);
    setBusy(loginForm, true, staffText.login.busy);
    const { error } = await supabase.auth.signInWithPassword({
      email: String(fields.get('email') ?? '').trim(),
      password: String(fields.get('password') ?? ''),
    });
    if (error) {
      setBusy(loginForm, false, staffText.login.busy);
      setMessage(loginForm, explain(error));
      return;
    }
    window.location.replace(DASHBOARD_PATH);
  });

  const resetForm = document.querySelector<HTMLFormElement>('[data-reset]');
  resetForm?.addEventListener('submit', async (event) => {
    event.preventDefault();
    const email = String(new FormData(resetForm).get('email') ?? '').trim();
    setMessage(resetForm, null);
    setBusy(resetForm, true, staffText.reset.busy);
    const { error } = await supabase.auth.resetPasswordForEmail(email, {
      redirectTo: window.location.origin + SET_PASSWORD_PATH,
    });
    setBusy(resetForm, false, staffText.reset.busy);
    if (error) {
      setMessage(resetForm, explain(error));
      return;
    }
    // The same answer whether or not the address has an account, so this
    // form cannot be used to find out who works here.
    open('sent');
  });

  document.querySelectorAll<HTMLElement>('[data-open]').forEach((control) => {
    control.addEventListener('click', () => open(control.dataset.open as keyof typeof views));
  });
  if (window.location.hash === '#vergeten') open('reset');
}

start();
