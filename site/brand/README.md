# Brand files

`originals/` holds the logo files exactly as supplied (EPS and PDF, CMYK,
made for print). They are kept for reference and are not published.

| Supplied file | What it is | Where the site uses it |
|---|---|---|
| `Habibi_Logo_CMYK` | Round logo: white wordmark on a black, patterned disc | Footer of every page (`src/assets/brand/habibi-logo-round.svg`), the favicon and the phone home-screen icon |
| `Habibi_Logo_Sec_CMYK_1` | Black wordmark with magenta dots and the tagline | Header of every page (`src/assets/brand/habibi-logo-black.svg`) |
| `Habibi_Logo_Sec_CMYK` and `Habibi_Logo_Sec_CMYK_2` (the two PDFs are the same file) | All-magenta wordmark with black tagline | Ready as `src/assets/brand/habibi-logo-magenta.svg`, not placed on a page yet |

The web versions were converted from the PDFs to SVG, cropped to the artwork
and slimmed down. The shapes are unchanged. Screen colours taken from the
files: black `#231f20`, magenta `#ec008c`, white.

`public/favicon.svg` is the round logo reduced to what survives at 16 to 32
pixels: the black disc, the wordmark and its dots.
