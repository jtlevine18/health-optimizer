interface Props {
  label: string
  value: string | number | undefined | null
  subtitle?: string
  className?: string
}

function format(v: string | number | undefined | null): string {
  if (v === null || v === undefined) return '—'
  return String(v)
}

export default function MetricCard({ label, value, subtitle, className = '' }: Props) {
  return (
    <div className={className}>
      <div className="metric-number">{format(value)}</div>
      <div className="metric-label">{label}</div>
      {subtitle && <div className="metric-delta">{subtitle}</div>}
    </div>
  )
}
