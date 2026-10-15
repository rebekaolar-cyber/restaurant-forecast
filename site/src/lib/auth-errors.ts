// Turns an error from Supabase Auth into one plain Dutch sentence.

import { isAuthRetryableFetchError, isAuthWeakPasswordError } from '@supabase/supabase-js';
import { staffText } from '../content/nl.staff';

const e = staffText.errors;

type AuthLikeError = { code?: string; status?: number; name?: string; message?: string } | null;

export function isNetworkError(error: unknown): boolean {
  if (!error) return false;
  if (isAuthRetryableFetchError(error)) return true;
  const message = (error as { message?: string }).message ?? '';
  return /failed to fetch|networkerror|load failed/i.test(message);
}

export function explain(error: AuthLikeError): string {
  if (!error) return e.generic;
  if (isNetworkError(error)) return e.network;
  if (isAuthWeakPasswordError(error) || error.code === 'weak_password') return e.weak;
  switch (error.code) {
    case 'invalid_credentials':
      return e.invalidCredentials;
    case 'email_not_confirmed':
      return e.notConfirmed;
    case 'same_password':
      return e.same;
    case 'over_email_send_rate_limit':
      return e.emailRate;
    case 'over_request_rate_limit':
      return e.tooMany;
  }
  if (error.status === 429) return e.tooMany;
  return e.generic;
}
