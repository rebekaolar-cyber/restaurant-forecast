// A safety catch: the website may only ever hold Supabase's PUBLIC key
// (sb_publishable_... or the older "anon" key). This recognises a SECRET key
// so the build and the page can refuse it instead of publishing it.
// Plain JavaScript on purpose: astro.config.mjs imports it too.

/** @param {unknown} key */
export function looksSecret(key) {
  if (typeof key !== 'string') return false;
  if (key.startsWith('sb_secret_')) return true;
  // Older keys are JWTs: the middle part says which role the key carries.
  const parts = key.split('.');
  if (parts.length !== 3) return false;
  try {
    const payload = JSON.parse(atob(parts[1].replace(/-/g, '+').replace(/_/g, '/')));
    return payload.role !== 'anon';
  } catch {
    return false;
  }
}

export const SECRET_KEY_MESSAGE =
  'PUBLIC_SUPABASE_PUBLISHABLE_KEY holds a SECRET Supabase key. The website must only ever get the public key (sb_publishable_...). Remove it, and roll the secret key in Supabase because it has been exposed to this build.';
