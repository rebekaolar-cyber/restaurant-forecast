// Builds public/og.jpg (1200x630): the picture shown when a page is shared.
// Teal ground, the star pattern, the wordmark, and three dish photos in arches.
// Run from site/: node tools/make-og.mjs
import sharp from 'sharp';
import fs from 'node:fs';
const root = new URL('..', import.meta.url).pathname.replace(/\/$/, '');
const art = fs.readFileSync(root + '/src/content/art.ts', 'utf8');
const logo = JSON.parse(art.match(/export const logoPaths = (\[.*?\]);/s)[1]);
const stars = fs.readFileSync(root + '/public/art/stars.svg', 'utf8');
const starsUri = 'data:image/svg+xml;base64,' + Buffer.from(stars).toString('base64');
const photo = async (n) => 'data:image/jpeg;base64,' + (await sharp(`${root}/src/assets/photos/dishes/${n}.jpg`).resize(300, 400, { fit: 'cover' }).jpeg({ quality: 90 }).toBuffer()).toString('base64');
const arch = 'M0,100 L0,46 L6,46 C6,40 0,39 0,31 C0,19 17,13 30,9.5 C40,6.8 47,4 50,0 C53,4 60,6.8 70,9.5 C83,13 100,19 100,31 C100,39 94,40 94,46 L100,46 L100,100';
const dishes = ['hommus', 'shish-tavuk', 'muhammara'];
const W = 1200, H = 630, aw = 186, ah = 248, gap = 30, y0 = 214;
const x0 = W - 64 - 3 * aw - 2 * gap;
let arches = '';
for (const [i, n] of dishes.entries()) {
  const x = x0 + i * (aw + gap), y = y0 - (i === 1 ? 36 : 0);
  arches += `<clipPath id="c${i}"><path transform="translate(${x} ${y}) scale(${aw / 100} ${ah / 100})" d="${arch} Z"/></clipPath>
  <image href="${await photo(n)}" x="${x}" y="${y}" width="${aw}" height="${ah}" preserveAspectRatio="xMidYMid slice" clip-path="url(#c${i})"/>
  <path transform="translate(${x - 8} ${y - 8}) scale(${(aw + 16) / 100} ${(ah + 8) / 100})" d="${arch}" fill="none" stroke="#e2c084" stroke-width="${1.6 / ((aw + 16) / 100)}" />`;
}
const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}">
  <rect width="${W}" height="${H}" fill="#1f4a46"/>
  <defs><radialGradient id="fade"><stop offset=".35" stop-color="#fff"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></radialGradient>
  <mask id="m"><circle cx="250" cy="300" r="520" fill="url(#fade)"/></mask></defs>
  <image href="${starsUri}" x="-250" y="-200" width="1000" height="1000" opacity=".15" mask="url(#m)"/>
  <g transform="translate(78 236) scale(.98)"><g transform="translate(-44.91 -185.45)">
    <path d="${logo[0]}" fill="#f4ece2"/><path d="${logo[1]}" fill="#ec008c"/><path d="${logo[2]}" fill="#f4ece2"/>
  </g></g>
  ${arches}
  <rect y="${H - 10}" width="${W}" height="10" fill="#8a2b1f"/>
</svg>`;
await sharp(Buffer.from(svg)).jpeg({ quality: 84, mozjpeg: true }).toFile(root + '/public/og.jpg');
console.log(fs.statSync(root + '/public/og.jpg').size);
