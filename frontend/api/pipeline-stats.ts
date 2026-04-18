import type { VercelRequest, VercelResponse } from '@vercel/node'
import { getDataSources, getMandis, getRegion, regionMandiSqlPattern } from './_region.js'

export default async function handler(req: VercelRequest, res: VercelResponse) {
  try {
    const dbUrl = process.env.DATABASE_URL
    if (!dbUrl) return res.status(500).json({ error: 'DATABASE_URL not set' })
    const { neon } = await import('@neondatabase/serverless')
    const sql = neon(dbUrl)
    const region = getRegion()
    const mandiPattern = regionMandiSqlPattern(region)

    const runs = await sql`
      SELECT run_id, started_at, status, duration_sec, total_cost_usd,
             mandis_count, commodities_count
      FROM pipeline_runs
      ORDER BY started_at DESC
      LIMIT 20
    `

    const totalRuns = runs.length
    const successfulRuns = runs.filter((r: any) => r.status === 'ok').length
    const totalCost = runs.reduce((s: number, r: any) => s + (r.total_cost_usd || 0), 0)

    // Region + 30-day window filter on market_prices so pre-migration
    // rows stop padding the counts.
    const mandiRows = await sql`
      SELECT DISTINCT mandi_id FROM market_prices
      WHERE mandi_id LIKE ${mandiPattern}
        AND created_at >= NOW() - INTERVAL '30 days'
    `
    const commodityRows = await sql`
      SELECT DISTINCT commodity_id FROM market_prices
      WHERE mandi_id LIKE ${mandiPattern}
        AND created_at >= NOW() - INTERVAL '30 days'
    `
    const mandiCount = mandiRows.length
    const commoditySet = new Set((commodityRows as any[]).map((r) => r.commodity_id))

    res.setHeader('Access-Control-Allow-Origin', '*')
    res.json({
      total_runs: totalRuns,
      successful_runs: successfulRuns,
      success_rate: totalRuns > 0 ? Math.round(successfulRuns / totalRuns * 100) / 100 : 0,
      mandis_monitored: mandiCount || getMandis(region).length,
      commodities_tracked: commoditySet.size || 4,
      price_conflicts_found: 0,
      total_cost_usd: Math.round(totalCost * 100) / 100,
      avg_cost_per_run_usd: totalRuns > 0 ? Math.round(totalCost / totalRuns * 10000) / 10000 : 0,
      last_run: runs[0]?.started_at || null,
      data_sources: getDataSources(region),
      region,
      source: 'neon',
    })
  } catch (e: any) {
    res.status(500).json({ error: e.message })
  }
}
