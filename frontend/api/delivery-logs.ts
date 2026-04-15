import type { VercelRequest, VercelResponse } from '@vercel/node'

export default async function handler(req: VercelRequest, res: VercelResponse) {
  res.setHeader('Access-Control-Allow-Origin', '*')
  try {
    const dbUrl = process.env.DATABASE_URL
    if (!dbUrl) {
      return res.json({ delivery_logs: [], total: 0 })
    }
    const { neon } = await import('@neondatabase/serverless')
    const sql = neon(dbUrl)
    const rows = await sql`
      SELECT farmer_id, farmer_name, phone, channel, sms_text, sms_text_local,
             status, error, created_at
      FROM delivery_logs
      ORDER BY created_at DESC
      LIMIT 50
    `

    res.json({ delivery_logs: rows, total: rows.length })
  } catch (e: any) {
    // Table may not exist yet if the pipeline hasn't run since delivery_logs
    // was added to the schema. Treat "undefined_table" (42P01) as empty, not 500.
    if (e?.code === '42P01' || /does not exist/i.test(e?.message ?? '')) {
      return res.json({ delivery_logs: [], total: 0 })
    }
    res.status(500).json({ delivery_logs: [], total: 0, error: e?.message ?? String(e) })
  }
}
