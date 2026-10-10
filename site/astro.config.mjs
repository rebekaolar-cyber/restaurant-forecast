import { defineConfig } from 'astro/config';

// Static site: every page is plain HTML built ahead of time, so Cloudflare
// Pages only has to serve files. No server code runs for visitors.
export default defineConfig({
  output: 'static',
  trailingSlash: 'always',
  build: {
    // Keep CSS and JS in separate files (never inline in the HTML). That lets
    // stage 4 use a strict content security policy without exceptions.
    inlineStylesheets: 'never',
  },
  vite: {
    build: { assetsInlineLimit: 0 },
  },
});
