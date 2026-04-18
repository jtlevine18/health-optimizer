import type { VercelRequest, VercelResponse } from '@vercel/node'
import { getCommodityName, getRegion } from './_region'

export default async function handler(req: VercelRequest, res: VercelResponse) {
  res.setHeader('Access-Control-Allow-Origin', '*')
  try {
    const dbUrl = process.env.DATABASE_URL
    if (!dbUrl) return res.json({ price_conflicts: [], total: 0, source: 'neon' })
    const { neon } = await import('@neondatabase/serverless')
    const sql = neon(dbUrl)
    const region = getRegion()

    const runs = await sql`
      SELECT price_conflicts FROM pipeline_runs
      WHERE price_conflicts IS NOT NULL
      ORDER BY started_at DESC LIMIT 1
    `

    const raw = runs[0]?.price_conflicts || []

    const conflicts = raw.map((c: any) => ({
      ...c,
      commodity_name: c.commodity_name || getCommodityName(c.commodity_id, region),
      delta_pct: c.delta_pct || 0,
      reasoning: c.reasoning || c.resolution || 'Auto-reconciled based on source reliability',
      confidence: c.confidence || 0.7,
      investigation_steps: c.investigation_steps || null,
    }))

    res.json({ price_conflicts: conflicts, total: conflicts.length, region, source: 'neon' })
  } catch (_e: any) {
    res.json({ price_conflicts: [], total: 0, source: 'neon' })
  }
}
