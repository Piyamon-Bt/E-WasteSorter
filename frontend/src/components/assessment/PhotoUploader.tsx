import { ImagePlus, RefreshCw, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { DETAIL_SLOT, deviceById } from '../../content/devices'
import { preparePhoto, preparePhotos } from '../../lib/photos'
import { useAssessment } from '../../state/AssessmentContext'
import { useNavigation } from '../../state/Navigation'
import { MAX_DETAIL_PHOTOS, selectDetailPhotos, selectMissingSlots } from '../../state/selectors'
import { Button } from '../ui/Button'
import { FilePickButton } from '../ui/FilePickButton'
import { Notice } from '../ui/Notice'

const GUIDANCE = [
  'Keep the device switched off for all photos. Power-on checks come later, after the physical review.',
  'Use good, even light and avoid reflections on the screen.',
  'Fill the frame with the device and keep it in focus.',
  'Add close-ups of any damage, labels or model numbers as additional detail photos.',
  'Do not open or take the device apart.',
]

/** Required view slots for the selected device, plus optional detail photos. */
export function PhotoUploader() {
  const { state, actions } = useAssessment()
  const { goToSection } = useNavigation()
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [busy, setBusy] = useState(false)

  if (!state.deviceType) {
    return <Notice>Choose Laptop or Mobile phone to see which photos are needed.</Notice>
  }
  const device = deviceById[state.deviceType]
  const missing = selectMissingSlots(state)
  const details = selectDetailPhotos(state)
  const processing = state.analysis.status === 'processing'
  const serverIssue = (slot: string) => state.photoProblems.imageIssues.filter((i) => i.view === slot)

  async function setSlot(slot: string, files: File[]) {
    if (!files[0]) return
    setBusy(true)
    const { photo, error } = await preparePhoto(files[0], slot)
    setBusy(false)
    setErrors((e) => ({ ...e, [slot]: error ?? '' }))
    if (photo) actions.setSlotPhoto(slot, photo)
  }

  async function addDetails(files: File[]) {
    setBusy(true)
    const { photos, errors: errs } = await preparePhotos(files, DETAIL_SLOT, MAX_DETAIL_PHOTOS - details.length)
    setBusy(false)
    setErrors((e) => ({ ...e, [DETAIL_SLOT]: errs.join(' ') }))
    if (photos.length) actions.addDetailPhotos(photos)
  }

  function analyze() {
    actions.startAnalysis()
    goToSection('analyze')
  }

  return (
    <div className="space-y-10">
      <p className="text-[15px] text-muted">
        Assign each photo to its view. JPG, PNG or WebP, up to 10 MB each. The app checks that every slot is
        filled and that photos are usable; it cannot confirm that a photo really shows the named view.
      </p>

      <ul className="grid grid-cols-1 gap-x-6 gap-y-8 sm:grid-cols-2" aria-label="Required views">
        {device.views.map((view) => {
          const photo = state.photos.find((p) => p.slot === view.id)
          const issues = serverIssue(view.id)
          return (
            <li key={view.id} className="min-w-0">
              <p className="text-[15px] font-medium text-ink">{view.label}</p>
              <p className="text-[13px] text-muted">{view.hint}</p>
              <div className="mt-2 aspect-[4/3] overflow-hidden rounded-md border border-line bg-faint">
                {photo ? (
                  <img src={photo.url} alt={`${view.label} photo`} className="size-full object-contain" />
                ) : (
                  <div className="flex size-full items-center justify-center text-[13px] text-muted">No photo yet</div>
                )}
              </div>
              <div className="mt-2 flex flex-wrap gap-1">
                <FilePickButton
                  variant={photo ? 'quiet' : 'secondary'}
                  className={photo ? '-ml-3' : ''}
                  disabled={busy || processing}
                  label={`${photo ? 'Replace' : 'Add'} photo: ${view.label}`}
                  onFiles={(files) => void setSlot(view.id, files)}
                >
                  {photo ? <RefreshCw aria-hidden className="size-4" /> : <ImagePlus aria-hidden className="size-4" />}
                  {photo ? 'Replace' : 'Add photo'}
                </FilePickButton>
                {photo && (
                  <Button variant="quiet" disabled={processing} aria-label={`Remove photo: ${view.label}`} onClick={() => actions.removePhoto(photo.id)}>
                    <Trash2 aria-hidden className="size-4" /> Remove
                  </Button>
                )}
              </div>
              {(errors[view.id] || issues.length > 0) && (
                <ul className="mt-1 space-y-1 text-[14px]" aria-live="polite">
                  {errors[view.id] && <li className="text-danger">{errors[view.id]}</li>}
                  {issues.map((i) => (
                    <li key={i.problem} className={i.blocking ? 'text-danger' : 'text-muted'}>
                      {i.blocking ? 'Replace this photo: ' : 'Note: '}
                      {i.problem}
                    </li>
                  ))}
                </ul>
              )}
            </li>
          )
        })}
      </ul>

      <div>
        <h3 className="text-[15px] font-medium text-ink">Additional detail (optional)</h3>
        <p className="text-[14px] text-muted">
          Close-ups of damage, labels or model numbers. Up to {MAX_DETAIL_PHOTOS}.
        </p>
        {details.length > 0 && (
          <ul className="mt-3 flex flex-wrap gap-3" aria-label="Additional detail photos">
            {details.map((p, i) => (
              <li key={p.id} className="w-28">
                <img src={p.url} alt={`Additional detail ${i + 1}`} className="aspect-square w-full rounded-md border border-line object-cover" />
                <Button variant="quiet" className="-ml-3" disabled={processing} aria-label={`Remove detail photo ${i + 1}`} onClick={() => actions.removePhoto(p.id)}>
                  Remove
                </Button>
              </li>
            ))}
          </ul>
        )}
        <div className="mt-3">
          <FilePickButton multiple disabled={busy || processing || details.length >= MAX_DETAIL_PHOTOS} onFiles={(f) => void addDetails(f)}>
            <ImagePlus aria-hidden className="size-4" /> Add detail photos
          </FilePickButton>
        </div>
        {errors[DETAIL_SLOT] && <p className="mt-2 text-[14px] text-danger">{errors[DETAIL_SLOT]}</p>}
        {serverIssue(DETAIL_SLOT).map((i) => (
          <p key={i.filename + i.problem} className="mt-1 text-[14px] text-danger">
            {i.filename}: {i.problem}
          </p>
        ))}
      </div>

      <div>
        <h3 className="text-[15px] font-medium text-ink">Capture tips</h3>
        <ul className="mt-2 space-y-1 text-[15px] text-muted">
          {GUIDANCE.map((g) => (
            <li key={g} className="flex gap-2">
              <span aria-hidden>–</span>
              {g}
            </li>
          ))}
        </ul>
      </div>

      <div className="space-y-3">
        <Button onClick={analyze} disabled={missing.length > 0 || processing || busy}>
          {processing ? 'Analyzing…' : 'Analyze photos'}
        </Button>
        {missing.length > 0 && (
          <p className="text-[15px] text-muted" aria-live="polite">
            Still needed: {missing.map((m) => m.label).join(', ')}.
          </p>
        )}
        {state.photoProblems.slotProblems.map((p) => (
          <p key={p} role="alert" className="text-[15px] text-danger">
            {p}
          </p>
        ))}
      </div>
    </div>
  )
}
