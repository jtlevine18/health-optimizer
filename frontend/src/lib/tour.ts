import type { Step } from 'react-joyride'

export const tourSteps: Step[] = [
  // ── Dashboard ──
  {
    target: '[data-tour="hero"]',
    title: 'Welcome to the Supply Chain Optimizer',
    content:
      'This dashboard monitors a health supply chain pipeline for district health facilities in West Africa. ' +
      'It ingests messy facility reports, uses Claude agents to extract and reconcile data, ' +
      'forecasts climate-driven drug demand with an ML model, and generates budget-constrained procurement plans ' +
      'across 10 facilities in Nigeria and Ghana.',
    placement: 'bottom',
    disableBeacon: true,
  },
  {
    target: '[data-tour="stage-cards"]',
    title: 'Six-stage AI pipeline',
    content:
      'Data flows from raw text reports through AI extraction, reconciliation, ML forecasting, ' +
      'agent-based procurement optimization, and RAG-powered recommendations.',
    placement: 'bottom',
    disableBeacon: true,
  },
  {
    target: '[data-tour="metrics"]',
    title: 'Live metrics',
    content:
      'Facilities monitored, active stockout risks, drugs tracked, and pipeline run counts ' +
      'update after each pipeline execution.',
    placement: 'top',
    disableBeacon: true,
  },
  // ── Inputs ──
  {
    target: '[data-tour="inputs-title"]',
    title: 'AI data extraction',
    content:
      'Facility stock reports arrive as unstructured text. Claude agents parse stock levels, ' +
      'disease surveillance reports, and informal CHW messages into structured data.',
    placement: 'bottom',
    disableBeacon: true,
  },
  {
    target: '[data-tour="inputs-extraction"]',
    title: 'Messy in, clean out',
    content:
      'Left: the raw text as received. Right: structured tables extracted by the AI agent. ' +
      'The visual contrast is the point \u2014 this is where LLMs add real value in low-resource health systems.',
    placement: 'top',
    disableBeacon: true,
  },
  {
    target: '[data-tour="inputs-metrics"]',
    title: 'Cross-source reconciliation',
    content:
      'When stock reports and LMIS records disagree, the agent flags conflicts, applies resolution logic, ' +
      'and explains its reasoning. Each facility gets a data quality score.',
    placement: 'bottom',
    disableBeacon: true,
  },
  // ── Demand ──
  {
    target: '[data-tour="demand-title"]',
    title: 'Disease-driven demand',
    content:
      'Rainfall patterns drive malaria and diarrhoeal disease. The forecast engine predicts ' +
      'how drug demand will shift based on climate data and seasonal patterns.',
    placement: 'bottom',
    disableBeacon: true,
  },
  {
    target: '[data-tour="demand-metrics"]',
    title: 'Forecast signals',
    content:
      'Drugs forecasted, average demand change, climate-driven percentage, and model confidence.',
    placement: 'bottom',
    disableBeacon: true,
  },
  // ── Procurement ──
  {
    target: '[data-tour="procurement-title"]',
    title: 'Budget-constrained procurement',
    content:
      'The procurement engine takes forecasted demand, applies safety stock calculations, ' +
      'and allocates the quarterly budget across essential medicines, prioritizing critical drugs.',
    placement: 'bottom',
    disableBeacon: true,
  },
  {
    target: '[data-tour="procurement-metrics"]',
    title: 'Coverage metrics',
    content:
      'Budget utilization, drug coverage ratios, stockout risks, and critical drug coverage. ' +
      'The optimizer balances coverage against available budget.',
    placement: 'bottom',
    disableBeacon: true,
  },
  {
    target: '[data-tour="procurement-tabs"]',
    title: 'Agent reasoning',
    content:
      'The Agent Reasoning tab shows the Claude agent\'s tool calls, redistribution decisions, ' +
      'and step-by-step logic for how it allocated the budget and made tradeoff decisions.',
    placement: 'top',
    disableBeacon: true,
  },
  // ── Final ──
  {
    target: '[data-tour="hero"]',
    title: 'The hard problems remain',
    content:
      'The full chain from messy text reports and climate data to an optimized procurement plan, automated by AI agents. ' +
      'The hard problems that remain are human ones: community health workers reporting stock levels accurately, ' +
      'facility staff acting on recommendations, and the physical logistics of getting drugs from warehouse to clinic. ' +
      'That\u2019s where the investment should go.',
    placement: 'center',
    disableBeacon: true,
  },
]

export const stepRoutes: Record<number, string> = {
  0: '/',
  1: '/',
  2: '/',
  3: '/inputs',
  4: '/inputs',
  5: '/inputs',
  6: '/demand',
  7: '/demand',
  8: '/procurement',
  9: '/procurement',
  10: '/procurement',
  11: '/',
}

export const tourStyles = {
  options: {
    zIndex: 10000,
    arrowColor: '#1a1a1a',
    backgroundColor: '#1a1a1a',
    primaryColor: '#d4a019',
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
    color: '#d4a019',
    marginBottom: 8,
  },
  tooltipContent: {
    padding: '8px 0 0',
  },
  buttonNext: {
    backgroundColor: '#d4a019',
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
