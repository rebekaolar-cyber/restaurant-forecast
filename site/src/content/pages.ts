// Page text of the public site in Dutch, English, German and Arabic.
// Short interface words (menu labels, day names, buttons) are in strings.ts.
// Dutch is the restaurant's own text or Rebeka's; English, German and Arabic are
// our translations and still need a check by a native speaker.
// Facts (address, phone, hours, seats) come from restaurant.ts and hours.ts.

import type { Lang } from './i18n';
import { restaurant } from './restaurant';

const { seats } = restaurant;

const nl = {
  skip: 'Naar de inhoud',
  mainNav: 'Hoofdmenu',
  menuParts: 'Onderdelen van de menukaart',
  testLabel: 'Testversie',
  testBanner: 'Dit is een testversie van de nieuwe website. De officiële website is',
  photoToCome: 'Foto volgt',
  pricesInEuro: 'Alle prijzen in euro.',
  priceUnread: 'onleesbaar',
  staffLogin: 'Inloggen voor medewerkers',
  pagesNav: 'Pagina’s',
  phone: 'Telefoon',
  email: 'E-mail',
  address: 'Adres',
  bookVia: `Reserveren gaat via ${restaurant.bookingProvider}, het reserveringssysteem van het restaurant.`,
  mapAlt: 'Kaart van de Wethouder Beversstraat in Enschede met Restaurant Habibi',
  mapCredit: 'Kaart',
  mapToCome: 'Kaart volgt',
  status: {
    opensToday: 'Vandaag open van {open} tot {close}',
    openNow: 'Nu open, tot {close}',
    closedOpensToday: 'Nu gesloten. Vandaag open vanaf {open}',
    closedOpensTomorrow: 'Nu gesloten. Morgen open vanaf {open}',
  },
  meta: {
    home: {
      title: 'Restaurant Habibi, Libanees restaurant in Enschede',
      description: 'Libanees restaurant Habibi in Enschede: elke avond open voor diner, binnen of in de binnentuin. Bekijk het menu en reserveer een tafel.',
    },
    menu: {
      title: 'Menu',
      description: 'Het menu van Restaurant Habibi in Enschede: koude en warme maza, gerechten van de houtskoolgrill, desserts en dranken, met prijzen en allergeneninformatie.',
    },
    about: {
      title: 'Over ons',
      description: 'Restaurant Habibi in Enschede: Libanese gerechten naar familierecepten, een restaurant en een binnentuin die het hele jaar open is.',
    },
    contact: {
      title: 'Contact en route',
      description: 'Adres, telefoonnummer, e-mail en openingstijden van Restaurant Habibi, Wethouder Beversstraat 185 in Enschede.',
    },
    privacy: {
      title: 'Privacyverklaring',
      description: 'Hoe de website van Restaurant Habibi met uw gegevens omgaat: geen cookies, geen statistiek, geen formulieren.',
    },
    notFound: { title: 'Pagina niet gevonden' },
  },
  about: {
    lead: 'Heerlijk uitgebreid tafelen? Dat doe je bij Habibi.',
    cardEyebrow: 'Uit onze menukaart',
    card: [
      'Onze met zeer veel liefde gemaakte gerechten, zijn geïnspireerd op recepten die in onze familie al sinds vele generaties in gebruik zijn. Al deze gerechten zijn gebaseerd op de Libanese/Arabische keuken. Deze is ontstaan vanuit allerlei invloeden uit het midden oosten.',
      'Op onze menukaart staan, naast onze reguliere gerechten, onder andere een aantal warme en koude kleine gerechten die ook wel “Maza” genoemd worden. Deze kleine gerechten, waarvan sommige ook zeer geschikt zijn voor vegetariërs, kunnen met het hele tafelgezelschap genuttigd en gedeeld worden.',
      'Ook kunt u natuurlijk kiezen uit verschillende vlees gerechten, waarvan een groot deel op onze authentieke houtskool-grill bereid worden.',
      'Mocht u nog vragen hebben over onze gerechten, dan kunt u hiervoor natuurlijk terecht bij een van onze medewerkers. Heeft u een voedselallergie? Vraag naar onze allergenenkaart!',
    ],
    factsTitle: 'In het kort',
    facts: {
      open: ['Open', 'Elke dag, voor diner'],
      seats: ['Plaatsen', `${seats.restaurant} binnen en ${seats.binnentuin} in de binnentuin`],
      garden: ['Binnentuin', 'Het hele jaar open'],
      address: 'Adres',
    },
  },
  contact: {
    lead: 'Je vindt ons aan de Wethouder Beversstraat in Enschede. Bellen of mailen mag altijd; een tafel reserveer je het snelst online.',
    reserveTitle: 'Reserveren',
  },
  privacy: {
    updated: 'Laatst bijgewerkt op 13 oktober 2026.',
    intro: 'Deze website is gemaakt om zo weinig mogelijk over u te weten. Hieronder staat wat er wel en niet gebeurt wanneer u de website bezoekt.',
    wanted: 'Nog aan te vullen door de eigenaar: officiële bedrijfsnaam, KvK-nummer en een e-mailadres voor vragen over privacy.',
    sections: [
      ['Wie is verantwoordelijk', [`${restaurant.name}, ${restaurant.street}, ${restaurant.postcode} ${restaurant.city}, is verantwoordelijk voor deze website.`]],
      ['Wat deze website niet doet', [
        'Deze website plaatst geen cookies, gebruikt geen statistiek- of advertentieprogramma’s en laadt geen onderdelen van andere partijen. Ook de lettertypen en de kaart komen van onze eigen website.',
        'Op de openbare pagina’s staan geen formulieren. Als gast laat u hier dus geen naam, telefoonnummer of e-mailadres achter.',
      ]],
      ['Wat er technisch nodig is', [
        'De website staat bij hostingbedrijf Cloudflare. Om een pagina te kunnen tonen en misbruik te voorkomen verwerkt Cloudflare bij elk bezoek technische gegevens, zoals uw IP-adres en het type browser. Wij gebruiken die gegevens niet om bezoekers te volgen of te herkennen.',
      ]],
      ['Reserveren, bellen en mailen', [
        `De knop “Reserveren” brengt u naar ${restaurant.bookingProvider}, het reserveringssysteem dat het restaurant gebruikt. De gegevens die u daar invult, worden door ${restaurant.bookingProvider} verwerkt; daarvoor geldt de privacyverklaring van ${restaurant.bookingProvider}. Het reserveringssysteem staat niet op onze eigen pagina’s.`,
        'Een klik op het telefoonnummer of het e-mailadres opent alleen de telefoon- of e-mailapp op uw eigen apparaat.',
      ]],
      ['Inloggen voor medewerkers', [
        'Medewerkers met een uitnodiging kunnen inloggen op een afgeschermd dashboard. Daarvoor bewaren wij hun e-mailadres en een versleuteld wachtwoord bij onze databaseleverancier Supabase, op servers in de Europese Unie (Frankfurt). Alleen de inlogpagina en het dashboard maken verbinding met Supabase, de openbare pagina’s niet.',
        'Na het inloggen bewaart de browser een inlogsleutel op het eigen apparaat, zodat de medewerker ingelogd blijft. Die sleutel is alleen voor het inloggen en wordt niet gebruikt om iemand te volgen. Met “Uitloggen” wordt hij verwijderd.',
      ]],
      ['Links naar andere websites', [
        'De kaart is een afbeelding op onze eigen website, gemaakt van OpenStreetMap. Pas wanneer u op de kaart of op “Route plannen” klikt, gaat u naar Google Maps, waar de voorwaarden van Google gelden. Hetzelfde geldt voor de links naar Instagram, Facebook en TikTok.',
      ]],
      ['Uw rechten', [
        'U mag ons vragen welke gegevens wij van u hebben en u mag ze laten verbeteren of verwijderen. Bent u het niet eens met hoe wij met gegevens omgaan, dan kunt u een klacht indienen bij de Autoriteit Persoonsgegevens.',
      ]],
    ] as [string, string[]][],
  },
  notFound: {
    heading: 'Deze pagina bestaat niet',
    text: 'De link is verouderd of het adres is verkeerd getypt.',
    home: 'Naar de homepage',
  },
};

export type PageCopy = typeof nl;

const en: PageCopy = {
  skip: 'Skip to content',
  mainNav: 'Main menu',
  menuParts: 'Parts of the menu',
  testLabel: 'Test version',
  testBanner: 'This is a test version of the new website. The official website is',
  photoToCome: 'Photo to come',
  pricesInEuro: 'All prices in euros.',
  priceUnread: 'unreadable',
  staffLogin: 'Staff login',
  pagesNav: 'Pages',
  phone: 'Phone',
  email: 'Email',
  address: 'Address',
  bookVia: `Bookings go through ${restaurant.bookingProvider}, the restaurant’s booking system.`,
  mapAlt: 'Map of Wethouder Beversstraat in Enschede showing Restaurant Habibi',
  mapCredit: 'Map',
  mapToCome: 'Map to come',
  status: {
    opensToday: 'Open today from {open} to {close}',
    openNow: 'Open now, until {close}',
    closedOpensToday: 'Closed now. Open today from {open}',
    closedOpensTomorrow: 'Closed now. Open tomorrow from {open}',
  },
  meta: {
    home: {
      title: 'Restaurant Habibi, Lebanese restaurant in Enschede',
      description: 'Lebanese restaurant Habibi in Enschede: open every evening for dinner, inside or in the courtyard garden. See the menu and book a table.',
    },
    menu: {
      title: 'Menu',
      description: 'The menu of Restaurant Habibi in Enschede: cold and hot maza, dishes from the charcoal grill, desserts and drinks, with prices and allergen information.',
    },
    about: {
      title: 'About us',
      description: 'Restaurant Habibi in Enschede: Lebanese dishes from family recipes, a dining room and a courtyard garden that is open all year.',
    },
    contact: {
      title: 'Contact and directions',
      description: 'Address, phone number, email and opening hours of Restaurant Habibi, Wethouder Beversstraat 185 in Enschede.',
    },
    privacy: {
      title: 'Privacy statement',
      description: 'How the Restaurant Habibi website handles your data: no cookies, no analytics, no forms.',
    },
    notFound: { title: 'Page not found' },
  },
  about: {
    lead: 'Love a long, leisurely dinner? That’s what Habibi is for.',
    cardEyebrow: 'From our menu card',
    card: [
      'Our dishes, made with a great deal of love, are inspired by recipes that our family has used for many generations. They are all based on Lebanese and Arab cooking, which grew out of many influences from across the Middle East.',
      'Besides our regular dishes, the menu has a number of small hot and cold dishes known as “maza”. They are made to be shared by the whole table, and several are well suited to vegetarians.',
      'You can of course also choose from a range of meat dishes, many of them prepared on our authentic charcoal grill.',
      'If you have any questions about our dishes, just ask one of our staff. Do you have a food allergy? Ask for our allergen menu!',
    ],
    factsTitle: 'At a glance',
    facts: {
      open: ['Open', 'Every day, for dinner'],
      seats: ['Seats', `${seats.restaurant} inside and ${seats.binnentuin} in the courtyard garden`],
      garden: ['Courtyard garden', 'Open all year'],
      address: 'Address',
    },
  },
  contact: {
    lead: 'You’ll find us on Wethouder Beversstraat in Enschede. Feel free to call or email; booking a table is quickest online.',
    reserveTitle: 'Book a table',
  },
  privacy: {
    updated: 'Last updated on 13 October 2026.',
    intro: 'This website is built to know as little about you as possible. Below is what does and does not happen when you visit it.',
    wanted: 'Still to be added by the owner: the official company name, the Chamber of Commerce (KvK) number and an email address for privacy questions.',
    sections: [
      ['Who is responsible', [`${restaurant.name}, ${restaurant.street}, ${restaurant.postcode} ${restaurant.city}, is responsible for this website.`]],
      ['What this website does not do', [
        'This website sets no cookies, uses no analytics or advertising tools and loads nothing from other parties. The fonts and the map also come from our own website.',
        'There are no forms on the public pages, so as a guest you leave no name, phone number or email address here.',
      ]],
      ['What is technically needed', [
        'The website is hosted by Cloudflare. To show a page and prevent abuse, Cloudflare processes technical data on every visit, such as your IP address and browser type. We do not use this data to follow or recognise visitors.',
      ]],
      ['Booking, calling and emailing', [
        `The “Book a table” button takes you to ${restaurant.bookingProvider}, the booking system the restaurant uses. ${restaurant.bookingProvider} processes the details you enter there, under ${restaurant.bookingProvider}’s own privacy statement. The booking system is not part of our own pages.`,
        'Clicking the phone number or email address only opens the phone or email app on your own device.',
      ]],
      ['Staff login', [
        'Invited staff can log in to a protected dashboard. For this we keep their email address and an encrypted password with our database provider Supabase, on servers in the European Union (Frankfurt). Only the login page and the dashboard connect to Supabase, the public pages do not.',
        'After logging in, the browser keeps a login key on the staff member’s own device so they stay logged in. It is used for logging in only, never to follow anyone, and “Log out” removes it.',
      ]],
      ['Links to other websites', [
        'The map is an image on our own website, made from OpenStreetMap. Only when you click the map or “Get directions” do you go to Google Maps, where Google’s terms apply. The same goes for the links to Instagram, Facebook and TikTok.',
      ]],
      ['Your rights', [
        'You may ask us what data we hold about you and have it corrected or deleted. If you disagree with how we handle data, you can complain to the Dutch Data Protection Authority (Autoriteit Persoonsgegevens).',
      ]],
    ],
  },
  notFound: {
    heading: 'This page does not exist',
    text: 'The link is out of date or the address was mistyped.',
    home: 'Go to the homepage',
  },
};

const de: PageCopy = {
  skip: 'Zum Inhalt',
  mainNav: 'Hauptmenü',
  menuParts: 'Teile der Speisekarte',
  testLabel: 'Testversion',
  testBanner: 'Dies ist eine Testversion der neuen Website. Die offizielle Website ist',
  photoToCome: 'Foto folgt',
  pricesInEuro: 'Alle Preise in Euro.',
  priceUnread: 'unleserlich',
  staffLogin: 'Login für Mitarbeiter',
  pagesNav: 'Seiten',
  phone: 'Telefon',
  email: 'E-Mail',
  address: 'Adresse',
  bookVia: `Reservierungen laufen über ${restaurant.bookingProvider}, das Reservierungssystem des Restaurants.`,
  mapAlt: 'Karte der Wethouder Beversstraat in Enschede mit dem Restaurant Habibi',
  mapCredit: 'Karte',
  mapToCome: 'Karte folgt',
  status: {
    opensToday: 'Heute geöffnet von {open} bis {close}',
    openNow: 'Jetzt geöffnet, bis {close}',
    closedOpensToday: 'Jetzt geschlossen. Heute ab {open} geöffnet',
    closedOpensTomorrow: 'Jetzt geschlossen. Morgen ab {open} geöffnet',
  },
  meta: {
    home: {
      title: 'Restaurant Habibi, libanesisches Restaurant in Enschede',
      description: 'Das libanesische Restaurant Habibi in Enschede: jeden Abend zum Abendessen geöffnet, drinnen oder im Innenhof. Speisekarte ansehen und Tisch reservieren.',
    },
    menu: {
      title: 'Speisekarte',
      description: 'Die Speisekarte des Restaurant Habibi in Enschede: kalte und warme Maza, Gerichte vom Holzkohlegrill, Desserts und Getränke, mit Preisen und Allergenen.',
    },
    about: {
      title: 'Über uns',
      description: 'Restaurant Habibi in Enschede: libanesische Gerichte nach Familienrezepten, ein Restaurant und ein Innenhof, der das ganze Jahr geöffnet ist.',
    },
    contact: {
      title: 'Kontakt und Anfahrt',
      description: 'Adresse, Telefon, E-Mail und Öffnungszeiten des Restaurant Habibi, Wethouder Beversstraat 185 in Enschede.',
    },
    privacy: {
      title: 'Datenschutzerklärung',
      description: 'Wie die Website des Restaurant Habibi mit Ihren Daten umgeht: keine Cookies, keine Statistik, keine Formulare.',
    },
    notFound: { title: 'Seite nicht gefunden' },
  },
  about: {
    lead: 'Gemütlich und ausgiebig tafeln? Das geht bei Habibi.',
    cardEyebrow: 'Aus unserer Speisekarte',
    card: [
      'Unsere mit viel Liebe zubereiteten Gerichte sind von Rezepten inspiriert, die in unserer Familie seit vielen Generationen verwendet werden. Sie alle beruhen auf der libanesisch-arabischen Küche, die aus vielen Einflüssen des Nahen Ostens entstanden ist.',
      'Neben unseren regulären Gerichten finden Sie auf der Karte kleine warme und kalte Gerichte, die „Maza“ genannt werden. Sie werden mit dem ganzen Tisch geteilt, und einige eignen sich besonders für Vegetarier.',
      'Natürlich können Sie auch aus verschiedenen Fleischgerichten wählen, von denen viele auf unserem authentischen Holzkohlegrill zubereitet werden.',
      'Haben Sie Fragen zu unseren Gerichten, wenden Sie sich gern an unsere Mitarbeiter. Sie haben eine Lebensmittelallergie? Fragen Sie nach unserer Allergenkarte!',
    ],
    factsTitle: 'Auf einen Blick',
    facts: {
      open: ['Geöffnet', 'Täglich, zum Abendessen'],
      seats: ['Plätze', `${seats.restaurant} drinnen und ${seats.binnentuin} im Innenhof`],
      garden: ['Innenhof', 'Das ganze Jahr geöffnet'],
      address: 'Adresse',
    },
  },
  contact: {
    lead: 'Sie finden uns in der Wethouder Beversstraat in Enschede. Rufen Sie gern an oder schreiben Sie uns; einen Tisch reservieren Sie am schnellsten online.',
    reserveTitle: 'Tisch reservieren',
  },
  privacy: {
    updated: 'Zuletzt aktualisiert am 13. Oktober 2026.',
    intro: 'Diese Website ist so gebaut, dass sie so wenig wie möglich über Sie weiß. Hier steht, was bei einem Besuch passiert und was nicht.',
    wanted: 'Vom Inhaber noch zu ergänzen: offizieller Firmenname, KvK-Nummer (Handelsregister) und eine E-Mail-Adresse für Datenschutzfragen.',
    sections: [
      ['Verantwortlich', [`${restaurant.name}, ${restaurant.street}, ${restaurant.postcode} ${restaurant.city}, ist für diese Website verantwortlich.`]],
      ['Was diese Website nicht tut', [
        'Diese Website setzt keine Cookies, nutzt keine Statistik- oder Werbeprogramme und lädt nichts von anderen Anbietern. Auch die Schriften und die Karte kommen von unserer eigenen Website.',
        'Auf den öffentlichen Seiten gibt es keine Formulare. Als Gast hinterlassen Sie hier also weder Namen noch Telefonnummer oder E-Mail-Adresse.',
      ]],
      ['Was technisch nötig ist', [
        'Die Website liegt beim Hosting-Anbieter Cloudflare. Um eine Seite anzuzeigen und Missbrauch zu verhindern, verarbeitet Cloudflare bei jedem Besuch technische Daten wie Ihre IP-Adresse und den Browsertyp. Wir nutzen diese Daten nicht, um Besucher zu verfolgen oder wiederzuerkennen.',
      ]],
      ['Reservieren, anrufen und mailen', [
        `Die Schaltfläche „Tisch reservieren“ bringt Sie zu ${restaurant.bookingProvider}, dem Reservierungssystem des Restaurants. Ihre dort eingegebenen Daten verarbeitet ${restaurant.bookingProvider} nach seiner eigenen Datenschutzerklärung. Das Reservierungssystem ist nicht Teil unserer Seiten.`,
        'Ein Klick auf die Telefonnummer oder die E-Mail-Adresse öffnet nur die Telefon- oder E-Mail-App auf Ihrem eigenen Gerät.',
      ]],
      ['Login für Mitarbeiter', [
        'Eingeladene Mitarbeiter können sich bei einem geschützten Dashboard anmelden. Dafür speichern wir ihre E-Mail-Adresse und ein verschlüsseltes Passwort bei unserem Datenbankanbieter Supabase, auf Servern in der Europäischen Union (Frankfurt). Nur die Login-Seite und das Dashboard verbinden sich mit Supabase, die öffentlichen Seiten nicht.',
        'Nach dem Login speichert der Browser einen Anmeldeschlüssel auf dem eigenen Gerät, damit die Person angemeldet bleibt. Er dient nur der Anmeldung, nie dem Verfolgen, und „Abmelden“ löscht ihn.',
      ]],
      ['Links zu anderen Websites', [
        'Die Karte ist ein Bild auf unserer eigenen Website, erstellt aus OpenStreetMap. Erst wenn Sie auf die Karte oder „Route planen“ klicken, gelangen Sie zu Google Maps, wo die Bedingungen von Google gelten. Dasselbe gilt für die Links zu Instagram, Facebook und TikTok.',
      ]],
      ['Ihre Rechte', [
        'Sie können uns fragen, welche Daten wir über Sie haben, und sie berichtigen oder löschen lassen. Wenn Sie mit unserem Umgang mit Daten nicht einverstanden sind, können Sie sich bei der niederländischen Datenschutzbehörde (Autoriteit Persoonsgegevens) beschweren.',
      ]],
    ],
  },
  notFound: {
    heading: 'Diese Seite gibt es nicht',
    text: 'Der Link ist veraltet oder die Adresse wurde falsch eingegeben.',
    home: 'Zur Startseite',
  },
};

const ar: PageCopy = {
  skip: 'انتقل إلى المحتوى',
  mainNav: 'القائمة الرئيسية',
  menuParts: 'أقسام القائمة',
  testLabel: 'نسخة تجريبية',
  testBanner: 'هذه نسخة تجريبية من الموقع الجديد. الموقع الرسمي هو',
  photoToCome: 'الصورة قريبًا',
  pricesInEuro: 'جميع الأسعار باليورو.',
  priceUnread: 'غير مقروء',
  staffLogin: 'دخول الموظفين',
  pagesNav: 'الصفحات',
  phone: 'الهاتف',
  email: 'البريد الإلكتروني',
  address: 'العنوان',
  bookVia: `يتم الحجز عبر ${restaurant.bookingProvider}، نظام الحجز الخاص بالمطعم.`,
  mapAlt: 'خريطة شارع فيتهاودر بيفرسسترات في إنسخيده ويظهر عليها مطعم حبيبي',
  mapCredit: 'الخريطة',
  mapToCome: 'الخريطة لاحقًا',
  status: {
    opensToday: 'مفتوح اليوم من {open} حتى {close}',
    openNow: 'مفتوح الآن حتى {close}',
    closedOpensToday: 'مغلق الآن. يفتح اليوم من {open}',
    closedOpensTomorrow: 'مغلق الآن. يفتح غدًا من {open}',
  },
  meta: {
    home: {
      title: 'مطعم حبيبي، مطعم لبناني في إنسخيده',
      description: 'مطعم حبيبي اللبناني في إنسخيده: مفتوح كل مساء لتناول العشاء، في الداخل أو في الحديقة الداخلية. تصفّحوا القائمة واحجزوا طاولة.',
    },
    menu: {
      title: 'القائمة',
      description: 'قائمة مطعم حبيبي في إنسخيده: مازة باردة وساخنة، أطباق من شواية الفحم، حلويات ومشروبات، مع الأسعار ومعلومات الحساسية.',
    },
    about: {
      title: 'من نحن',
      description: 'مطعم حبيبي في إنسخيده: أطباق لبنانية من وصفات العائلة، وقاعة طعام وحديقة داخلية مفتوحة طوال العام.',
    },
    contact: {
      title: 'التواصل والوصول',
      description: 'عنوان مطعم حبيبي ورقم الهاتف والبريد الإلكتروني وساعات العمل، فيتهاودر بيفرسسترات 185 في إنسخيده.',
    },
    privacy: {
      title: 'بيان الخصوصية',
      description: 'كيف يتعامل موقع مطعم حبيبي مع بياناتكم: لا ملفات تعريف ارتباط، ولا إحصاءات، ولا نماذج.',
    },
    notFound: { title: 'الصفحة غير موجودة' },
  },
  about: {
    lead: 'تحبّون السهرات الطويلة حول مائدة عامرة؟ هذا ما ستجدونه في حبيبي.',
    cardEyebrow: 'من قائمة طعامنا',
    card: [
      'أطباقنا المحضّرة بكثير من الحب مستوحاة من وصفات تستخدمها عائلتنا منذ أجيال عديدة. وكلها مبنية على المطبخ اللبناني والعربي الذي نشأ من تأثيرات متنوعة من أنحاء الشرق الأوسط.',
      'إلى جانب أطباقنا المعتادة، تضم القائمة أطباقًا صغيرة ساخنة وباردة تُعرف بـ«المازة». تُشارَك مع جميع من على الطاولة، وبعضها مناسب جدًا للنباتيين.',
      'ويمكنكم بالطبع الاختيار من بين أطباق لحوم متنوعة، يُحضَّر كثير منها على شواية الفحم الأصيلة لدينا.',
      'إذا كانت لديكم أسئلة عن أطباقنا، فاسألوا أحد العاملين لدينا. هل لديكم حساسية من طعام ما؟ اطلبوا قائمة مسببات الحساسية!',
    ],
    factsTitle: 'باختصار',
    facts: {
      open: ['مفتوح', 'كل يوم، لتناول العشاء'],
      seats: ['المقاعد', `${seats.restaurant} في الداخل و${seats.binnentuin} في الحديقة الداخلية`],
      garden: ['الحديقة الداخلية', 'مفتوحة طوال العام'],
      address: 'العنوان',
    },
  },
  contact: {
    lead: 'تجدوننا في شارع فيتهاودر بيفرسسترات في إنسخيده. يمكنكم الاتصال أو مراسلتنا في أي وقت، وأسرع طريقة لحجز طاولة هي عبر الإنترنت.',
    reserveTitle: 'احجزوا طاولة',
  },
  privacy: {
    updated: 'آخر تحديث: 13 أكتوبر 2026.',
    intro: 'صُمّم هذا الموقع ليعرف عنكم أقل قدر ممكن. فيما يلي ما يحدث وما لا يحدث عند زيارتكم له.',
    wanted: 'يُستكمل لاحقًا من قِبل المالك: الاسم الرسمي للشركة، ورقم السجل التجاري (KvK)، وبريد إلكتروني لأسئلة الخصوصية.',
    sections: [
      ['الجهة المسؤولة', [`${restaurant.name}، ${restaurant.street}، ${restaurant.postcode} ${restaurant.city}، هو المسؤول عن هذا الموقع.`]],
      ['ما لا يفعله هذا الموقع', [
        'لا يضع هذا الموقع ملفات تعريف ارتباط، ولا يستخدم برامج إحصاء أو إعلانات، ولا يحمّل أي شيء من جهات أخرى. حتى الخطوط والخريطة تأتي من موقعنا نفسه.',
        'لا توجد نماذج في الصفحات العامة، لذا لا تتركون هنا اسمًا أو رقم هاتف أو بريدًا إلكترونيًا.',
      ]],
      ['ما هو ضروري تقنيًا', [
        'يستضيف الموقعَ مزوّدُ الاستضافة Cloudflare. ولعرض الصفحة ومنع إساءة الاستخدام تعالج Cloudflare في كل زيارة بيانات تقنية مثل عنوان IP ونوع المتصفح. لا نستخدم هذه البيانات لتتبّع الزوار أو التعرّف عليهم.',
      ]],
      ['الحجز والاتصال والمراسلة', [
        `ينقلكم زر «احجزوا طاولة» إلى ${restaurant.bookingProvider}، نظام الحجز الذي يستخدمه المطعم. تعالج ${restaurant.bookingProvider} البيانات التي تدخلونها هناك وفق بيان الخصوصية الخاص بها. نظام الحجز ليس جزءًا من صفحاتنا.`,
        'النقر على رقم الهاتف أو البريد الإلكتروني يفتح فقط تطبيق الهاتف أو البريد على جهازكم.',
      ]],
      ['دخول الموظفين', [
        'يمكن للموظفين المدعوّين الدخول إلى لوحة تحكم محمية. لذلك نحفظ بريدهم الإلكتروني وكلمة مرور مشفّرة لدى مزوّد قاعدة البيانات Supabase على خوادم في الاتحاد الأوروبي (فرانكفورت). صفحة الدخول ولوحة التحكم فقط تتصلان بـ Supabase، أما الصفحات العامة فلا.',
        'بعد الدخول يحفظ المتصفح مفتاح دخول على جهاز الموظف نفسه ليبقى مسجّلًا. يُستخدم للدخول فقط ولا يُستخدم للتتبّع، ويحذفه زر «تسجيل الخروج».',
      ]],
      ['روابط إلى مواقع أخرى', [
        'الخريطة صورة على موقعنا نفسه مأخوذة من OpenStreetMap. فقط عند النقر على الخريطة أو «خطّطوا طريقكم» تنتقلون إلى خرائط Google حيث تسري شروط Google. والأمر نفسه ينطبق على روابط Instagram وFacebook وTikTok.',
      ]],
      ['حقوقكم', [
        'يحق لكم أن تسألونا عن البيانات التي نحتفظ بها عنكم وأن تطلبوا تصحيحها أو حذفها. وإذا لم توافقوا على طريقة تعاملنا مع البيانات، يمكنكم تقديم شكوى إلى هيئة حماية البيانات الهولندية (Autoriteit Persoonsgegevens).',
      ]],
    ],
  },
  notFound: {
    heading: 'هذه الصفحة غير موجودة',
    text: 'الرابط قديم أو أن العنوان كُتب بشكل خاطئ.',
    home: 'إلى الصفحة الرئيسية',
  },
};

export const copy: Record<Lang, PageCopy> = { nl, en, de, ar };
