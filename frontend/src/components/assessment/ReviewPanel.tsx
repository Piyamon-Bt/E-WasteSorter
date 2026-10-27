import { AlertTriangle, ImagePlus, Loader2 } from 'lucide-react'
import { useState } from 'react'
import { viewLabel } from '../../content/devices'
import { kindLabels, kindOrder, responseLabels } from '../../content/labels'
import { preparePhotos } from '../../lib/photos'
import { useAssessment } from '../../state/AssessmentContext'
import { emptyReview } from '../../state/assessmentReducer'
import { useNavigation } from '../../state/Navigation'
import { selectUnreviewed } from '../../state/selectors'
import type { Observation, UserResponse } from '../../types/api'
import { Button } from '../ui/Button'
import { ChoiceGroup } from '../ui/ChoiceGroup'
import { FilePickButton } from '../ui/FilePickButton'
import { Notice } from '../ui/Notice'

const responseOptions = (Object.keys(responseLabels) as UserResponse[]).map((value) => ({ value, label: responseLabels[value] }))
const MAX_EXTRA = 4

const outcomeText = {
  upheld: 'The re-check still supports this observation.',
  revised: 'The re-check corrected this observation.',
  not_supported: 'The new photos do not show this issue. It is withdrawn.',
  unresolved: 'The evidence is still not clear enough to decide.',
}

function ObservationCard({ observation }: { observation: Observation }) {
  const { state, actions } = useAssessment()
  const [error, setError] = useState('')
  const review = state.reviews[observation.id] ?? emptyReview
  const followUp = state.followUps[observation.id]
  const shown = followUp?.revised_observation ?? observation
  const photos = state.photos.filter((p) => shown.views.includes(p.slot))
  const isRisk = observation.kind === 'suspected_safety_risk'
  const canRecheck = review.response === 'disagree' || review.response === 'unsure'

  async function addExtra(files: File[]) {
    const { photos: added, errors } = await preparePhotos(files, 'followup', MAX_EXTRA - review.extraPhotos.length)
    setError(errors.join(' '))
    if (added.length) actions.addExtraPhotos(observation.id, added)
  }

  return (
    <li className={`rounded-lg border p-5 ${isRisk ? 'border-danger' : 'border-line'}`}>
      <p className={`flex items-center gap-2 text-[13px] tracking-[0.06em] uppercase ${isRisk ? 'text-danger' : 'text-muted'}`}>
        {isRisk && <AlertTriangle aria-hidden className="size-4" />}
        {kindLabels[shown.kind]}
      </p>
      <h4 className="mt-1 text-[17px] font-medium text-ink">{shown.part}</h4>
      <p className="mt-2 text-[15px] text-ink">{shown.description}</p>
      <dl className="mt-3 grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-[14px]">
        <dt className="text-muted">Evidence</dt>
        <dd className="text-ink">{shown.visible_evidence}</dd>
        <dt className="text-muted">Uncertainty</dt>
        <dd className="text-ink">
          {shown.uncertainty} — {shown.uncertainty_reason}
        </dd>
        <dt className="text-muted">Photos</dt>
        <dd className="text-ink">{shown.views.map((v) => viewLabel(state.deviceType, v)).join(', ') || 'None'}</dd>
      </dl>
      {photos.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-2">
          {photos.map((p) => (
            <img key={p.id} src={p.url} alt={`Supporting photo: ${viewLabel(state.deviceType, p.slot)}`} className="h-24 rounded-md border border-line object-cover" />
          ))}
        </div>
      )}

      {observation.kind !== 'unassessable' && (
        <div className="mt-5 space-y-4">
          <ChoiceGroup
            legend="Does this match your device?"
            name={`review-${observation.id}`}
            value={review.response}
            options={responseOptions}
            onChange={(r) => actions.respond(observation.id, r)}
          />
          <label className="block text-[14px] text-muted">
            Explain (optional)
            <textarea
              value={review.note}
              maxLength={1000}
              onChange={(e) => actions.setReviewNote(observation.id, e.target.value)}
              className="mt-1 min-h-20 w-full rounded-md border border-line px-3 py-2 text-[15px] text-ink"
            />
          </label>

          {canRecheck && (
            <div className="space-y-3 rounded-md bg-faint p-4">
              <p className="text-[14px] text-ink">
                {isRisk
                  ? 'Disagreeing does not clear a safety risk. Add close-up photos of this area (including edge-on views) so it can be re-checked.'
                  : 'Add photos of this area to have it re-checked, or continue and it will be recorded as disputed.'}
              </p>
              {review.extraPhotos.length > 0 && (
                <ul className="flex flex-wrap gap-2">
                  {review.extraPhotos.map((p, i) => (
                    <li key={p.id} className="w-24">
                      <img src={p.url} alt={`New photo ${i + 1}`} className="aspect-square w-full rounded-md border border-line object-cover" />
                      <Button variant="quiet" className="-ml-3" onClick={() => actions.removeExtraPhoto(observation.id, p.id)}>
                        Remove
                      </Button>
                    </li>
                  ))}
                </ul>
              )}
              <div className="flex flex-wrap gap-2">
                <FilePickButton multiple disabled={review.extraPhotos.length >= MAX_EXTRA} onFiles={(f) => void addExtra(f)}>
                  <ImagePlus aria-hidden className="size-4" /> Add photos
                </FilePickButton>
                <Button
                  onClick={() => actions.requestFollowUp(observation.id)}
                  disabled={review.followUpStatus === 'processing' || review.extraPhotos.length === 0}
                >
                  {review.followUpStatus === 'processing' ? (
                    <>
                      <Loader2 aria-hidden className="size-4 animate-spin motion-reduce:animate-none" /> Re-checking…
                    </>
                  ) : (
                    'Re-check with new photos'
                  )}
                </Button>
              </div>
              {error && <p className="text-[14px] text-danger">{error}</p>}
              {review.followUpError && (
                <p role="alert" className="text-[14px] text-danger">
                  Re-check failed: {review.followUpError}
                </p>
              )}
            </div>
          )}
          {followUp && (
            <p className="text-[14px] text-ink" aria-live="polite">
              <span className="font-medium">Re-check result{followUp.source === 'simulated' ? ' (simulated)' : ''}:</span>{' '}
              {outcomeText[followUp.outcome]} {followUp.explanation}
            </p>
          )}
        </div>
      )}
    </li>
  )
}

export function ReviewPanel() {
  const { state, actions } = useAssessment()
  const { goToSection } = useNavigation()
  const result = state.analysis.data

  if (state.analysis.status !== 'complete' || !result) {
    return (
      <div className="space-y-5">
        <Notice>Observations appear here once an analysis has completed.</Notice>
        <Button variant="secondary" onClick={() => goToSection('analyze')}>
          Go to Analyze
        </Button>
      </div>
    )
  }

  const unreviewed = selectUnreviewed(state)
  const sorted = [...result.observations].sort((a, b) => kindOrder.indexOf(a.kind) - kindOrder.indexOf(b.kind))
  const anyFollowUpRunning = Object.values(state.reviews).some((r) => r.followUpStatus === 'processing')

  return (
    <div className="space-y-10">
      {result.source === 'simulated' && (
        <p className="inline-block rounded-sm border border-line px-3 py-1.5 text-[14px] text-ink">
          Simulated observations — not derived from your photos.
        </p>
      )}
      <ul className="space-y-6">
        {sorted.map((o) => (
          <ObservationCard key={o.id} observation={o} />
        ))}
      </ul>

      {result.unassessable_areas.length > 0 && (
        <div>
          <h3 className="text-[17px] font-medium text-ink">Not assessable from photos</h3>
          <ul className="mt-3 space-y-1 text-[15px] text-ink">
            {result.unassessable_areas.map((u) => (
              <li key={u} className="flex gap-2">
                <span aria-hidden className="text-muted">
                  –
                </span>
                {u}
              </li>
            ))}
          </ul>
          <p className="mt-3 text-[14px] text-muted">
            “No visible damage” is about appearance only. It does not mean the device works.
          </p>
        </div>
      )}

      <div className="space-y-3">
        <Button
          onClick={() => {
            actions.confirmReview()
            goToSection('functionality')
          }}
          disabled={unreviewed.length > 0 || anyFollowUpRunning || state.plan.status === 'processing'}
        >
          Continue to functional checks
        </Button>
        {unreviewed.length > 0 && (
          <p className="text-[15px] text-muted">Respond to every observation first ({unreviewed.length} left).</p>
        )}
        {state.plan.status === 'failed' && (
          <p role="alert" className="text-[15px] text-danger">
            {state.plan.error}
          </p>
        )}
      </div>
    </div>
  )
}
