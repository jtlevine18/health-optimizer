import type { Step } from 'react-joyride'

export const tourSteps: Step[] = [
  // ── Step 1: Welcome (/) ──
  {
    target: '[data-tour="hero"]',
    title: 'Lakshmi grows rice in Thanjavur',
    content:
      'She harvests in September. Three mandis within 40km, each quoting a different price. ' +
      'She sells at the nearest one for whatever the middleman offers \u2014 and loses 15\u201330% of what her rice is actually worth. ' +
      'This tool does what a broker would: tells her which market, which day, and at what net price after transport and fees.',
    placement: 'bottom',
    disableBeacon: true,
  },
  // ── Step 2: The hook (/) ──
  {
    target: '[data-tour="callout"]',
    title: 'Two databases. Different prices. Same market.',
    content:
      'India has two government price databases: Agmarknet and eNAM. They disagree 5\u201312% of the time. ' +
      'Nobody reconciles them. Farmers trust whichever middleman they ask. This tool investigates the gap.',
    placement: 'bottom',
    disableBeacon: true,
  },
  // ── Step 3: Live data (/) ──
  {
    target: '[data-tour="metrics"]',
    title: '15 real mandis. 10 commodities. Updated daily.',
    content:
      'These are real regulated markets from Thanjavur to Tirunelveli, with prices from the actual Agmarknet API. ' +
      'The \u2018Conflicts\u2019 count shows how many prices the two government databases disagreed on \u2014 ' +
      'each one is a case where a farmer wouldn\u2019t know which number to trust.',
    placement: 'top',
    disableBeacon: true,
  },
  // ── Step 4: Price table (/) ──
  {
    target: '[data-tour="price-table"]',
    title: 'Every price has a story',
    content:
      'Green means above seasonal average \u2014 good time to sell. Red means below. ' +
      'Hover over any cell to see both source prices and how they were reconciled. ' +
      'The confidence score tells you how much to trust the number.',
    placement: 'top',
    disableBeacon: true,
  },
  // ── Step 5: Navigate to Forecast (/forecast) ──
  {
    target: '[data-tour="forecast-title"]',
    title: 'Should she sell now or wait two weeks?',
    content:
      'The system predicts prices at 7, 14, and 30 days \u2014 ' +
      'with honest confidence ranges so farmers know how much to trust each forecast. ' +
      'Rice typically drops 15% in October as harvest floods the market, then climbs through May.',
    placement: 'bottom',
    disableBeacon: true,
  },
  // ── Step 8: Forecast confidence (/forecast) ──
  {
    target: '[data-tour="forecast-metrics"]',
    title: 'The confidence band matters',
    content:
      '\u20b92,300 \u00b1 \u20b9150 is a strong signal. \u20b92,300 \u00b1 \u20b9500 means wait for more data. ' +
      'The wider the band, the less certain the forecast \u2014 ' +
      'and the more reason to hold off on a sell decision.',
    placement: 'bottom',
    disableBeacon: true,
  },
  // ── Step 9: Navigate to Sell (/sell) ──
  {
    target: '[data-tour="sell-title"]',
    title: 'The full calculation',
    content:
      'Kumbakonam offers \u20b9150/quintal more than Thanjavur. But it\u2019s 30km away. Transport costs \u20b980. ' +
      'Storage at Thanjavur for two weeks loses \u20b945 to spoilage. ' +
      'The optimizer computes every combination and finds the one that puts the most money in Lakshmi\u2019s pocket.',
    placement: 'bottom',
    disableBeacon: true,
  },
  // ── Step 10: Net price breakdown (/sell) ──
  {
    target: '[data-tour="waterfall"]',
    title: 'Net price, not market price',
    content:
      'Market price minus transport, minus storage loss, minus mandi fees equals net price. ' +
      'That\u2019s the number that matters. The middleman knows this math. Now Lakshmi does too.',
    placement: 'top',
    disableBeacon: true,
  },
  // ── Step 11: Credit readiness (/sell) ──
  {
    target: '[data-tour="credit-readiness"]',
    title: 'Should she borrow for next season?',
    content:
      'Based on her expected harvest revenue, the tool assesses whether an input loan makes sense \u2014 ' +
      'and caps it at 40% of expected revenue. Green means strong. Amber means proceed with caution. Red means wait.',
    placement: 'top',
    disableBeacon: true,
  },
  // ── Step 12: End on Pipeline ──
  {
    target: '[data-tour="nav-pipeline"]',
    title: 'How it all fits together',
    content:
      'The full chain — from scraping two government databases to generating a personalized ' +
      'sell recommendation in Tamil. The system is designed to be forked ' +
      'for a different region, set of crops, or market network.',
    placement: 'right',
    disableBeacon: true,
  },
]

export const stepRoutes: Record<number, string> = {
  0: '/',         // hero
  1: '/',         // callout
  2: '/',         // metrics
  3: '/',         // price table
  4: '/forecast', // forecast title
  5: '/forecast', // forecast metrics
  6: '/sell',     // sell title
  7: '/sell',     // waterfall
  8: '/sell',     // credit readiness
  9: '/sell',     // nav-pipeline (end)
}

export const tourStyles = {
  options: {
    zIndex: 10000,
    arrowColor: '#1a1a1a',
    backgroundColor: '#1a1a1a',
    primaryColor: '#0d7377',
    textColor: '#e0dcd5',
    overlayColor: 'rgba(0, 0, 0, 0.45)',
  },
  tooltip: {
    borderRadius: 10,
    padding: '20px 22px',
    maxWidth: 380,
    fontFamily: '"DM Sans", system-ui, sans-serif',
    fontSize: '0.88rem',
    lineHeight: 1.6,
  },
  tooltipTitle: {
    fontFamily: '"Source Serif 4", Georgia, serif',
    fontWeight: 700,
    fontSize: '1.05rem',
    color: '#0d7377',
    marginBottom: 8,
  },
  tooltipContent: {
    padding: '8px 0 0',
  },
  buttonNext: {
    backgroundColor: '#0d7377',
    color: '#fff',
    borderRadius: 6,
    fontFamily: '"DM Sans", system-ui, sans-serif',
    fontWeight: 600,
    fontSize: '0.8rem',
    letterSpacing: '0.5px',
    textTransform: 'uppercase' as const,
    padding: '8px 18px',
  },
  buttonBack: {
    color: '#888',
    fontFamily: '"DM Sans", system-ui, sans-serif',
    fontWeight: 500,
    fontSize: '0.8rem',
    marginRight: 8,
  },
  buttonSkip: {
    color: '#666',
    fontFamily: '"DM Sans", system-ui, sans-serif',
    fontSize: '0.75rem',
  },
  spotlight: {
    borderRadius: 10,
  },
  beacon: {
    display: 'none',
  },
  beaconInner: {
    display: 'none',
  },
  beaconOuter: {
    display: 'none',
  },
}
