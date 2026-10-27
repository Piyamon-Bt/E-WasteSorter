import { DETAIL_SLOT, deviceById } from '../content/devices'
import { effectiveObservation, hasOpenRisk, isWithdrawn } from '../lib/observations'
import type { AssessmentSnapshot, Observation, ObservationReview } from '../types/api'
import type { SectionId } from '../types/assessment'
import type { AssessmentState } from './assessmentReducer'

export const MAX_DETAIL_PHOTOS = 6

export function selectMissingSlots(s: AssessmentState) {
  if (!s.deviceType) return []
  const filled = new Set(s.photos.map((p) => p.slot))
  return deviceById[s.deviceType].views.filter((v) => !filled.has(v.id))
}

export function selectDetailPhotos(s: AssessmentState) {
  return s.photos.filter((p) => p.slot === DETAIL_SLOT)
}

/** Reviews in the backend's shape, including follow-up results. */
export function selectReviews(s: AssessmentState): ObservationReview[] {
  const observations = s.analysis.data?.observations ?? []
  return observations.map((o) => ({
    observation_id: o.id,
    response: s.reviews[o.id]?.response ?? null,
    note: s.reviews[o.id]?.note ?? '',
    follow_ups: s.followUps[o.id] ?? [],
  }))
}

export interface EffectiveObservation {
  original: Observation
  current: Observation
  openRisk: boolean
  withdrawn: boolean
}

/** Observations after their follow-up history, with any risk that is still open. */
export function selectEffectiveObservations(s: AssessmentState): EffectiveObservation[] {
  return (s.analysis.data?.observations ?? []).map((o) => {
    const history = s.followUps[o.id] ?? []
    return { original: o, current: effectiveObservation(o, history), openRisk: hasOpenRisk(o, history), withdrawn: isWithdrawn(history) }
  })
}

/** Observations the user must respond to before continuing. */
export function selectUnreviewed(s: AssessmentState) {
  return (s.analysis.data?.observations ?? []).filter((o) => o.kind !== 'unassessable' && !s.reviews[o.id]?.response)
}

export function selectSnapshot(s: AssessmentState): AssessmentSnapshot | null {
  if (!s.deviceType || !s.analysis.data || !s.identity) return null
  return {
    device_type: s.deviceType,
    physical: s.analysis.data,
    reviews: selectReviews(s),
    functional: s.functional.data,
    identity: s.identity,
    location: s.location
      ? {
          country: s.location.country,
          area: s.location.area || null,
          used_device_location: s.location.latitude !== null,
        }
      : null,
    prices: s.research.prices,
    services: s.research.services,
  }
}

/** Workflow completion — driven only by user actions, never by scrolling. */
export function selectCompleted(s: AssessmentState): Record<SectionId, boolean> {
  const analyzed = s.analysis.status === 'complete'
  const reviewed = analyzed && s.reviewConfirmed && s.plan.status === 'complete'
  const functional = reviewed && s.functional.status === 'complete'
  const identity = functional && s.identity !== null
  const location = identity && s.location !== null
  return {
    device: s.analysis.status !== 'idle',
    analyze: analyzed,
    review: reviewed,
    functionality: functional,
    identity,
    location,
    results: location && s.research.status === 'complete',
  }
}

/** Short note shown in the navigation when a section's prerequisites are missing. */
export function selectPrerequisites(s: AssessmentState): Partial<Record<SectionId, string>> {
  const done = selectCompleted(s)
  const notes: Partial<Record<SectionId, string>> = {}
  if (!s.deviceType) notes.device = 'Choose a device'
  if (s.analysis.status === 'idle') notes.analyze = 'Needs all views'
  if (!done.analyze) notes.review = 'After analysis'
  if (!done.review) notes.functionality = 'After review'
  if (!done.functionality) notes.identity = 'After checks'
  if (!done.identity) notes.location = 'After model'
  if (!done.location) notes.results = 'After location'
  return notes
}
