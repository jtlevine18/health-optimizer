import { Link } from 'react-router-dom'

export default function NotFound() {
  return (
    <div className="animate-slide-up">
      <div className="pt-2 pb-6">
        <h1 className="page-title">Page not found</h1>
        <p className="page-caption">
          The page you were looking for doesn't exist or has moved.
        </p>
      </div>

      <div className="card card-body" style={{ maxWidth: 560 }}>
        <p className="text-sm text-warm-body m-0 mb-4 leading-relaxed">
          Double-check the URL, or head back to the dashboard to see current
          mandi prices, forecasts, and sell recommendations.
        </p>
        <Link
          to="/"
          className="inline-flex items-center text-xs font-sans font-semibold uppercase tracking-wider"
          style={{
            color: '#0d7377',
            letterSpacing: '0.5px',
            textDecoration: 'none',
          }}
        >
          Back to dashboard &rarr;
        </Link>
      </div>
    </div>
  )
}
