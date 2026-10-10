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
    pageTitle: 'Dashboard',
    title: 'Komende 14 dagen',
    checking: 'Even controleren of u bent ingelogd…',
    logout: 'Uitloggen',
    loading: 'Prognose laden…',
    noscript: 'Het dashboard werkt alleen als JavaScript aan staat in uw browser.',

    // {time} = 02:52, {day} = wo 7 okt, {model} = the name the forecast job gives itself.
    updatedToday: 'Prognose bijgewerkt vandaag om {time}.',
    updatedYesterday: 'Prognose bijgewerkt gisteren om {time}.',
    updatedOther: 'Prognose bijgewerkt op {day} om {time}.',
    model: 'Model: {model}.',
    placeholderModel: 'Dit zijn voorbeeldcijfers. De echte prognose volgt nog.',
    stale:
      'De prognose is al meer dan anderhalve dag niet bijgewerkt. De nachtelijke berekening is waarschijnlijk mislukt.',
    refresh: 'Vernieuwen',
    refreshing: 'Bezig met vernieuwen…',
    hint: 'Kies een dag om de bezetting aan te passen of een notitie te maken.',

    columns: { guests: 'Gasten', servers: 'Bediening', cooks: 'Keuken', weather: 'Weer' },
    today: 'vandaag',
    guests: 'gasten',
    noForecast: 'Geen prognose',
    // Shown under a number the manager changed. {n} = the forecast's number.
    forecastWas: 'prognose {n}',
    noteLabel: 'Notitie:',
    noWeatherYet: 'Het weer is nog niet beschikbaar.',
    weather: {
      forecast: 'Weersverwachting',
      measured: 'Gemeten weer',
      unknown: 'Geen weergegevens voor deze dag.',
      dry: 'droog',
      max: 'maximaal {n} °C',
      rain: '{n} regen',
      wind: 'wind tot {n} km/u',
      sun: '{n} uur zon',
    },

    noRestaurantTitle: 'Nog geen restaurant gekoppeld',
    noRestaurant:
      'Uw account is nog niet aan een restaurant gekoppeld. Vraag de beheerder om u toe te voegen.',
    emptyTitle: 'Nog geen prognose',
    empty:
      'Er is nog geen prognose voor de komende 14 dagen. De prognose wordt elke nacht berekend. U kunt per dag al wel uw eigen bezetting invullen.',
    loadErrorTitle: 'De gegevens zijn niet geladen',
    loadError: 'De server gaf geen antwoord of weigerde de aanvraag.',
    offlineTitle: 'Geen verbinding',
    retry: 'Opnieuw proberen',

    editor: {
      // {day} = zaterdag 10 oktober
      title: 'Bezetting voor {day}',
      servers: 'Bediening',
      cooks: 'Keuken',
      less: 'één minder',
      more: 'één meer',
      forecastHint: 'Prognose: {n}',
      noForecastHint: 'Geen prognose',
      note: 'Notitie',
      noteHint: 'Optioneel. Zet hier geen namen of telefoonnummers in.',
      save: 'Opslaan',
      saving: 'Bezig met opslaan…',
      saved: 'Opgeslagen.',
      remove: 'Terug naar de prognose',
      removed: 'Uw aanpassing is verwijderd. De prognose geldt weer.',
      nothingToSave: 'Er is niets aangepast. De prognose geldt.',
      // {when} = vandaag om 21:14 / op vr 9 okt om 21:14
      changedAt: 'Laatst aangepast {when}.',
      whenToday: 'vandaag om {time}',
      whenYesterday: 'gisteren om {time}',
      whenOther: 'op {day} om {time}',
      invalid: 'Vul een heel getal van 0 tot 99 in, of laat het veld leeg.',
      saveFailed: 'Niet opgeslagen. De server weigerde de wijziging. Probeer het opnieuw.',
      saveOffline: 'Niet opgeslagen: geen verbinding. Controleer uw internet en probeer het opnieuw.',
    },
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
