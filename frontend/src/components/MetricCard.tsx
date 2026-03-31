import { useEffect, useRef, useState } from 'react'

interface Props {
  label: string
  value: string | number | undefined | null
  subtitle?: string
  className?: string
}

function useCountUp(target: string | number | undefined | null, duration = 600) {
  const [display, setDisplay] = useState<string>('--')
  const hasAnimated = useRef(false)

  useEffect(() => {
    if (target === null || target === undefined) {
      setDisplay('--')
      return
    }

    const str = String(target)

    if (hasAnimated.current) {
      setDisplay(str)
      return
    }

    const match = str.match(/(\d+)/)
    if (!match) {
      setDisplay(str)
      hasAnimated.current = true
      return
    }

    const num = parseInt(match[1], 10)
    if (num === 0) {
      setDisplay(str)
      hasAnimated.current = true
      return
    }

    const prefix = str.slice(0, match.index)
    const suffix = str.slice((match.index ?? 0) + match[1].length)
    const start = performance.now()

    function tick(now: number) {
      const elapsed = now - start
      const progress = Math.min(elapsed / duration, 1)
      const eased = 1 - Math.pow(1 - progress, 3)
      const current = Math.round(num * eased)
      setDisplay(`${prefix}${current}${suffix}`)

      if (progress < 1) {
        requestAnimationFrame(tick)
      } else {
        hasAnimated.current = true
      }
    }

    requestAnimationFrame(tick)
  }, [target, duration])

  return display
}

export default function MetricCard({ label, value, subtitle, className = '' }: Props) {
  const display = useCountUp(value)

  return (
    <div className={`metric-card ${className}`}>
      <div className="metric-label">{label}</div>
      <div className="metric-value">{display}</div>
      {subtitle && (
        <p className="text-xs text-warm-muted mt-1">{subtitle}</p>
      )}
    </div>
  )
}
