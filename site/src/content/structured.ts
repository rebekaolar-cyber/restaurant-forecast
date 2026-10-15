// Structured data for search engines (schema.org, as JSON-LD).
// Google and others read this to show the address, opening hours, the booking
// link and the menu in search results. It only repeats facts that are already
// on the pages: nothing here is new information.

import { LANGS, ROUTES, type Lang } from './i18n';
import { restaurant } from './restaurant';
import { week, clock } from './hours';
import { categories, type Dish, type Section } from './menu';
import { t } from './i18n';

const SITE = 'https://www.habibienschede.nl';
const abs = (path: string) => new URL(path, SITE).href;

const DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];

/** Opening hours as schema.org wants them. Friday and Saturday close at 01:00 the next morning. */
function hours() {
  return week.map((d, i) => ({
    '@type': 'OpeningHoursSpecification',
    dayOfWeek: `https://schema.org/${DAYS[i]}`,
    opens: clock(d.open),
    closes: clock(d.close),
  }));
}

/** The restaurant itself: name, address, hours, contact and the booking link. */
export function restaurantLd(lang: Lang) {
  return {
    '@context': 'https://schema.org',
    '@type': 'Restaurant',
    '@id': `${SITE}/#restaurant`,
    name: restaurant.name,
    url: abs(ROUTES.home[lang]),
    image: abs('/og.jpg'),
    servesCuisine: ['Lebanese', 'Middle Eastern'],
    address: {
      '@type': 'PostalAddress',
      streetAddress: restaurant.street,
      postalCode: restaurant.postcode,
      addressLocality: restaurant.city,
      addressCountry: 'NL',
    },
    ...(restaurant.geo && {
      geo: { '@type': 'GeoCoordinates', latitude: restaurant.geo.latitude, longitude: restaurant.geo.longitude },
    }),
    ...(restaurant.phone && { telephone: restaurant.phoneIntl }),
    ...(restaurant.email && { email: restaurant.email }),
    openingHoursSpecification: hours(),
    acceptsReservations: restaurant.bookingUrl,
    hasMenu: abs(ROUTES.menu[lang]),
    sameAs: [restaurant.instagram, restaurant.facebook, restaurant.tiktok],
    availableLanguage: LANGS.map((l) => l),
  };
}

const DIET: Record<string, string> = {
  gf: 'https://schema.org/GlutenFreeDiet',
  veg: 'https://schema.org/VegetarianDiet',
  vegan: 'https://schema.org/VeganDiet',
};

/** "8.5" -> "8.50". Prices the card photo did not show are left out. */
function offer(price: string | null) {
  if (!price || !/^\d+(\.\d+)?$/.test(price)) return undefined;
  return { '@type': 'Offer', price: Number(price).toFixed(2), priceCurrency: 'EUR' };
}

function clean(text: string): string {
  // "{?}" marks a word the card photo did not show; search engines get the text without it.
  return text.replace(/\s*\{\?\}\s*/g, ' ').replace(/\s+/g, ' ').trim();
}

function item(lang: Lang, dish: Dish, fallbackName: string) {
  const o = offer(dish.price);
  const desc = dish.desc ? clean(dish.desc[lang]) : '';
  return {
    '@type': 'MenuItem',
    name: dish.name ?? fallbackName,
    ...(desc && { description: desc }),
    ...(o && { offers: o }),
    ...(dish.icons.length && { suitableForDiet: dish.icons.map((k) => DIET[k]) }),
  };
}

function section(lang: Lang, sec: Section) {
  const title = sec.title[lang];
  return {
    '@type': 'MenuSection',
    name: title,
    hasMenuItem: sec.items.map((d) => item(lang, d, title)),
  };
}

/** The whole menu card, with a section per part of the card. */
export function menuLd(lang: Lang) {
  return {
    '@context': 'https://schema.org',
    '@type': 'Menu',
    '@id': `${abs(ROUTES.menu[lang])}#menu`,
    name: `${restaurant.name}: ${t(lang, 'Menu')}`,
    url: abs(ROUTES.menu[lang]),
    inLanguage: lang,
    hasMenuSection: categories.map((cat) => ({
      '@type': 'MenuSection',
      name: cat.label[lang],
      hasMenuSection: cat.sections.flat().map((s) => section(lang, s)),
    })),
  };
}
