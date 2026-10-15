// The few Dutch phrases the browser script needs ("open today" line and the
// marker in the opening-hours list). Kept apart from nl.ts so visitors do not
// download every page's text with it.
// {open} and {close} are replaced with times such as 17:00.

export const statusText = {
  opensToday: 'Vandaag open van {open} tot {close}',
  openNow: 'Nu open, tot {close}',
  closedOpensToday: 'Nu gesloten. Vandaag open vanaf {open}',
  closedOpensTomorrow: 'Nu gesloten. Morgen open vanaf {open}',
  rowToday: 'vandaag',
  rowOpen: 'nu open',
} as const;
