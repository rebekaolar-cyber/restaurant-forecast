// Small helpers shared by the login and password forms.

import { staffText } from '../content/nl.staff';

export function show(el: Element | null | undefined, visible = true): void {
  if (el instanceof HTMLElement) el.hidden = !visible;
}

/** Show one message in the form's alert line, or clear it with null. */
export function setMessage(form: HTMLFormElement, text: string | null): void {
  const line = form.querySelector<HTMLElement>('[data-message]');
  if (!line) return;
  line.textContent = text ?? '';
  line.hidden = !text;
}

/** Lock the form while a request runs, and say so on the button. */
export function setBusy(form: HTMLFormElement, busy: boolean, busyLabel: string): void {
  const button = form.querySelector<HTMLButtonElement>('button[type="submit"]');
  if (!button) return;
  if (busy) {
    button.dataset.label = button.textContent ?? '';
    button.textContent = busyLabel;
  } else if (button.dataset.label) {
    button.textContent = button.dataset.label;
  }
  button.disabled = busy;
  form.setAttribute('aria-busy', String(busy));
}

/** "Toon" / "Verberg" buttons next to password fields. */
export function wirePasswordToggles(root: ParentNode = document): void {
  root.querySelectorAll<HTMLButtonElement>('[data-toggle-password]').forEach((button) => {
    const input = document.getElementById(button.getAttribute('aria-controls') ?? '');
    if (!(input instanceof HTMLInputElement)) return;
    button.addEventListener('click', () => {
      const reveal = input.type === 'password';
      input.type = reveal ? 'text' : 'password';
      button.textContent = reveal ? staffText.login.hide : staffText.login.show;
      button.setAttribute('aria-pressed', String(reveal));
    });
  });
}
