import { describe, expect, it } from 'vitest'
import { buildIdentity, emptyFields } from '../lib/identity'
import type { FunctionalPlan, IdentitySuggestion, PhysicalAssessment } from '../types/api'
import type { SlotPhoto } from '../types/assessment'
import { assessmentReducer, createInitialState, type AssessmentState } from './assessmentReducer'
import { selectCompleted, selectMissingSlots, selectReviews, selectSnapshot, selectUnreviewed } from './selectors'

const photo = (slot: string): SlotPhoto => ({ id: `p-${slot}`, file: {} as File, url: `blob:${slot}`, slot, width: 800, height: 600 })

const physical: PhysicalAssessment = {
  source: 'simulated',
  model: 'mock-fixture',
  device_type: 'mobile',
  observations: [
    { id: 'obs-1', kind: 'physical_damage', part: 'Front glass', description: '', views: ['front'], visible_evidence: '', uncertainty: 'medium', uncertainty_reason: '', risk_type: null },
    { id: 'obs-2', kind: 'unassessable', part: 'Internals', description: '', views: [], visible_evidence: '', uncertainty: 'high', uncertainty_reason: '', risk_type: null },
  ],
  unassessable_areas: [],
  identity: { evidence_strength: 'strong', candidates: [{ brand: 'Acme', model: 'P1', evidence: 'logo' }], visible_specs: [], notes: '' },
  summary: '',
  view_check: 'slot_assignment_only',
}

const plan: FunctionalPlan = { device_type: 'mobile', safety: { blocked: false, risks: [], guidance: [] }, checks: [], guidance: [] }

function analyzed(): AssessmentState {
  let s = createInitialState()
  s = assessmentReducer(s, { type: 'device/set', deviceType: 'mobile' })
  for (const v of ['front', 'back', 'left', 'right', 'top', 'bottom']) s = assessmentReducer(s, { type: 'photos/set', slot: v, photo: photo(v) })
  s = assessmentReducer(s, { type: 'analysis/start' })
  return assessmentReducer(s, { type: 'analysis/success', key: s.analysisKey, result: physical })
}

describe('assessment reducer', () => {
  it('reports missing required views per device', () => {
    let s = assessmentReducer(createInitialState(), { type: 'device/set', deviceType: 'laptop' })
    expect(selectMissingSlots(s)).toHaveLength(6)
    s = assessmentReducer(s, { type: 'photos/set', slot: 'screen', photo: photo('screen') })
    expect(selectMissingSlots(s).map((v) => v.id)).not.toContain('screen')
  })

  it('replacing a slot photo keeps one photo per slot and clears the analysis', () => {
    let s = analyzed()
    s = assessmentReducer(s, { type: 'photos/set', slot: 'front', photo: { ...photo('front'), id: 'new' } })
    expect(s.photos.filter((p) => p.slot === 'front')).toHaveLength(1)
    expect(s.analysis.status).toBe('idle')
  })

  it('ignores a stale analysis response after the photos changed', () => {
    let s = createInitialState()
    s = assessmentReducer(s, { type: 'device/set', deviceType: 'mobile' })
    s = assessmentReducer(s, { type: 'analysis/start' })
    const staleKey = s.analysisKey
    s = assessmentReducer(s, { type: 'photos/set', slot: 'front', photo: photo('front') })
    s = assessmentReducer(s, { type: 'analysis/success', key: staleKey, result: physical })
    expect(s.analysis.data).toBeNull()
  })

  it('requires responses to every assessable observation', () => {
    let s = analyzed()
    expect(selectUnreviewed(s).map((o) => o.id)).toEqual(['obs-1'])
    s = assessmentReducer(s, { type: 'review/respond', id: 'obs-1', response: 'disagree' })
    expect(selectUnreviewed(s)).toHaveLength(0)
    expect(selectReviews(s)[0]).toMatchObject({ observation_id: 'obs-1', response: 'disagree', follow_ups: [] })
  })

  it('changing a review invalidates later steps', () => {
    let s = analyzed()
    s = assessmentReducer(s, { type: 'review/respond', id: 'obs-1', response: 'agree' })
    s = assessmentReducer(s, { type: 'plan/start' })
    s = assessmentReducer(s, { type: 'plan/success', key: s.inputKey, plan })
    expect(selectCompleted(s).review).toBe(true)
    s = assessmentReducer(s, { type: 'review/respond', id: 'obs-1', response: 'unsure' })
    expect(selectCompleted(s).review).toBe(false)
    expect(s.plan.status).toBe('idle')
  })

  it('reset clears the assessment and issues a new assessment id', () => {
    const s = analyzed()
    const next = assessmentReducer(s, { type: 'reset' })
    expect(next.photos).toHaveLength(0)
    expect(next.analysis.data).toBeNull()
    expect(next.assessmentId).not.toBe(s.assessmentId)
  })

  it('snapshot needs an identity before research', () => {
    let s = analyzed()
    expect(selectSnapshot(s)).toBeNull()
    s = assessmentReducer(s, { type: 'identity/set', identity: buildIdentity(physical.identity, 'none', emptyFields) })
    expect(selectSnapshot(s)?.device_type).toBe('mobile')
  })
})

describe('identity confirmation', () => {
  const strong: IdentitySuggestion = physical.identity

  it('a kept strong candidate is evidence-verified', () => {
    const id = buildIdentity(strong, '0', { ...emptyFields, brand: 'Acme', model: 'P1' })
    expect(id).toMatchObject({ status: 'candidate_selected', evidence_verified: true })
  })

  it('a corrected model is user-confirmed, not verified', () => {
    const id = buildIdentity(strong, '0', { ...emptyFields, brand: 'Acme', model: 'P2' })
    expect(id).toMatchObject({ status: 'confirmed', evidence_verified: false })
  })

  it('weak evidence never verifies a candidate', () => {
    const id = buildIdentity({ ...strong, evidence_strength: 'weak' }, '0', { ...emptyFields, brand: 'Acme', model: 'P1' })
    expect(id.evidence_verified).toBe(false)
  })
})

describe('defaults', () => {
  it('starts with Laptop selected so photo slots show immediately', () => {
    const s = createInitialState()
    expect(s.deviceType).toBe('laptop')
    expect(selectMissingSlots(s)).toHaveLength(6)
  })
})
