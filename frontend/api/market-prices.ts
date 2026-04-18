import type { VercelRequest, VercelResponse } from '@vercel/node'
import { getCommodityName, getMandiName, getRegion, regionMandiSqlPattern } from './_region.js'

export default async function handler(req: VercelRequest, res: VercelResponse) {
  res.setHeader('Access-Control-Allow-Origin', '*')
  try {
    const dbUrl = process.env.DATABASE_URL
    if (!dbUrl) return res.status(500).json({ error: 'DATABASE_URL not set' })
    const { neon } = await import('@neondatabase/serverless')
    const sql = neon(dbUrl)
    const region = getRegion()
    const mandiPattern = regionMandiSqlPattern(region)

    // Only the last 14 days so stale rows stop masquerading as current;
    // region-filter on mandi_id prefix pushed into SQL to cut transfer.
    const prices = await sql`
      SELECT DISTINCT ON (mandi_id, commodity_id)
        mandi_id, commodity_id, price_rs, source, date, full_data, created_at
      FROM market_prices
      WHERE created_at >= NOW() - INTERVAL '14 days'
        AND mandi_id LIKE ${mandiPattern}
      ORDER BY mandi_id, commodity_id, created_at DESC
    `

    const enriched = prices.map((p: any) => {
      const mandi_name = getMandiName(p.mandi_id, region)
      const commodity_name = getCommodityName(p.commodity_id, region)
      if (p.full_data && typeof p.full_data === 'object') {
        return { ...p.full_data, mandi_name, commodity_name }
      }
      return {
        mandi_id: p.mandi_id,
        mandi_name,
        commodity_id: p.commodity_id,
        commodity_name,
        price_rs: p.price_rs,
        reconciled_price_rs: p.price_rs,
        agmarknet_price_rs: null,
        enam_price_rs: null,
        confidence: 0.85,
        price_trend: 'flat',
        date: p.date || '',
        source_used: p.source || '',
      }
    })

    res.json({ market_prices: enriched, total: enriched.length, region, source: 'neon' })
  } catch (e: any) {
    res.status(500).json({ error: e?.message ?? String(e) })
  }
}
