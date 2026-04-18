import type { VercelRequest, VercelResponse } from '@vercel/node'
import { getCommodityName, getMandiName, getRegion, isRegionMandi } from './_region.js'

export default async function handler(req: VercelRequest, res: VercelResponse) {
  res.setHeader('Access-Control-Allow-Origin', '*')
  try {
    const dbUrl = process.env.DATABASE_URL
    if (!dbUrl) return res.status(500).json({ error: 'DATABASE_URL not set' })
    const { neon } = await import('@neondatabase/serverless')
    const sql = neon(dbUrl)
    const region = getRegion()

    const forecasts = await sql`
      SELECT DISTINCT ON (mandi_id, commodity_id, horizon_days)
        run_id, mandi_id, commodity_id, forecast_date, horizon_days,
        predicted_price, ci_lower, ci_upper, model_type, created_at
      FROM price_forecasts
      ORDER BY mandi_id, commodity_id, horizon_days, created_at DESC
    `

    const grouped: Record<string, any> = {}
    for (const f of forecasts) {
      if (!isRegionMandi(f.mandi_id, region)) continue
      const key = `${f.mandi_id}|${f.commodity_id}`
      if (!grouped[key]) {
        grouped[key] = {
          mandi_id: f.mandi_id,
          mandi_name: getMandiName(f.mandi_id, region),
          commodity_id: f.commodity_id,
          commodity_name: getCommodityName(f.commodity_id, region),
          current_price_rs: null,
          price_7d: null, price_14d: null, price_30d: null,
          ci_lower_7d: null, ci_upper_7d: null,
          direction: 'flat',
          confidence: 0.8,
        }
      }
      const g = grouped[key]
      if (f.horizon_days === 7) {
        g.price_7d = f.predicted_price
        g.ci_lower_7d = f.ci_lower
        g.ci_upper_7d = f.ci_upper
        g.current_price_rs = f.predicted_price
      } else if (f.horizon_days === 14) {
        g.price_14d = f.predicted_price
      } else if (f.horizon_days === 30) {
        g.price_30d = f.predicted_price
      }
    }

    const result = Object.values(grouped)
    res.json({ price_forecasts: result, total: result.length, region, source: 'neon' })
  } catch (e: any) {
    res.status(500).json({ error: e.message })
  }
}
