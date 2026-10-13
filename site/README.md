# Restaurant Habibi: website

The public website and the manager's dashboard behind a login. Built with
[Astro](https://astro.build) as a static site: the build produces plain HTML,
CSS and a few small scripts, and Cloudflare Pages serves those files.

Everything for the website lives in this `site/` folder. The forecast, the
database and the nightly job live elsewhere in the repo and are not touched
from here.

## Run it on your own computer

You need Node.js 22.12 or newer.

```
cd site
npm install
npm run dev        # the site at http://localhost:4321, reloads as you edit
npm run build      # builds the real thing into site/dist
npm run preview    # serves site/dist, exactly what Cloudflare will serve
npm run check      # type check
npm test           # unit tests for the dashboard's date and save logic
```

## Pages and languages

Every public page exists in Dutch, English, German and Arabic. Dutch lives at
the plain address, the others under `/en/`, `/de/` and `/ar/` (Arabic reads
right to left). The header links to the same page in the other languages.

| Page | Dutch | English | German | Arabic |
|---|---|---|---|---|
| Home | `/` | `/en/` | `/de/` | `/ar/` |
| Menu | `/menu/` | `/en/menu/` | `/de/speisekarte/` | `/ar/menu/` |
| About | `/over-ons/` | `/en/about/` | `/de/ueber-uns/` | `/ar/about/` |
| Contact | `/contact/` | `/en/contact/` | `/de/kontakt/` | `/ar/contact/` |
| Privacy | `/privacy/` | `/en/privacy/` | `/de/datenschutz/` | `/ar/privacy/` |

One file, `src/pages/[...path].astro`, builds all twenty from the list in
`src/content/i18n.ts`. The page designs are in `src/components/pages/`, the
shared parts (header, footer, hours, map, door) in `src/components/site/`.

Moving between pages plays the green double door (a browser "view
transition", CSS only). Switching language only cross-fades. Browsers without
this feature simply load the next page.

The menu page has a switch "Met foto's / Alleen tekst": the same card with
the dish photos, or as a plain list for guests who only want to read. On a
phone, tapping a photo shows the description and allergy marks.

## Where to change things

| What | File |
|---|---|
| Name, address, booking link, map link, phone, e-mail, socials, seats | `src/content/restaurant.ts` |
| Opening hours (pages, footer and the "open today" line all read this) | `src/content/hours.ts` |
| The menu: dishes, prices, descriptions in four languages, photos | `src/content/menu.ts` |
| Short interface words (buttons, menu headings, day names) | `src/content/strings.ts` |
| Page texts (about, contact, privacy, page titles for search engines) | `src/content/pages.ts` |
| Dish photos | `src/assets/photos/dishes/`, then the dish's `photo` field in `menu.ts` |
| Colours, type, spacing | the `:root` block at the top of `src/styles/site.css` |
| The picture shown when a page is shared | `public/og.jpg`, made by `node tools/make-og.mjs` |

The English, German and Arabic texts are our own translations and still need
a check by a native speaker.

Anything shown hatched with a dashed edge ("Foto volgt", "Kaart volgt",
"TODO") is waiting for real content. Never invent dishes, prices or opening
hours. If it is not known, leave the placeholder.

`menu.ts`, `strings.ts` and `art.ts` were generated once from the design
preview. Edit them here directly from now on.

## The map

The map in the footer and on the contact page is a picture kept with the
site, so no map service loads on our pages. Until it is made, a marked
"Kaart volgt" placeholder shows. To add it: export a PNG of the street from
openstreetmap.org (Share → Image, about 1200 × 900), save it as
`src/assets/map/map.png`, and rebuild. The pin and the credit line are drawn
by the site.

## Security headers

`public/_headers` tells every visitor's browser what the site may do. The
public pages may load nothing from other websites: no scripts, no styles, no
fonts, no pictures, no connections (`Content-Security-Policy`). They cannot be
shown inside another website, always use https, and do not get access to the
camera, microphone or location. The login and dashboard get the same rules
plus one connection: the Supabase project. Only `!` lines in that file remove
a header for those two pages, so the two policies never mix.

Because of this policy the HTML has no inline scripts and no `style="..."`
attributes. Keep it that way: put styles in `src/styles/` and scripts in
`src/scripts/`. A new outside service (for example an embedded video) will
not work until it is added to `_headers` on purpose.

`public/_redirects` sends the old booking address `/reserveren/` straight to
TheFork.

To see the headers locally exactly as Cloudflare sends them:
`npx wrangler pages dev dist` after a build.

## Search engines

Each page has a title and description in its language, a canonical address,
links to its other languages (`hreflang`), a sharing picture, and structured
data (schema.org) with the address, opening hours, booking link and the full
menu with prices. `/sitemap.xml` lists every page in every language.
`/robots.txt` keeps search engines out while the site is a test version.

## Test version and live version

Until the environment variable `PUBLIC_SITE_LIVE` is set to `true`, the site
is a test version: every page shows a banner that points to the official
website, and every page asks search engines not to index it. Leave it unset
on the test address.

## Login and dashboard

| Page | What it does |
|---|---|
| `/login/` | Log in with e-mail and password. Also "Wachtwoord vergeten?". There is no sign-up: accounts exist only by invitation. |
| `/login/nieuw-wachtwoord/` | Where an invitation or reset e-mail leads: choose a password. |
| `/dashboard/` | The manager's screen: the next 14 days. Sends anyone who is not logged in to `/login/`. |

How the lock works, in plain words:

- The site is static, so the dashboard page itself is an empty frame that
  anyone could download. It contains no figures.
- When it opens, `src/scripts/dashboard.ts` first asks Supabase whether this
  browser holds a valid login. Only after a yes does it show the screen and
  ask for data. Without a login it goes to `/login/` and asks for nothing.
- The real lock is in the database: row level security gives rows only to a
  logged-in member of the restaurant. Changing the page in the browser does
  not get anyone past that.
- All three pages carry `noindex`, in the page and in `public/_headers`.

The Supabase project address and its **public** key are in
`src/lib/supabase.ts`. Both are meant to be visible; they open nothing on
their own. The **secret** key never goes anywhere in this folder, and the
build stops if one is put in `PUBLIC_SUPABASE_PUBLISHABLE_KEY`.

Settings this needs in Supabase (Authentication):

- Sign-ups switched off, so nobody can create their own account.
- **Site URL** set to the address of this site, and the same address followed
  by `/**` added under **Redirect URLs**. Invitation and reset e-mails send
  people back to that address.
- A person can use the dashboard once they are invited **and** have a row in
  `restaurant_members`.

## The dashboard

One screen with the next 14 days. Per day: expected guests (number and bar),
the staff per roster role, and the weather. Choosing a day opens it: the
manager can set their own numbers per role and write a note.

The roster roles, in roster order:

| Roster letter | Column in the database | Shown as |
|---|---|---|
| W | `servers` (floor staff) | Bediening |
| B | `bar_staff` | Bar |
| R | `runners` | Runners |
| F | `food_staff` | Food |

The kitchen (`cooks`) is a fixed crew and is not on the roster. The dashboard
shows it (once above the list when it is the same every day, and in each
opened day) but never offers to change it.

What it reads and writes (names are the shared contract):

| Table | Use |
|---|---|
| `restaurants` | read: id, name, timezone of the restaurant this login belongs to |
| `forecasts` | read: guests, servers, bar_staff, runners, food_staff, cooks, model, created_at |
| `daily_weather` | read |
| `forecast_overrides` | read, upsert on `restaurant_id, date, shift`, delete |

How an override is stored:

- Only `restaurant_id, date, shift, servers, bar_staff, runners, food_staff,
  cooks, note` are sent. The database records who changed it and when.
- A number equal to the forecast's is sent as empty, which means "keep the
  forecast's number". Only a number the manager really changed is pinned.
- `cooks` is always sent empty: the kitchen is never overridden from here.
- Numbers back at the forecast and no note: the row is deleted.
- The line then shows the manager's number in a black box with the
  forecast's number under it (on the line that starts with "prognose"), and
  the note.

If the database does not have `bar_staff`, `runners` and `food_staff` yet,
the dashboard notices (the database answers "column does not exist"), asks
again without them, and shows and saves only W. Nothing has to be changed
here once the columns arrive.

Things it decides on its own:

- "Today" is the day the evening started, until 04:00 at night, in the
  restaurant's own timezone.
- A day without a forecast still gets a line ("Geen prognose").
- "Prognose bijgewerkt ..." is the newest `created_at` on screen. Older than
  36 hours gives a warning that the nightly run probably failed.
- Rows with `model = 'placeholder'` are flagged as example figures.
- The note is shown as plain text, never as HTML.

Where the code is:

| File | What |
|---|---|
| `src/lib/forecast-days.ts` | the logic: which days, which number counts, what to save (tested in `forecast-days.test.ts`) |
| `src/lib/dashboard-data.ts` | every database call |
| `src/scripts/dashboard.ts` | checks the login before anything is shown or fetched |
| `src/scripts/dashboard-view.ts` | draws the list and the edit panel |
| `src/styles/dashboard.css` | the look |
| `src/content/nl.staff.ts` | every Dutch sentence |

## Privacy rules this site keeps

- No tracking, no cookies, no scripts or fonts from other parties. Only the
  login pages and the dashboard talk to Supabase; the public pages do not,
  and the security headers enforce that.
- Fonts are files in `src/assets/fonts/` (all under the SIL Open Font
  License; the licence texts sit next to them), including Amiri and Noto Sans
  Arabic for the Arabic pages.
- No booking form of our own. Every reserve button is a plain link to the
  restaurant's TheFork booking page. The widget is not embedded, so nothing
  from TheFork loads on these pages.
- No secret keys in this folder, ever. It holds only the Supabase project
  URL and the public key.

## Brand files

The logo files as supplied are in `brand/originals/`. The versions the site
uses are SVG files in `src/assets/brand/`. See `brand/README.md`.

## Cloudflare Pages settings

| Setting | Value |
|---|---|
| Production branch | `main` |
| Framework preset | Astro |
| Build command | `npm run build` |
| Build output directory | `dist` |
| Root directory | `site` |
| Environment variable `NODE_VERSION` | `22.16.0` |
| Environment variable `ASTRO_TELEMETRY_DISABLED` | `1` |

The login needs no extra variables.
