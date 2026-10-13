// /vt.js: a tiny script that runs before the first paint of every public page.
// When the browser animates from one page to the next (the page door), it
// checks whether the visitor only switched language on the same page. Then the
// door stays away and the page simply cross-fades. Sends nothing anywhere.
import { LANGS, ROUTES } from '../content/i18n';

export function GET() {
  const map: Record<string, string> = {};
  for (const [page, byLang] of Object.entries(ROUTES)) {
    for (const lang of LANGS) map[byLang[lang]] = page;
  }
  const js = `(function(){var P=${JSON.stringify(map)};addEventListener('pagereveal',function(e){try{var a=window.navigation&&navigation.activation,f=a&&a.from;if(!e.viewTransition||!f)return;var x=P[new URL(f.url).pathname],y=P[location.pathname];if(x&&x===y)e.viewTransition.types.add('lang')}catch(_){}})})();\n`;
  return new Response(js, { headers: { 'Content-Type': 'text/javascript; charset=utf-8' } });
}
