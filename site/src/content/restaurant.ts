// Facts about the restaurant. Everything here came from Rebeka's project
// notes. `null` means "not supplied yet": the page shows a marked placeholder.

export const restaurant = {
  name: 'Restaurant Habibi',
  shortName: 'Habibi',
  street: 'Wethouder Beversstraat 185',
  postcode: '7543 BK',
  city: 'Enschede',
  currentWebsite: 'https://habibienschede.nl',
  currentWebsiteLabel: 'habibienschede.nl',
  // The restaurant's TheFork booking page. Every reserve button is a plain
  // link to it. It is never embedded, so nothing from TheFork loads on our pages.
  bookingUrl:
    'https://widget.thefork.com/nl/b248b8ae-4043-4bc2-ad8b-5c5d4979147c?step=date&utm_source=habibienschede.nl',
  bookingProvider: 'TheFork',
  // A plain link to a map. Nothing from the map provider loads on our pages.
  mapUrl:
    'https://www.google.com/maps/search/?api=1&query=Restaurant+Habibi%2C+Wethouder+Beversstraat+185%2C+7543+BK+Enschede',
  phone: null as string | null,
  email: null as string | null,
  seats: { restaurant: 120, binnentuin: 134 },
} as const;
