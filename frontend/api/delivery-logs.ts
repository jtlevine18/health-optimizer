import type { VercelRequest, VercelResponse } from '@vercel/node'

export default async function handler(req: VercelRequest, res: VercelResponse) {
  try {
    const dbUrl = process.env.DATABASE_URL
    if (!dbUrl) {
      res.setHeader('Access-Control-Allow-Origin', '*')
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

    res.setHeader('Access-Control-Allow-Origin', '*')
    res.json({ delivery_logs: rows, total: rows.length })
  } catch (e: any) {
    res.status(500).json({ delivery_logs: [], total: 0, error: e.message })
  }
}
