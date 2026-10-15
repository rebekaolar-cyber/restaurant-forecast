// The page an invitation or reset e-mail leads to: choose a password.
// The e-mail link logs the person in once; saving a password here makes the
// normal login work from then on.

import { supabase, DASHBOARD_PATH } from '../lib/supabase';
import { explain } from '../lib/auth-errors';
import { staffText } from '../content/nl.staff';
import { setBusy, setMessage, show, wirePasswordToggles } from './staff-form';

const checking = document.querySelector<HTMLElement>('[data-view="checking"]');
const formView = document.querySelector<HTMLElement>('[data-view="form"]');
const expired = document.querySelector<HTMLElement>('[data-view="expired"]');
const saved = document.querySelector<HTMLElement>('[data-view="saved"]');

// Supabase reports a dead link in the address, after the "#".
const linkFailed = /(^#|&)error(_code)?=/.test(window.location.hash);

async function start(): Promise<void> {
  show(checking);
  // getSession waits until the client has read the one-time login from the address.
  const { data } = await supabase.auth.getSession();
  show(checking, false);
  if (linkFailed || !data.session) {
    show(expired);
    return;
  }
  show(formView);
  wirePasswordToggles();

  const form = document.querySelector<HTMLFormElement>('[data-set-password]');
  form?.addEventListener('submit', async (event) => {
    event.preventDefault();
    const fields = new FormData(form);
    const password = String(fields.get('password') ?? '');
    const repeat = String(fields.get('repeat') ?? '');
    setMessage(form, null);
    if (password.length < 8) return setMessage(form, staffText.errors.tooShort);
    if (password !== repeat) return setMessage(form, staffText.errors.mismatch);

    setBusy(form, true, staffText.setPassword.busy);
    const { error } = await supabase.auth.updateUser({ password });
    if (error) {
      setBusy(form, false, staffText.setPassword.busy);
      setMessage(form, explain(error));
      return;
    }
    show(formView, false);
    show(saved);
    window.setTimeout(() => window.location.replace(DASHBOARD_PATH), 1200);
  });
}

start();
