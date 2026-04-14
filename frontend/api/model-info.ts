import type { VercelRequest, VercelResponse } from '@vercel/node'

export default async function handler(_req: VercelRequest, res: VercelResponse) {
  res.setHeader('Access-Control-Allow-Origin', '*')

  const metrics: Record<string, number | null> = {
    rmse: null,
    mae: null,
    r2: null,
    directional_accuracy: null,
    train_samples: null,
  }

  try {
    const dbUrl = process.env.DATABASE_URL
    if (dbUrl) {
      const { neon } = await import('@neondatabase/serverless')
      const sql = neon(dbUrl)
      const rows = (await sql`
        SELECT metric_name, metric_value
        FROM model_metrics
        WHERE run_id = (
          SELECT run_id FROM model_metrics ORDER BY created_at DESC LIMIT 1
        )
      `) as Array<{ metric_name: string; metric_value: number }>

      for (const r of rows) {
        if (r.metric_name in metrics) {
          metrics[r.metric_name] = r.metric_value
        }
      }
    }
  } catch {
    // Fall through with null metrics
  }

  const hasLive = metrics.rmse != null || metrics.mae != null || metrics.r2 != null

  res.json({
    model_metrics: {
      model_type: 'chronos_xgboost_mos',
      ...metrics,
      features: [
        'current_reconciled_price',
        'price_trend_7d',
        'seasonal_index',
        'mandi_arrival_volume_7d_avg',
        'rainfall_7d',
        'days_since_harvest',
      ],
    },
    source: hasLive ? 'neon' : 'static',
  })
}
