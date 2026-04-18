import type { VercelRequest, VercelResponse } from '@vercel/node'
import { getFeaturedFarmers, getMandiName, getRegion, isRegionFarmer, regionFarmerSqlPattern } from './_region.js'

export default async function handler(req: VercelRequest, res: VercelResponse) {
  res.setHeader('Access-Control-Allow-Origin', '*')
  try {
    const dbUrl = process.env.DATABASE_URL
    if (!dbUrl) return res.status(500).json({ error: 'DATABASE_URL not set' })
    const { neon } = await import('@neondatabase/serverless')
    const sql = neon(dbUrl)
    const region = getRegion()
    const fallbacks = getFeaturedFarmers(region)
    const farmerPattern = regionFarmerSqlPattern(region)

    const recs = await sql`
      SELECT DISTINCT ON (farmer_id)
        farmer_id, full_data, net_price_rs, best_mandi_id, commodity_id,
        recommendation_text, potential_gain_rs, best_timing, created_at
      FROM sell_recommendations
      WHERE farmer_id LIKE ${farmerPattern}
      ORDER BY farmer_id, created_at DESC
    `

    // SQL LIKE fetches a superset (can't distinguish FMR-K0001 from FMR-KUMR);
    // isRegionFarmer() tightens to exact region match.
    const filtered = recs.filter((r: any) => isRegionFarmer(r.farmer_id, region))

    const result = filtered.map((r: any) => {
      // Newer runs write full_data JSONB carrying the complete recommendation
      // (farmer metadata + all_options + credit_readiness + recommendation_local
      // + local_language_code). Prefer that branch whenever it's present.
      if (r.full_data && typeof r.full_data === 'object') {
        const fd = r.full_data
        const fallback = fallbacks[r.farmer_id]
        return {
          ...fd,
          farmer_lat: fd.farmer_lat ?? fallback?.lat ?? 0,
          farmer_lon: fd.farmer_lon ?? fallback?.lon ?? 0,
        }
      }

      // Legacy rows (pre-Phase-1.4) only have individual columns — no
      // recommendation_local / local_language_code. DB-schema gap: the
      // SQL column stays full_data JSONB; the fallback emits empty strings
      // so the UI can render without throwing.
      const fallback = fallbacks[r.farmer_id] || { name: r.farmer_id, lat: 0, lon: 0, commodity: r.commodity_id, quantity: 20 }
      return {
        farmer_id: r.farmer_id,
        farmer_name: fallback.name,
        commodity_id: r.commodity_id,
        commodity_name: r.commodity_id,
        quantity_quintals: fallback.quantity,
        farmer_lat: fallback.lat,
        farmer_lon: fallback.lon,
        best_option: {
          mandi_id: r.best_mandi_id,
          mandi_name: getMandiName(r.best_mandi_id, region),
          sell_timing: r.best_timing || 'now',
          net_price_rs: r.net_price_rs,
          market_price_rs: r.net_price_rs,
          transport_cost_rs: 0,
          storage_loss_rs: 0,
          mandi_fee_rs: 0,
          distance_km: 0,
        },
        all_options: [],
        potential_gain_rs: r.potential_gain_rs || 0,
        recommendation_text: r.recommendation_text || '',
        recommendation_local: '',
        local_language_code: '',
        credit_readiness: null,
      }
    })

    res.json({ sell_recommendations: result, total: result.length, region, source: 'neon' })
  } catch (e: any) {
    res.status(500).json({ error: e.message })
  }
}
