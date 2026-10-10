// The one Supabase client for the login pages and the dashboard.
//
// The two values below are the project's address and its PUBLIC key. They are
// safe to publish: every visitor's browser receives them anyway, and on their
// own they open nothing. What a person may read is decided by the login and
// by row level security in the database. The SECRET key never belongs here.
//
// To point a build at another project (for example a local test server), set
// PUBLIC_SUPABASE_URL and PUBLIC_SUPABASE_PUBLISHABLE_KEY.

import { createClient } from '@supabase/supabase-js';
import { looksSecret, SECRET_KEY_MESSAGE } from './key-guard.mjs';

const url = import.meta.env.PUBLIC_SUPABASE_URL || 'https://wuyqodgnnjoefaxepkiz.supabase.co';
const key =
  import.meta.env.PUBLIC_SUPABASE_PUBLISHABLE_KEY ||
  'sb_publishable_MAz9nrGmBEnc_Y_SLCBxwA_8B8tc91r';

if (looksSecret(key)) throw new Error(SECRET_KEY_MESSAGE);

export const supabase = createClient(url, key, {
  auth: {
    // Stay logged in on this device, and renew the login quietly in the background.
    persistSession: true,
    autoRefreshToken: true,
    // Invitation and password-reset e-mails send the user back with a one-time
    // login in the address. Pick that up when a page opens.
    detectSessionInUrl: true,
    flowType: 'implicit',
  },
});

export const LOGIN_PATH = '/login/';
export const DASHBOARD_PATH = '/dashboard/';
export const SET_PASSWORD_PATH = '/login/nieuw-wachtwoord/';
