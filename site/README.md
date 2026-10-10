# Restaurant Habibi: website

The public website and the manager's dashboard behind a login. Built with
[Astro](https://astro.build) as a static site: the build produces plain HTML,
CSS and one small script, and Cloudflare Pages serves those files.

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
```

## Where to change things

| What | File |
|---|---|
| Name, address, booking link, map link, phone, e-mail, seats | `src/content/restaurant.ts` |
| Opening hours (pages, footer and the "open today" line all read this) | `src/content/hours.ts` |
| The menu | `src/content/menu.ts` |
| Every Dutch sentence on the pages | `src/content/nl.ts` and `src/content/nl.status.ts` |
| Photos | put files in `src/assets/photos/`, then fill the slot in `src/content/photos.ts` |
| Colours, type, spacing | the `:root` block at the top of `src/styles/global.css` |

Anything shown hatched with a dashed edge and the word "Placeholder" is
waiting for real content. A placeholder disappears by itself once its content
is filled in: a phone number in `restaurant.ts`, menu sections in `menu.ts`,
a photo in `photos.ts`.

Never invent dishes, prices or opening hours. If it is not known, leave the
placeholder.

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
| `/dashboard/` | The manager's screen. Sends anyone who is not logged in to `/login/`. |

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

## Privacy rules this site keeps

- No tracking, no cookies, no scripts or fonts from other parties. Only the
  login pages and the dashboard talk to Supabase; the public pages do not.
- Fonts are files in `src/assets/fonts/` (both under the SIL Open Font
  License; the licence texts sit next to them).
- No forms. Reserving happens in the restaurant's own booking system.
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
