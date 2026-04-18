import type { VercelRequest, VercelResponse } from '@vercel/node'
import { getRegion } from './_region.js'

export default async function handler(_req: VercelRequest, res: VercelResponse) {
  res.setHeader('Cache-Control', 'public, max-age=60')
  res.json({ region: getRegion() })
}
