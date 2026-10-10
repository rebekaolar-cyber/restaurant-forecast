import type { ImageMetadata } from 'astro';

// Photo slots. To fill one: put the file in src/assets/photos/, import it
// here, set `src` and write an `alt` that describes what is in the picture.
// While `src` is null the page shows a marked placeholder that says which
// photo belongs there.
//
//   import binnentuin from '../assets/photos/binnentuin.jpg';
//   binnentuin: { src: binnentuin, alt: 'Gedekte tafels in de binnentuin bij avond', wanted: '…' },

export type Photo = { src: ImageMetadata | null; alt: string; wanted: string };
export type PhotoName = 'hero' | 'restaurant' | 'binnentuin' | 'about' | 'menu';

export const photos: Record<PhotoName, Photo> = {
  hero: {
    src: null,
    alt: '',
    wanted: 'Grote sfeerfoto voor de homepage, bij voorkeur de binnentuin of de eetzaal bij avond (staand formaat).',
  },
  restaurant: {
    src: null,
    alt: '',
    wanted: 'Foto van de eetzaal binnen (liggend formaat).',
  },
  binnentuin: {
    src: null,
    alt: '',
    wanted: 'Foto van de binnentuin (liggend formaat).',
  },
  about: {
    src: null,
    alt: '',
    wanted: 'Foto bij het verhaal van het restaurant: de keuken, het team aan het werk of een detail van het interieur. Geen herkenbare gasten.',
  },
  menu: {
    src: null,
    alt: '',
    wanted: 'Foto van een of meer gerechten (liggend formaat).',
  },
};
