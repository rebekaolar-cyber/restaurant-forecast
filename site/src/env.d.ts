/// <reference types="astro/client" />

interface ImportMetaEnv {
  /** "true" once this site is the official one. Anything else = test version. */
  readonly PUBLIC_SITE_LIVE?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
