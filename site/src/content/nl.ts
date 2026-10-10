// All Dutch text of the public pages lives here (plus four short sentences in
// nl.status.ts), so a second language is one more pair of files of the same shape. Text that states facts (hours, address, seats)
// is filled in from restaurant.ts and hours.ts, not typed twice.
//
// Written for this test version from Rebeka's project notes. Replace with the
// restaurant's own words when they arrive.

import { restaurant } from './restaurant';
import { statusText } from './nl.status';

const { seats } = restaurant;

export const nl = {
  lang: 'nl',
  siteName: restaurant.name,

  nav: {
    label: 'Hoofdmenu',
    home: 'Home',
    menu: 'Menu',
    about: 'Over ons',
    contact: 'Contact',
    privacy: 'Privacy',
    skip: 'Naar de inhoud',
  },

  reserve: {
    button: 'Reserveer een tafel',
    short: 'Reserveren',
    note: `U reserveert in het reserveringssysteem op ${restaurant.currentWebsiteLabel}.`,
  },

  testBanner: {
    text: 'Dit is een testversie. De officiële website van Restaurant Habibi is',
  },

  placeholder: {
    tag: 'Placeholder',
  },

  days: ['Maandag', 'Dinsdag', 'Woensdag', 'Donderdag', 'Vrijdag', 'Zaterdag', 'Zondag'],
  daysShort: ['Ma', 'Di', 'Wo', 'Do', 'Vr', 'Za', 'Zo'],

  hours: {
    title: 'Openingstijden',
    everyDay: 'Elke dag open voor diner',
    late: 'Op vrijdag en zaterdag zijn we open tot 01:00.',
    status: statusText, // see nl.status.ts
  },

  address: {
    title: 'Adres',
    map: 'Bekijk op de kaart',
    mapNote: 'Opent Google Maps.',
  },

  home: {
    title: 'Restaurant Habibi, Enschede',
    description:
      'Libanees restaurant Habibi in Enschede is elke dag open voor diner, binnen of in de binnentuin. Bekijk de openingstijden en reserveer een tafel.',
    heading: 'Elke avond diner, binnen of in de binnentuin',
    lead: 'Libanees restaurant Habibi aan de Wethouder Beversstraat in Enschede is zeven dagen per week open.',
    menuLink: 'Bekijk het menu',
    rooms: {
      title: 'Twee plekken om te zitten',
      restaurant: {
        title: 'Het restaurant',
        text: `Binnen is plaats voor ${seats.restaurant} gasten.`,
      },
      binnentuin: {
        title: 'De binnentuin',
        text: `De binnentuin heeft ${seats.binnentuin} plaatsen en is het hele jaar open.`,
      },
    },
    visit: {
      title: 'Openingstijden en adres',
    },
  },

  menu: {
    title: 'Menu',
    description: 'Het menu van Libanees restaurant Habibi in Enschede.',
    heading: 'Menu',
    empty: {
      wanted:
        'Het volledige menu: secties, gerechten, omschrijvingen, prijzen en allergeneninformatie, overgenomen van de huidige kaart.',
      meanwhile: 'Het actuele menu staat op',
      layoutTitle: 'Zo komt het menu eruit te zien',
      sampleSection: 'Naam van de sectie',
      sampleItem: 'Naam van het gerecht',
      sampleDescription: 'Korte omschrijving van het gerecht.',
      samplePrice: '€ 0,00',
    },
  },

  about: {
    title: 'Over ons',
    description: 'Over Restaurant Habibi in Enschede: het restaurant, de binnentuin en de openingstijden.',
    heading: 'Over Habibi',
    storyWanted:
      'Het verhaal van het restaurant in twee of drie alinea’s: de keuken, de mensen erachter en sinds wanneer. Overnemen van de huidige website of aanleveren door de eigenaar.',
    facts: {
      title: 'In het kort',
      open: { term: 'Open', value: 'Elke dag, alleen voor diner' },
      seats: {
        term: 'Plaatsen',
        value: `${seats.restaurant} binnen en ${seats.binnentuin} in de binnentuin`,
      },
      garden: { term: 'Binnentuin', value: 'Het hele jaar open' },
      address: { term: 'Adres' },
    },
  },

  contact: {
    title: 'Contact',
    description:
      'Adres, openingstijden en routelink van Restaurant Habibi, Wethouder Beversstraat 185 in Enschede.',
    heading: 'Contact',
    reserveTitle: 'Reserveren',
    reachTitle: 'Telefoon en e-mail',
    phone: 'Telefoon',
    email: 'E-mail',
    reachWanted: 'Telefoonnummer en e-mailadres van het restaurant.',
  },

  privacy: {
    title: 'Privacyverklaring',
    description: 'Hoe de website van Restaurant Habibi met uw gegevens omgaat.',
    heading: 'Privacyverklaring',
    updated: 'Laatst bijgewerkt op 10 oktober 2026.',
    intro:
      'Deze website is gemaakt om zo weinig mogelijk over u te weten. Hieronder staat wat er wel en niet gebeurt wanneer u de website bezoekt.',
    sections: [
      {
        heading: 'Wie is verantwoordelijk',
        paragraphs: [
          `${restaurant.name}, ${restaurant.street}, ${restaurant.postcode} ${restaurant.city}, is verantwoordelijk voor deze website.`,
        ],
        wanted:
          'Officiële bedrijfsnaam, KvK-nummer en een e-mailadres voor vragen over privacy.',
      },
      {
        heading: 'Wat deze website niet doet',
        paragraphs: [
          'Deze website plaatst geen cookies, gebruikt geen statistiek- of advertentieprogramma’s en laadt geen onderdelen van andere partijen. Ook de lettertypen komen van onze eigen website.',
          'Er staan geen formulieren op de website. U laat hier dus geen naam, telefoonnummer of e-mailadres achter.',
        ],
      },
      {
        heading: 'Wat er technisch nodig is',
        paragraphs: [
          'De website staat bij hostingbedrijf Cloudflare. Om een pagina te kunnen tonen en misbruik te voorkomen verwerkt Cloudflare bij elk bezoek technische gegevens, zoals uw IP-adres en het type browser. Wij gebruiken die gegevens niet om bezoekers te volgen of te herkennen.',
        ],
      },
      {
        heading: 'Reserveren',
        paragraphs: [
          `De knop “Reserveer een tafel” brengt u naar het reserveringssysteem op ${restaurant.currentWebsiteLabel}. De gegevens die u daar invult, worden door dat systeem verwerkt. Daarvoor geldt de privacyverklaring die u daar vindt.`,
        ],
      },
      {
        heading: 'Links naar andere websites',
        paragraphs: [
          'De kaartlink opent Google Maps. Pas wanneer u op die link klikt, gaat u naar de website van Google, waar de voorwaarden van Google gelden.',
        ],
      },
      {
        heading: 'Uw rechten',
        paragraphs: [
          'U mag ons vragen welke gegevens wij van u hebben en u mag ze laten verbeteren of verwijderen. Bent u het niet eens met hoe wij met gegevens omgaan, dan kunt u een klacht indienen bij de Autoriteit Persoonsgegevens.',
        ],
      },
    ],
  },

  notFound: {
    title: 'Pagina niet gevonden',
    heading: 'Deze pagina bestaat niet',
    text: 'De link is verouderd of het adres is verkeerd getypt.',
    home: 'Ga naar de homepage',
  },

  logoAlt: 'Restaurant Habibi, the taste of Lebanon',

  footer: {
    navLabel: 'Pagina’s',
    through: 't/m',
  },
} as const;

export type Copy = typeof nl;
