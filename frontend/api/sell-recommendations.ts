import type { VercelRequest, VercelResponse } from '@vercel/node'

const FARMERS: Record<string, { name: string; lat: number; lon: number; commodity: string; quantity: number }> = {
  'FMR-LKSH': { name: 'Lakshmi', lat: 10.78, lon: 79.14, commodity: 'RICE-SAMBA', quantity: 25 },
  'FMR-KUMR': { name: 'Kumar', lat: 11.34, lon: 77.72, commodity: 'TUR-FIN', quantity: 15 },
  'FMR-MEEN': { name: 'Meena', lat: 10.36, lon: 77.97, commodity: 'BAN-ROB', quantity: 30 },
}

export default async function handler(req: VercelRequest, res: VercelResponse) {
  try {
    const dbUrl = process.env.DATABASE_URL
    if (!dbUrl) return res.status(500).json({ error: 'DATABASE_URL not set' })
    const { neon } = await import('@neondatabase/serverless')
    const sql = neon(dbUrl)
    const recs = await sql`
      SELECT DISTINCT ON (farmer_id)
        farmer_id, full_data, net_price_rs, best_mandi_id, commodity_id,
        recommendation_text, potential_gain_rs, best_timing, created_at
      FROM sell_recommendations
      ORDER BY farmer_id, created_at DESC
    `

    const result = recs.map((r: any) => {
      // If full_data exists (from newer pipeline runs), use it directly
      if (r.full_data && typeof r.full_data === 'object') {
        const fd = r.full_data
        const farmer = FARMERS[r.farmer_id]
        return {
          ...fd,
          farmer_lat: fd.farmer_lat ?? farmer?.lat ?? 10.8,
          farmer_lon: fd.farmer_lon ?? farmer?.lon ?? 78.8,
        }
      }

      // Fallback for older rows without full_data. DB-schema gap: the
      // SQL column stays as `sell_recommendations.full_data` JSONB (no
      // dedicated `recommendation_local` column), so this fallback path
      // emits empty strings for the new fields — any row written by a
      // Phase 1.4+ pipeline run will hit the `full_data` branch above
      // and carry `recommendation_local` + `local_language_code` through.
      const farmer = FARMERS[r.farmer_id] || { name: r.farmer_id, lat: 10.8, lon: 78.8, commodity: r.commodity_id, quantity: 20 }
      return {
        farmer_id: r.farmer_id,
        farmer_name: farmer.name,
        commodity_id: r.commodity_id,
        commodity_name: r.commodity_id,
        quantity_quintals: farmer.quantity,
        farmer_lat: farmer.lat,
        farmer_lon: farmer.lon,
        best_option: {
          mandi_id: r.best_mandi_id,
          mandi_name: r.best_mandi_id,
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

    res.setHeader('Access-Control-Allow-Origin', '*')
    res.json({ sell_recommendations: result, total: result.length, source: 'neon' })
  } catch (e: any) {
    res.status(500).json({ error: e.message })
  }
}
