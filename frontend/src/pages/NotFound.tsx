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

      <div style={{ maxWidth: 560, paddingTop: '8px' }}>
        <p
          style={{
            fontFamily: '"Space Grotesk", system-ui, sans-serif',
            fontSize: '14px',
            color: '#606373',
            marginBottom: '20px',
            lineHeight: 1.7,
          }}
        >
          Double-check the URL, or head back to the dashboard to see current
          market prices, forecasts, and sell recommendations.
        </p>
        <Link to="/" className="text-link">
          Back to dashboard &rarr;
        </Link>
      </div>
    </div>
  )
}
