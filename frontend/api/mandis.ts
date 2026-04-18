import type { VercelRequest, VercelResponse } from '@vercel/node'
import { getMandis, getRegion } from './_region'

export default async function handler(req: VercelRequest, res: VercelResponse) {
  res.setHeader('Access-Control-Allow-Origin', '*')
  const region = getRegion()
  const mandis = getMandis(region)
  res.json({ mandis, total: mandis.length, region, source: 'static' })
}
