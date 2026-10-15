// Instructions for search engines, built into /robots.txt.
// While this is a test version (PUBLIC_SITE_LIVE is not "true") every page stays
// out of search results. Once live, everything except the staff pages may be read.
import type { APIRoute } from 'astro';

export const GET: APIRoute = ({ site }) => {
  const live = import.meta.env.PUBLIC_SITE_LIVE === 'true';
  const sitemap = new URL('/sitemap.xml', site ?? 'https://www.habibienschede.nl').href;
  const body = live
    ? `User-agent: *\nDisallow: /login/\nDisallow: /dashboard/\n\nSitemap: ${sitemap}\n`
    : `# Test version: please do not index.\nUser-agent: *\nDisallow: /\n`;
  return new Response(body, { headers: { 'Content-Type': 'text/plain; charset=utf-8' } });
};
