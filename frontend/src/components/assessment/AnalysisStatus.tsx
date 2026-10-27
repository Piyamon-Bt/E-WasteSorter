import { Loader2 } from 'lucide-react'
import { useAssessment } from '../../state/AssessmentContext'
import { useBackend } from '../../state/Backend'
import { useNavigation } from '../../state/Navigation'
import { selectMissingSlots } from '../../state/selectors'
import { Button } from '../ui/Button'
import { FadeSwap } from '../ui/FadeSwap'
import { Notice } from '../ui/Notice'

export function AnalysisStatus() {
  const { state, actions } = useAssessment()
  const { isMock } = useBackend()
  const { goToSection } = useNavigation()
  const { analysis } = state
  const missing = selectMissingSlots(state)
  const hasPhotoProblems = state.photoProblems.slotProblems.length > 0 || state.photoProblems.imageIssues.some((i) => i.blocking)

  const statusLabel = { idle: 'Not started', processing: 'Processing', complete: 'Complete', failed: 'Stopped' }[analysis.status]

  return (
    <div className="space-y-8">
      <div className="flex items-center gap-3">
        <span className="text-[13px] tracking-[0.08em] text-muted uppercase">Status</span>
        <span className="text-[16px] font-medium text-ink">{statusLabel}</span>
      </div>

      <FadeSwap swapKey={analysis.status} className="space-y-5">
        {analysis.status === 'idle' && (
          <>
            <p className="text-[16px] text-muted">
              {!state.deviceType
                ? 'Choose a device and add its photos first.'
                : missing.length
                  ? `${missing.length} required view${missing.length > 1 ? 's are' : ' is'} still missing.`
                  : 'All required views are ready. Analysis starts only when you choose to.'}
            </p>
            {state.deviceType && missing.length === 0 ? (
              <Button onClick={actions.startAnalysis}>Analyze photos</Button>
            ) : (
              <Button variant="secondary" onClick={() => goToSection('device')}>
                Go to photos
              </Button>
            )}
          </>
        )}

        {analysis.status === 'processing' && (
          <p className="flex items-center gap-3 text-[16px] text-ink">
            <Loader2 aria-hidden className="size-4 animate-spin motion-reduce:animate-none" />
            {isMock ? 'Preparing simulated observations…' : 'Assessing all views together…'}
          </p>
        )}

        {analysis.status === 'complete' && analysis.data && (
          <>
            <p className="text-[16px] text-ink">{analysis.data.summary}</p>
            <p className="text-[15px] text-muted">
              {analysis.data.observations.length} observation{analysis.data.observations.length === 1 ? '' : 's'} to review.
            </p>
            <Button onClick={() => goToSection('review')}>Review observations</Button>
          </>
        )}

        {analysis.status === 'failed' && (
          <>
            <p role="alert" className="text-[16px] text-danger">
              {analysis.error}
            </p>
            {hasPhotoProblems ? (
              <Button variant="secondary" onClick={() => goToSection('device')}>
                Replace the marked photos
              </Button>
            ) : (
              <Button onClick={actions.startAnalysis}>Retry</Button>
            )}
            <p className="text-[14px] text-muted">No observations were invented: nothing is shown until an analysis succeeds.</p>
          </>
        )}
      </FadeSwap>

      <Notice>
        {isMock
          ? 'Demo mode: your photos are checked for quality, but their content is not analyzed. Observations are simulated.'
          : 'Photos are sent to the configured AI provider for this analysis and are not stored by this app.'}
      </Notice>
    </div>
  )
}
