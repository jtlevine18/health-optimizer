interface LoadingProps {
  message?: string
}

export function LoadingSpinner({ message = 'Loading...' }: LoadingProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16">
      <div className="w-8 h-8 border-2 border-warm-border border-t-gold rounded-full animate-spin" />
      <p className="mt-4 text-sm text-warm-muted font-sans">{message}</p>
    </div>
  )
}

interface ErrorProps {
  message?: string
  onRetry?: () => void
}

export function ErrorState({ message = 'Failed to load data', onRetry }: ErrorProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16">
      <div className="w-12 h-12 rounded-full bg-red-50 flex items-center justify-center mb-3">
        <span className="text-error text-xl font-bold">!</span>
      </div>
      <p className="text-sm text-warm-body font-sans mb-3">{message}</p>
      {onRetry && (
        <button onClick={onRetry} className="btn-secondary text-xs">
          Retry
        </button>
      )}
    </div>
  )
}

/* ── Skeleton loaders ── */

export function DashboardSkeleton() {
  return (
    <div className="animate-fade-in space-y-8">
      <div className="pt-2 pb-6">
        <div className="skeleton-title mb-2" />
        <div className="skeleton-text w-2/5" />
      </div>
      <div>
        <div className="skeleton-text w-24 mb-4" />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="skeleton-card" />
          <div className="skeleton-card" />
          <div className="skeleton-card" />
        </div>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="skeleton-metric" />
        <div className="skeleton-metric" />
        <div className="skeleton-metric" />
        <div className="skeleton-metric" />
      </div>
      <div className="skeleton-chart" style={{ height: 160 }} />
    </div>
  )
}

export function TableSkeleton() {
  return (
    <div className="animate-fade-in space-y-6">
      <div className="pt-2 pb-6">
        <div className="skeleton-title mb-2" />
        <div className="skeleton-text w-2/5" />
      </div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="skeleton-metric" />
        <div className="skeleton-metric" />
        <div className="skeleton-metric" />
        <div className="skeleton-metric" />
      </div>
      <div className="skeleton-chart" style={{ height: 300 }} />
    </div>
  )
}
