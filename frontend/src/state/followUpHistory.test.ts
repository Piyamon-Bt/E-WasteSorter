import { describe, expect, it } from 'vitest'
import { effectiveObservation, hasOpenRisk } from '../lib/observations'
import type { FollowUpResult, Observation, PhysicalAssessment } from '../types/api'
import type { SlotPhoto } from '../types/assessment'
import { assessmentReducer, createInitialState, type Action, type AssessmentState } from './assessmentReducer'
import { selectEffectiveObservations, selectReviews } from './selectors'

const photo = (slot: string): SlotPhoto => ({ id: `p-${slot}`, file: {} as File, url: `blob:${slot}`, slot, width: 800, height: 600 })

const damage: Observation = {
  id: 'obs-1', kind: 'physical_damage', part: 'Back panel', description: '', views: ['back'],
  visible_evidence: '', uncertainty: 'medium', uncertainty_reason: '', risk_type: null,
}
const swelling: Observation = { ...damage, id: 'other', kind: 'suspected_safety_risk', part: 'Back panel lifting', risk_type: 'swelling' }
const cosmetic: Observation = { ...damage, id: 'other', kind: 'cosmetic_wear', part: 'Scratches' }

const physical: PhysicalAssessment = {
  source: 'simulated', model: null, device_type: 'mobile', observations: [damage], unassessable_areas: [],
  identity: { evidence_strength: 'none', candidates: [], visible_specs: [], notes: '' }, summary: '',
  view_check: 'slot_assignment_only',
}

const result = (outcome: FollowUpResult['outcome'], revised: Observation | null = null, extra = 1): FollowUpResult => ({
  observation_id: 'obs-1', outcome, revised_observation: revised, explanation: '', extra_images: extra,
  source: 'simulated', model: null,
})

function reviewed(): AssessmentState {
  let s = assessmentReducer(createInitialState(), { type: 'device/set', deviceType: 'mobile' })
  for (const v of ['front', 'back', 'left', 'right', 'top', 'bottom']) s = assessmentReducer(s, { type: 'photos/set', slot: v, photo: photo(v) })
  s = assessmentReducer(s, { type: 'analysis/start' })
  s = assessmentReducer(s, { type: 'analysis/success', key: s.analysisKey, result: physical })
  return assessmentReducer(s, { type: 'review/respond', id: 'obs-1', response: 'disagree' })
}

/** Runs one re-check: start, then the given response action built from the request's key and seq. */
function recheck(s: AssessmentState, respond: (key: number, seq: number) => Action): AssessmentState {
  s = assessmentReducer(s, { type: 'followUp/start', id: 'obs-1' })
  return assessmentReducer(s, respond(s.analysisKey, s.reviews['obs-1'].followUpSeq))
}

const success = (r: FollowUpResult) => (key: number, seq: number): Action => ({ type: 'followUp/success', key, seq, id: 'obs-1', result: r })
const openRisk = (s: AssessmentState) => selectEffectiveObservations(s)[0].openRisk

describe('follow-up history keeps safety risks', () => {
  it('damage → new risk → unresolved stays an open risk', () => {
    let s = recheck(reviewed(), success(result('revised', swelling)))
    expect(openRisk(s)).toBe(true)
    s = recheck(s, success(result('unresolved')))
    expect(selectReviews(s)[0].follow_ups.map((f) => f.outcome)).toEqual(['revised', 'unresolved'])
    expect(selectEffectiveObservations(s)[0].current.kind).toBe('suspected_safety_risk')
    expect(selectEffectiveObservations(s)[0].current.id).toBe('obs-1')
    expect(openRisk(s)).toBe(true)
  })

  it('damage → new risk → revised to cosmetic without clearance stays an open risk', () => {
    let s = recheck(reviewed(), success(result('revised', swelling)))
    s = recheck(s, success(result('revised', cosmetic, 2)))
    expect(selectEffectiveObservations(s)[0].current.kind).toBe('cosmetic_wear')
    expect(openRisk(s)).toBe(true)
  })

  it('an identified risk clears only with an explicit not_supported result on new photos', () => {
    let s = recheck(reviewed(), success(result('revised', swelling)))
    expect(openRisk(recheck(s, success(result('not_supported', null, 0))))).toBe(true)
    s = recheck(s, success(result('not_supported', null, 2)))
    expect(openRisk(s)).toBe(false)
  })

  it('a failed re-check does not erase the earlier risk', () => {
    let s = recheck(reviewed(), success(result('revised', swelling)))
    s = recheck(s, (key, seq) => ({ type: 'followUp/failure', key, seq, id: 'obs-1', error: 'timeout' }))
    expect(s.reviews['obs-1'].followUpStatus).toBe('failed')
    expect(selectReviews(s)[0].follow_ups).toHaveLength(1)
    expect(openRisk(s)).toBe(true)
  })

  it('stale or out-of-order responses cannot overwrite newer evidence', () => {
    let s = recheck(reviewed(), success(result('revised', swelling)))
    s = assessmentReducer(s, { type: 'followUp/start', id: 'obs-1' })
    const older = { key: s.analysisKey, seq: s.reviews['obs-1'].followUpSeq }
    s = assessmentReducer(s, { type: 'followUp/start', id: 'obs-1' })
    const newer = { key: s.analysisKey, seq: s.reviews['obs-1'].followUpSeq }
    s = assessmentReducer(s, success(result('unresolved'))(newer.key, newer.seq))
    // The older request answers last, claiming the risk is gone: ignored.
    s = assessmentReducer(s, success(result('not_supported', null, 3))(older.key, older.seq))
    s = assessmentReducer(s, { type: 'followUp/failure', key: older.key, seq: older.seq, id: 'obs-1', error: 'late' })
    expect(selectReviews(s)[0].follow_ups.map((f) => f.outcome)).toEqual(['revised', 'unresolved'])
    expect(s.reviews['obs-1'].followUpStatus).toBe('complete')
    expect(openRisk(s)).toBe(true)
  })

  it('responses for an earlier analysis are ignored', () => {
    let s = reviewed()
    s = assessmentReducer(s, { type: 'followUp/start', id: 'obs-1' })
    const stale = { key: s.analysisKey, seq: s.reviews['obs-1'].followUpSeq }
    s = assessmentReducer(s, { type: 'analysis/start' })
    s = assessmentReducer(s, success(result('revised', swelling))(stale.key, stale.seq))
    expect(s.followUps['obs-1']).toBeUndefined()
  })
})

describe('observation helpers', () => {
  it('keep the original id and the latest revision', () => {
    const current = effectiveObservation(damage, [result('revised', swelling), result('upheld')])
    expect(current).toMatchObject({ id: 'obs-1', kind: 'suspected_safety_risk' })
    expect(hasOpenRisk(damage, [])).toBe(false)
  })
})
