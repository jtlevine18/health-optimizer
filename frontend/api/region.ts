import type { VercelRequest, VercelResponse } from '@vercel/node'

// Thin endpoint that just echoes the deployment's region, driven by the
// `MARKET_INTEL_REGION` env var (matches `config.py`'s source of truth).
// The React app fetches this once via `useRegion()` to pick tour narrative,
// currency, and page copy. Defaults to Kenya since the Phase 1 pivot made
// Kenya the primary region.
export default async function handler(_req: VercelRequest, res: VercelResponse) {
  const raw = (process.env.MARKET_INTEL_REGION ?? 'kenya').toLowerCase()
  const region = raw === 'india' ? 'india' : 'kenya'
  res.setHeader('Cache-Control', 'public, max-age=60')
  res.json({ region })
}
