import { NavLink, Link } from 'react-router-dom'
import {
  Home,
  TrendingUp,
  IndianRupee,
  Settings,
  FileText,
} from 'lucide-react'
import { usePipelineRuns } from '../lib/api'

const NAV_ITEMS = [
  { to: '/', label: 'Home', icon: Home, tourId: 'nav-home' },
  { to: '/inputs', label: 'Data', icon: FileText, tourId: 'nav-inputs' },
  { to: '/forecast', label: 'Forecast', icon: TrendingUp, tourId: 'nav-forecast' },
  { to: '/sell', label: 'Sell Advisor', icon: IndianRupee, tourId: 'nav-sell' },
  { to: '/pipeline', label: 'How it works', icon: Settings, tourId: 'nav-pipeline' },
]

export default function Sidebar() {
  const { data: runsData } = usePipelineRuns()
  const dataMode = runsData?.runs?.[0]?.steps?.find((s) => s.step === 'ingest')?.details?.data_source_mode

  return (
    <aside
      className="fixed top-0 left-0 z-50 h-full w-56 flex flex-col"
      style={{ background: '#1b1e2d' }}
    >
      {/* Brand */}
      <div
        className="flex items-center h-16 px-5"
        style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}
      >
        <Link to="/" className="flex items-baseline gap-2 no-underline">
          <span
            style={{
              fontFamily: '"Source Serif 4", Georgia, serif',
              fontSize: '18px',
              fontWeight: 400,
              color: '#fcfaf7',
              letterSpacing: '-0.005em',
            }}
          >
            Crop pricing agent
          </span>
        </Link>
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-4 overflow-y-auto">
        {NAV_ITEMS.map(({ to, label, icon: Icon, tourId }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            data-tour={tourId}
            className="sidebar-link"
          >
            <Icon size={16} style={{ flexShrink: 0 }} />
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>

      {dataMode && (
        <div
          style={{
            padding: '12px 20px 6px',
            borderTop: '1px solid rgba(255,255,255,0.06)',
            fontFamily: '"Space Grotesk", system-ui, sans-serif',
            fontSize: '10px',
            fontWeight: 500,
            letterSpacing: '0.08em',
            textTransform: 'uppercase',
            color: dataMode === 'live' ? '#9ce0b5' : '#e0c884',
          }}
        >
          {dataMode === 'live' ? 'Live · Agmarknet data.gov.in' : 'Demo · seed=42'}
        </div>
      )}
      <div
        style={{
          padding: dataMode ? '0 20px 12px' : '12px 20px',
          borderTop: dataMode ? undefined : '1px solid rgba(255,255,255,0.06)',
          fontFamily: '"Space Grotesk", system-ui, sans-serif',
          fontSize: '10px',
          color: '#8d909e',
        }}
      >
        Farmer personas are simulated
      </div>

      <style>{`
        .sidebar-link {
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 10px 20px;
          font-family: "Space Grotesk", system-ui, sans-serif;
          font-size: 13px;
          font-weight: 500;
          color: #8d909e;
          border-left: 2px solid transparent;
          text-decoration: none;
          transition: color 0.15s ease, border-color 0.15s ease;
        }
        .sidebar-link:hover {
          color: #fcfaf7;
        }
        .sidebar-link.active {
          color: #fcfaf7;
          border-left-color: #446b26;
        }
      `}</style>
    </aside>
  )
}
