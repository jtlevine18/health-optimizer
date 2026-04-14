interface LoadingProps {
  message?: string
}

export function LoadingSpinner({ message = 'Loading' }: LoadingProps) {
  return (
    <div className="py-16">
      <p className="eyebrow">{message}</p>
    </div>
  )
}

interface ErrorProps {
  message?: string
  onRetry?: () => void
}

export function ErrorState({ message = 'Failed to load data', onRetry }: ErrorProps) {
  return (
    <div className="py-16">
      <p className="eyebrow" style={{ color: '#c71f48' }}>Error</p>
      <p
        style={{
          fontFamily: '"Space Grotesk", system-ui, sans-serif',
          fontSize: '14px',
          color: '#606373',
          marginTop: '8px',
          marginBottom: '16px',
        }}
      >
        {message}
      </p>
      {onRetry && (
        <button onClick={onRetry} className="btn-secondary">
          Retry
        </button>
      )}
    </div>
  )
}

/* ── Skeleton loaders ── */

export function DashboardSkeleton() {
  return (
    <div className="animate-fade-in space-y-10">
      <div className="pt-2 pb-6">
        <div className="skeleton-title mb-3" />
        <div className="skeleton-text" style={{ width: '40%' }} />
      </div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
        <div className="skeleton-metric" />
        <div className="skeleton-metric" />
        <div className="skeleton-metric" />
        <div className="skeleton-metric" />
      </div>
      <div className="skeleton-chart" style={{ height: 200 }} />
    </div>
  )
}

export function TableSkeleton() {
  return (
    <div className="animate-fade-in space-y-8">
      <div className="pt-2 pb-6">
        <div className="skeleton-title mb-3" />
        <div className="skeleton-text" style={{ width: '40%' }} />
      </div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
        <div className="skeleton-metric" />
        <div className="skeleton-metric" />
        <div className="skeleton-metric" />
        <div className="skeleton-metric" />
      </div>
      <div className="skeleton-chart" style={{ height: 300 }} />
    </div>
  )
}
