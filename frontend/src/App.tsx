import { useCallback, useEffect, useState } from 'react'
import { Routes, Route, useNavigate } from 'react-router-dom'
import Joyride, { type CallBackProps, STATUS, EVENTS, ACTIONS } from 'react-joyride'
import { Menu } from 'lucide-react'
import Sidebar from './components/Sidebar'
import MarketPrices from './pages/MarketPrices'
import Forecast from './pages/Forecast'
import SellOptimizer from './pages/SellOptimizer'
import Pipeline from './pages/Pipeline'
import Inputs from './pages/Inputs'
import NotFound from './pages/NotFound'
import { tourStepsForRegion, stepRoutes, tourStyles } from './lib/tour'
import { useRegion } from './lib/region'
import TourTooltip from './components/TourTooltip'
import type { Step } from 'react-joyride'

/**
 * Wait for the target element of a tour step to exist in the DOM.
 */
function waitForTourTarget(tourSteps: Step[], stepIdx: number, timeoutMs = 3000): Promise<void> {
  const step = tourSteps[stepIdx]
  if (!step || typeof step.target !== 'string') return Promise.resolve()
  const selector = step.target
  const start = performance.now()
  return new Promise((resolve) => {
    function tick() {
      if (document.querySelector(selector)) {
        resolve()
        return
      }
      if (performance.now() - start >= timeoutMs) {
        resolve()
        return
      }
      requestAnimationFrame(tick)
    }
    requestAnimationFrame(tick)
  })
}

export default function App() {
  const [runTour, setRunTour] = useState(false)
  const [stepIndex, setStepIndex] = useState(0)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const navigate = useNavigate()
  const region = useRegion()
  const tourSteps = tourStepsForRegion(region)

  // Listen for a manual relaunch event. Autostart is disabled by default.
  useEffect(() => {
    function handleRelaunch() {
      navigate('/')
      setTimeout(() => {
        setStepIndex(0)
        setRunTour(true)
      }, 400)
    }
    window.addEventListener('relaunch-tour', handleRelaunch)
    return () => window.removeEventListener('relaunch-tour', handleRelaunch)
  }, [navigate])

  const handleJoyrideCallback = useCallback(
    (data: CallBackProps) => {
      const { status, action, index, type } = data

      if (status === STATUS.FINISHED || status === STATUS.SKIPPED || action === ACTIONS.CLOSE) {
        setRunTour(false)
        setStepIndex(0)
        return
      }

      if (type === EVENTS.STEP_AFTER) {
        const nextIndex = action === ACTIONS.PREV ? index - 1 : index + 1
        const nextRoute = stepRoutes[nextIndex]
        const currentRoute = stepRoutes[index]
        const needsNav = nextRoute !== undefined && nextRoute !== currentRoute

        setRunTour(false)

        if (needsNav) {
          navigate(nextRoute!)
        }

        waitForTourTarget(tourSteps, nextIndex, 3000).then(() => {
          setStepIndex(nextIndex)
          setRunTour(true)
        })
      }
    },
    [navigate, tourSteps],
  )

  return (
    <div className="flex min-h-screen" style={{ background: '#ffffff' }}>
      <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />

      <div className="flex-1 lg:ml-56 flex flex-col min-w-0">
        <header
          className="flex items-center h-12 px-4 lg:hidden"
          style={{ background: '#ffffff' }}
        >
          <button
            onClick={() => setSidebarOpen(true)}
            aria-label="Open navigation menu"
            className="p-2 -ml-2"
            style={{ color: '#606373', background: 'none', border: 'none' }}
          >
            <Menu size={20} />
          </button>
        </header>
        <main className="flex-1 px-4 sm:px-8 lg:px-14 pt-6 lg:pt-16 pb-16" style={{ maxWidth: '1180px' }}>
          <Routes>
            <Route path="/" element={<MarketPrices />} />
            <Route path="/forecast" element={<Forecast />} />
            <Route path="/sell" element={<SellOptimizer />} />
            <Route path="/pipeline" element={<Pipeline />} />
            <Route path="/inputs" element={<Inputs />} />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </main>
      </div>

      <Joyride
        steps={tourSteps}
        run={runTour}
        stepIndex={stepIndex}
        continuous
        showSkipButton
        scrollToFirstStep
        disableOverlayClose
        spotlightClicks={false}
        callback={handleJoyrideCallback}
        styles={tourStyles}
        tooltipComponent={TourTooltip}
        floaterProps={{ disableAnimation: false }}
        locale={{
          back: 'Back',
          close: 'Close',
          last: 'Finish',
          next: 'Next',
          skip: 'Skip tour',
        }}
      />
    </div>
  )
}
