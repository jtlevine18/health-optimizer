interface Props {
  status: string
  className?: string
}

const STATUS_COLOR: Record<string, string> = {
  critical: '#c71f48',
  high: '#2d4a1a',
  moderate: '#446b26',
  low: '#4a7c59',
  none: '#606373',
  good: '#4a7c59',
  poor: '#c71f48',
  ok: '#4a7c59',
  success: '#4a7c59',
  active: '#4a7c59',
  partial: '#446b26',
  failed: '#c71f48',
  running: '#1b1e2d',
  pending: '#606373',
}

export default function StatusBadge({ status, className = '' }: Props) {
  const color = STATUS_COLOR[status] ?? '#606373'
  return (
    <span
      className={className}
      style={{
        fontFamily: '"Space Grotesk", system-ui, sans-serif',
        fontSize: '12px',
        fontWeight: 500,
        color,
      }}
    >
      {status}
    </span>
  )
}
