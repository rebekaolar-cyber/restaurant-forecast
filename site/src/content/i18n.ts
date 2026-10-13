// Languages and addresses of the public site.
// Dutch lives at the plain address, the other languages under /en/, /de/ and /ar/.
// Every page exists in all four languages; the header links to the same page
// in the other language.

import { TR } from './strings';

export const LANGS = ['nl', 'en', 'de', 'ar'] as const;
export type Lang = (typeof LANGS)[number];

export const LANG_NAMES: Record<Lang, string> = {
  nl: 'Nederlands',
  en: 'English',
  de: 'Deutsch',
  ar: 'العربية',
};

/** Open Graph locale per language. */
export const OG_LOCALE: Record<Lang, string> = { nl: 'nl_NL', en: 'en_GB', de: 'de_DE', ar: 'ar_AR' };

export type PageKey = 'home' | 'menu' | 'about' | 'contact' | 'privacy';

export const ROUTES: Record<PageKey, Record<Lang, string>> = {
  home: { nl: '/', en: '/en/', de: '/de/', ar: '/ar/' },
  menu: { nl: '/menu/', en: '/en/menu/', de: '/de/speisekarte/', ar: '/ar/menu/' },
  about: { nl: '/over-ons/', en: '/en/about/', de: '/de/ueber-uns/', ar: '/ar/about/' },
  contact: { nl: '/contact/', en: '/en/contact/', de: '/de/kontakt/', ar: '/ar/contact/' },
  privacy: { nl: '/privacy/', en: '/en/privacy/', de: '/de/datenschutz/', ar: '/ar/privacy/' },
};

export function href(lang: Lang, page: PageKey): string {
  return ROUTES[page][lang];
}

/** Interface text: the Dutch sentence is the key; the table holds the other three. */
export function t(lang: Lang, nl: string): string {
  if (lang === 'nl') return nl;
  const row = TR[nl];
  if (!row) throw new Error(`No translation for: ${nl}`);
  return row[LANGS.indexOf(lang) - 1];
}

/** Pick the right language from a {nl, en, de, ar} record. */
export function pick<T>(lang: Lang, text: Record<Lang, T>): T {
  return text[lang];
}

export function dir(lang: Lang): 'rtl' | 'ltr' {
  return lang === 'ar' ? 'rtl' : 'ltr';
}
