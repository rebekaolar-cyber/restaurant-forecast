// The menu. Leave `sections` empty until the real menu is supplied: the menu
// page then shows a marked placeholder instead. Never fill this with guesses.
//
// Example of one section once the real menu is in:
//   {
//     title: 'Naam van de sectie',
//     note: 'Optionele toelichting',
//     items: [{ name: 'Gerecht', description: 'Korte omschrijving', price: 12.5 }],
//   }

export type MenuItem = { name: string; description?: string; price?: number };
export type MenuSection = { title: string; note?: string; items: MenuItem[] };

export const sections: MenuSection[] = [];

export function euro(amount: number): string {
  return new Intl.NumberFormat('nl-NL', { style: 'currency', currency: 'EUR' }).format(amount);
}
