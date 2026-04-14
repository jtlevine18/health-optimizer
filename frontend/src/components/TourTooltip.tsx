import type { TooltipRenderProps } from 'react-joyride'
import { tourStyles, tourSteps } from '../lib/tour'

export default function TourTooltip({
  continuous,
  index,
  step,
  backProps,
  closeProps,
  primaryProps,
  skipProps,
  isLastStep,
}: TooltipRenderProps) {
  const styles = tourStyles

  return (
    <div
      style={{
        ...styles.tooltip,
        backgroundColor: styles.options.backgroundColor,
        color: styles.options.textColor,
      }}
    >
      {/* Title */}
      {step.title && (
        <div style={styles.tooltipTitle}>{step.title}</div>
      )}

      {/* Content */}
      <div style={styles.tooltipContent}>{step.content}</div>

      {/* Step counter */}
      <div
        style={{
          color: '#8d909e',
          fontSize: '12px',
          fontFamily: '"Space Grotesk", system-ui, sans-serif',
          marginTop: 12,
        }}
      >
        Step {index + 1} of {tourSteps.length}
      </div>

      {/* Buttons */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginTop: 14,
        }}
      >
        <button {...skipProps} style={styles.buttonSkip}>
          Skip tour
        </button>
        <div style={{ display: 'flex', alignItems: 'center' }}>
          {index > 0 && (
            <button {...backProps} style={styles.buttonBack}>
              Back
            </button>
          )}
          {continuous && (
            <button {...primaryProps} style={styles.buttonNext}>
              {isLastStep ? 'Finish' : 'Next'}
            </button>
          )}
          {!continuous && (
            <button {...closeProps} style={styles.buttonNext}>
              Close
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
