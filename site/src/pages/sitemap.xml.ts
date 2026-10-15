// The list of public pages for search engines, with each page's four languages.
// Built once at build time into /sitemap.xml. The staff pages are not in it.
import type { APIRoute } from 'astro';
import { LANGS, ROUTES, type PageKey } from '../content/i18n';

export const GET: APIRoute = ({ site }) => {
  const base = site ?? new URL('https://www.habibienschede.nl');
  const abs = (path: string) => new URL(path, base).href;
  const urls = (Object.keys(ROUTES) as PageKey[]).flatMap((page) =>
    LANGS.map((lang) => {
      const alternates = LANGS.map((l) => `    <xhtml:link rel="alternate" hreflang="${l}" href="${abs(ROUTES[page][l])}"/>`)
        .concat(`    <xhtml:link rel="alternate" hreflang="x-default" href="${abs(ROUTES[page].nl)}"/>`)
        .join('\n');
      return `  <url>\n    <loc>${abs(ROUTES[page][lang])}</loc>\n${alternates}\n  </url>`;
    }),
  );
  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">
${urls.join('\n')}
</urlset>
`;
  return new Response(xml, { headers: { 'Content-Type': 'application/xml; charset=utf-8' } });
};
