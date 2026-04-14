import { useMemo } from 'react'
import { useMarketPrices } from '../lib/api'
import { formatRs } from '../lib/format'

function abbreviateCommodity(name: string): string {
  const abbrevs: Record<string, string> = {
    paddy: 'PADDY',
    rice: 'RICE',
    groundnut: 'GNUT',
    turmeric: 'TURM',
    cotton: 'COTN',
    maize: 'MAIZE',
    banana: 'BANA',
    coconut: 'COCO',
    'coconut (copra)': 'COPA',
    onion: 'ONIN',
    'black gram': 'BGRAM',
    'black gram (urad)': 'URAD',
    'green gram (moong)': 'MUNG',
  }
  const lower = name.toLowerCase()
  return abbrevs[lower] ?? name.slice(0, 5).toUpperCase()
}

function priceMarker(price: number, avgPrice: number): {
  color: string
  prefix: string
} {
  const ratio = price / avgPrice
  if (ratio >= 1.05) return { color: '#4a7c59', prefix: '↑ ' }
  if (ratio <= 0.95) return { color: '#c71f48', prefix: '↓ ' }
  return { color: '#1b1e2d', prefix: '' }
}

export function PriceGrid() {
  const prices = useMarketPrices()

  const priceGrid = useMemo(() => {
    if (!prices.data?.market_prices?.length) return null

    const priceList = prices.data.market_prices

    const mandiMap = new Map<string, string>()
    const commodityMap = new Map<string, string>()
    for (const p of priceList) {
      if (!mandiMap.has(p.mandi_id)) mandiMap.set(p.mandi_id, p.mandi_name)
      if (!commodityMap.has(p.commodity_id))
        commodityMap.set(p.commodity_id, p.commodity_name)
    }

    const mandiList = Array.from(mandiMap.entries())
    const commodityList = Array.from(commodityMap.entries())

    const lookup = new Map<string, (typeof priceList)[0]>()
    for (const p of priceList) {
      lookup.set(`${p.mandi_id}|${p.commodity_id}`, p)
    }

    const avgPrices = new Map<string, number>()
    for (const [cid] of commodityList) {
      const commodityPrices = priceList.filter((p) => p.commodity_id === cid)
      if (commodityPrices.length) {
        const avg =
          commodityPrices.reduce((s, p) => s + p.reconciled_price_rs, 0) /
          commodityPrices.length
        avgPrices.set(cid, avg)
      }
    }

    return { mandis: mandiList, commodities: commodityList, lookup, avgPrices }
  }, [prices.data])

  if (!priceGrid) return <p className="eyebrow">No price data available</p>

  return (
    <div style={{ overflowX: 'auto' }}>
      <table className="etable" style={{ minWidth: 560 }}>
        <thead>
          <tr>
            <th>Market</th>
            {priceGrid.commodities.map(([cid, cname]) => (
              <th
                key={cid}
                className="num"
                title={cname}
                style={{ textAlign: 'right' }}
              >
                {abbreviateCommodity(cname)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {priceGrid.mandis.map(([mid, mname]) => (
            <tr key={mid}>
              <td style={{ whiteSpace: 'nowrap', fontWeight: 500 }}>{mname}</td>
              {priceGrid.commodities.map(([cid]) => {
                const entry = priceGrid.lookup.get(`${mid}|${cid}`)
                if (!entry) {
                  return (
                    <td
                      key={cid}
                      className="num"
                      style={{ textAlign: 'right', color: '#c4bfb6' }}
                    >
                      —
                    </td>
                  )
                }
                const avg =
                  priceGrid.avgPrices.get(cid) ?? entry.reconciled_price_rs
                const marker = priceMarker(entry.reconciled_price_rs, avg)
                return (
                  <td
                    key={cid}
                    className="num"
                    title={`${entry.commodity_name}: ${formatRs(entry.reconciled_price_rs)}`}
                    style={{ textAlign: 'right', color: marker.color }}
                  >
                    {marker.prefix}
                    {formatRs(entry.reconciled_price_rs)}
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>

      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '24px',
          marginTop: '16px',
          fontFamily: '"Space Grotesk", system-ui, sans-serif',
          fontSize: '12px',
          color: '#606373',
        }}
      >
        <span className="eyebrow">vs seasonal avg</span>
        <span style={{ color: '#4a7c59' }}>↑ above (+5%)</span>
        <span style={{ color: '#1b1e2d' }}>near average</span>
        <span style={{ color: '#c71f48' }}>↓ below (−5%)</span>
      </div>
    </div>
  )
}
