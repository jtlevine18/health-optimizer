/**
 * Region configuration for Market Intelligence Agent.
 *
 * All geography-specific strings and settings live here.
 * When adapting this project for a new region, this is one of the
 * files you change (see REBUILD.md for the full guide).
 */

export const REGION = {
  /** Display name for the region */
  name: 'Tamil Nadu',

  /** Country */
  country: 'India',

  /** Currency symbol and code */
  currency: { symbol: '\u20b9', code: 'INR' },

  /** Primary unit for commodity prices */
  priceUnit: 'quintal',

  /** Languages supported (first is primary) */
  languages: { ta: 'Tamil', en: 'English' } as Record<string, string>,

  /** Primary language code for translated recommendations */
  primaryLanguage: 'ta',

  /** Data source labels (shown in UI) */
  dataSources: {
    primary: 'Agmarknet (data.gov.in)',
    secondary: 'eNAM',
    weather: 'NASA POWER',
  },

  /** Market type label (what are markets called in this region?) */
  marketLabel: 'mandi',
  marketLabelPlural: 'mandis',

  /** Sidebar branding */
  sidebarTitle: 'TAMIL NADU MANDIS',
  sidebarFooter: 'Tamil Nadu Agricultural Markets',

  /** Map defaults */
  map: {
    center: [10.8, 78.8] as [number, number],
    zoom: 7,
  },

  /** Tour narrative — farmer archetype for the guided tour */
  tour: {
    farmerName: 'Lakshmi',
    farmerCrop: 'rice',
    farmerLocation: 'Thanjavur',
    regionDescription: 'Tamil Nadu',
    marketCount: 15,
  },
} as const
