import { defineConfig } from 'astro/config';
import { loadEnv } from 'vite';
import { looksSecret, SECRET_KEY_MESSAGE } from './src/lib/key-guard.mjs';

// Safety catch: everything named PUBLIC_ ends up in the files visitors
// download. If someone ever pastes the SECRET Supabase key into that variable,
// stop the build instead of publishing it.
const env = { ...loadEnv(process.env.NODE_ENV ?? 'production', process.cwd(), 'PUBLIC_'), ...process.env };
if (looksSecret(env.PUBLIC_SUPABASE_PUBLISHABLE_KEY)) throw new Error(SECRET_KEY_MESSAGE);

// Static site: every page is plain HTML built ahead of time, so Cloudflare
// Pages only has to serve files. No server code runs for visitors.
export default defineConfig({
  // The address the site will have once it replaces the current one. Used for
  // canonical links, language alternates, the sitemap and the sharing picture.
  site: 'https://habibienschede.nl',
  output: 'static',
  trailingSlash: 'always',
  build: {
    // Keep CSS and JS in separate files (never inline in the HTML). That lets
    // stage 4 use a strict content security policy without exceptions.
    inlineStylesheets: 'never',
  },
  vite: {
    build: {
      assetsInlineLimit: 0,
      // Keep the CSS as written. The default minifier (Lightning CSS) folds
      // animation-timeline into the animation shorthand, which browsers then
      // reject, so every scroll animation (the front door opening) stopped.
      // The size difference after compression is a few kilobytes.
      cssMinify: false,
    },
  },
});
