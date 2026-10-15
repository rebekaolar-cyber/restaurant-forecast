/// <reference types="astro/client" />

interface ImportMetaEnv {
  /** "true" once this site is the official one. Anything else = test version. */
  readonly PUBLIC_SITE_LIVE?: string;
  /** Optional: another Supabase project than the one in src/lib/supabase.ts. */
  readonly PUBLIC_SUPABASE_URL?: string;
  /** Optional, and only ever the PUBLIC key (sb_publishable_...). Never the secret key. */
  readonly PUBLIC_SUPABASE_PUBLISHABLE_KEY?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
