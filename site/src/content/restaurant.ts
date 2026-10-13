// Facts about the restaurant. Everything here came from Rebeka's project
// notes and the restaurant's own channels (phone, e-mail, social media). `null` means "not supplied yet": the page shows a marked placeholder.

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
  phone: '053 432 8444' as string | null,
  phoneIntl: '+31534328444',
  email: 'info@habibienschede.nl' as string | null,
  instagram: 'https://www.instagram.com/habibi_enschede/',
  facebook: 'https://www.facebook.com/HabibiLibaneesRestaurant',
  tiktok: 'https://www.tiktok.com/@habibi_enschede',
  seats: { restaurant: 120, binnentuin: 134 },
  // Where the restaurant is, from OpenStreetMap (the map entry "Habibi", Wethouder Beversstraat 185).
  // Used by search engines and for the map picture.
  geo: { latitude: 52.2067135, longitude: 6.8916213 } as { latitude: number; longitude: number } | null,
} as const;
