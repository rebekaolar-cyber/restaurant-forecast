// Dutch text for the staff pages: login, choosing a password, dashboard.
// The pages read it when the site is built; the scripts on those pages read it
// in the browser. Public pages never load this file.

export const staffText = {
  login: {
    title: 'Inloggen',
    intro: 'Voor medewerkers van Restaurant Habibi met een uitnodiging.',
    email: 'E-mailadres',
    password: 'Wachtwoord',
    show: 'Toon',
    hide: 'Verberg',
    submit: 'Inloggen',
    busy: 'Bezig met inloggen…',
    forgot: 'Wachtwoord vergeten?',
    noAccount: 'Nog geen account? Vraag de beheerder om een uitnodiging.',
    backToSite: 'Terug naar de website',
    noscript: 'Inloggen werkt alleen als JavaScript aan staat in uw browser.',
  },
  reset: {
    title: 'Wachtwoord vergeten',
    intro:
      'Vul uw e-mailadres in. U krijgt een e-mail met een link waarmee u een nieuw wachtwoord kiest.',
    submit: 'Stuur de link',
    busy: 'Bezig met versturen…',
    sent: 'Als dit e-mailadres bij een account hoort, is er een e-mail met een link verstuurd. Kijk ook in uw map met ongewenste e-mail.',
    back: 'Terug naar inloggen',
  },
  setPassword: {
    title: 'Kies een wachtwoord',
    intro: 'Kies een wachtwoord van minstens 8 tekens. Daarmee logt u voortaan in.',
    password: 'Nieuw wachtwoord',
    repeat: 'Herhaal het wachtwoord',
    submit: 'Wachtwoord opslaan',
    busy: 'Bezig met opslaan…',
    saved: 'Uw wachtwoord is opgeslagen. U gaat nu naar het dashboard.',
    checking: 'De link wordt gecontroleerd…',
    expiredTitle: 'Deze link werkt niet meer',
    expired: 'De link is verlopen of al een keer gebruikt. Vraag een nieuwe link aan.',
    request: 'Nieuwe link aanvragen',
  },
  dashboard: {
    title: 'Dashboard',
    checking: 'Even controleren of u bent ingelogd…',
    logout: 'Uitloggen',
    // {restaurant} is replaced with the restaurant's name from the database.
    loggedInFor: 'Ingelogd voor {restaurant}',
    loading: 'Gegevens laden…',
    noRestaurantTitle: 'Nog geen restaurant gekoppeld',
    noRestaurant:
      'Uw account is nog niet aan een restaurant gekoppeld. Vraag de beheerder om u toe te voegen.',
    loadErrorTitle: 'De gegevens zijn niet geladen',
    loadError: 'De server gaf geen antwoord of weigerde de aanvraag.',
    offlineTitle: 'Geen verbinding',
    retry: 'Opnieuw proberen',
    comingWanted:
      'De prognose voor de komende 14 dagen: verwachte gasten, aanbevolen bediening en keuken, en het weer. Volgt in fase 3.',
    noscript: 'Het dashboard werkt alleen als JavaScript aan staat in uw browser.',
  },
  errors: {
    invalidCredentials: 'Het e-mailadres of het wachtwoord klopt niet.',
    notConfirmed: 'Dit account is nog niet bevestigd. Open eerst de link in de uitnodigingsmail.',
    tooMany: 'Te veel pogingen. Wacht een paar minuten en probeer het opnieuw.',
    network:
      'Geen verbinding met de server. Controleer uw internetverbinding en probeer het opnieuw.',
    generic: 'Dat is niet gelukt. Probeer het opnieuw.',
    mismatch: 'De twee wachtwoorden zijn niet gelijk.',
    tooShort: 'Het wachtwoord moet minstens 8 tekens hebben.',
    weak: 'Dit wachtwoord is te zwak. Kies een langer of minder voor de hand liggend wachtwoord.',
    same: 'Kies een ander wachtwoord dan uw huidige.',
    emailRate:
      'Er is kort geleden al een e-mail verstuurd. Wacht een paar minuten en probeer het opnieuw.',
  },
} as const;
