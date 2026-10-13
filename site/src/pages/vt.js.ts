// /vt.js: a tiny script that runs before the first paint of every public page.
// When the browser animates from one page to the next, it decides how:
// to or from the homepage, the green double door plays ("door"); between the
// other pages (menu, about, contact, privacy) and when only the language
// changes, the page simply cross-fades. It reads only where the visitor came
// from on this same site and sends nothing anywhere.
import { LANGS, ROUTES } from '../content/i18n';

export function GET() {
  const map: Record<string, string> = {};
  for (const [page, byLang] of Object.entries(ROUTES)) {
    for (const lang of LANGS) map[byLang[lang]] = page;
  }
  const js = `(function(){var P=${JSON.stringify(map)};addEventListener('pagereveal',function(e){try{if(!e.viewTransition)return;var a=window.navigation&&navigation.activation,f=(a&&a.from&&a.from.url)||document.referrer;if(!f)return;var u=new URL(f);if(u.origin!==location.origin)return;var x=P[u.pathname],y=P[location.pathname];if(x!==y&&(x==='home'||y==='home'))e.viewTransition.types.add('door')}catch(_){}})})();\n`;
  return new Response(js, { headers: { 'Content-Type': 'text/javascript; charset=utf-8' } });
}
