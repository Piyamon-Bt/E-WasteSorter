import type {
  AccessoryCheck,
  CheckAnswer,
  ConfirmedIdentity,
  DeviceType,
  FollowUpResult,
  FunctionalEvaluation,
  FunctionalPlan,
  ImageQualityIssue,
  PhysicalAssessment,
  PriceResearch,
  RecommendationResult,
  ServicesResult,
  UserResponse,
} from '../types/api'
import type { AsyncStatus, ReviewDraft, SlotPhoto } from '../types/assessment'

export interface Remote<T> {
  status: AsyncStatus
  data: T | null
  error: string | null
}

export interface LocationState {
  country: string
  area: string
  latitude: number | null
  longitude: number | null
}

export interface CheckAnswerDraft {
  answer: CheckAnswer | null
  note: string
  accessory_check?: AccessoryCheck | null
}

export interface ResearchState {
  status: AsyncStatus
  prices: PriceResearch | null
  services: ServicesResult | null
  recommendation: RecommendationResult | null
  error: string | null
}

export interface AssessmentState {
  /** Random id sent to the backend for per-assessment limits. Regenerated on reset. */
  assessmentId: string
  deviceType: DeviceType | null
  photos: SlotPhoto[]
  photoProblems: { slotProblems: string[]; imageIssues: ImageQualityIssue[] }
  analysis: Remote<PhysicalAssessment>
  reviews: Record<string, ReviewDraft>
  /** Follow-up history per observation, oldest first. Never shortened by a later result. */
  followUps: Record<string, FollowUpResult[]>
  reviewConfirmed: boolean
  plan: Remote<FunctionalPlan>
  checkAnswers: Record<string, CheckAnswerDraft>
  functional: Remote<FunctionalEvaluation>
  identity: ConfirmedIdentity | null
  location: LocationState | null
  research: ResearchState
  /** Bumped when photos or device change: older analysis/follow-up responses are ignored. */
  analysisKey: number
  /** Bumped when any later input changes: older plan/check/research responses are ignored. */
  inputKey: number
  mockScenario: string | null
}

const idle = <T>(): Remote<T> => ({ status: 'idle', data: null, error: null })
const idleResearch: ResearchState = { status: 'idle', prices: null, services: null, recommendation: null, error: null }

/** Pre-selected so the photo slots and the 3D model are never empty. */
export const DEFAULT_DEVICE: DeviceType = 'laptop'

export function newAssessmentId() {
  return crypto.randomUUID()
}

export function createInitialState(mockScenario: string | null = null): AssessmentState {
  return {
    assessmentId: newAssessmentId(),
    deviceType: DEFAULT_DEVICE,
    photos: [],
    photoProblems: { slotProblems: [], imageIssues: [] },
    analysis: idle(),
    reviews: {},
    followUps: {},
    reviewConfirmed: false,
    plan: idle(),
    checkAnswers: {},
    functional: idle(),
    identity: null,
    location: null,
    research: idleResearch,
    analysisKey: 0,
    inputKey: 0,
    mockScenario,
  }
}

export const emptyReview: ReviewDraft = {
  response: null,
  note: '',
  extraPhotos: [],
  followUpStatus: 'idle',
  followUpError: null,
  followUpSeq: 0,
}

export type Action =
  | { type: 'device/set'; deviceType: DeviceType }
  | { type: 'photos/set'; slot: string; photo: SlotPhoto }
  | { type: 'photos/addDetail'; photos: SlotPhoto[] }
  | { type: 'photos/remove'; id: string }
  | { type: 'analysis/start' }
  | { type: 'analysis/success'; key: number; result: PhysicalAssessment }
  | { type: 'analysis/failure'; key: number; error: string; slotProblems?: string[]; imageIssues?: ImageQualityIssue[] }
  | { type: 'review/respond'; id: string; response: UserResponse }
  | { type: 'review/note'; id: string; note: string }
  | { type: 'review/addExtra'; id: string; photos: SlotPhoto[] }
  | { type: 'review/removeExtra'; id: string; photoId: string }
  | { type: 'followUp/start'; id: string }
  | { type: 'followUp/success'; key: number; id: string; seq: number; result: FollowUpResult }
  | { type: 'followUp/failure'; key: number; id: string; seq: number; error: string }
  | { type: 'plan/start' }
  | { type: 'plan/success'; key: number; plan: FunctionalPlan }
  | { type: 'plan/failure'; key: number; error: string }
  | { type: 'checks/answer'; checkId: string; answer: CheckAnswer }
  | { type: 'checks/note'; checkId: string; note: string }
  | { type: 'checks/accessory'; checkId: string; accessory: AccessoryCheck }
  | { type: 'functional/start' }
  | { type: 'functional/success'; key: number; result: FunctionalEvaluation }
  | { type: 'functional/failure'; key: number; error: string }
  | { type: 'identity/set'; identity: ConfirmedIdentity }
  | { type: 'location/set'; location: LocationState }
  | { type: 'research/start' }
  | { type: 'research/partial'; key: number; prices?: PriceResearch; services?: ServicesResult }
  | { type: 'research/success'; key: number; recommendation: RecommendationResult }
  | { type: 'research/failure'; key: number; error: string }
  | { type: 'mock/scenario'; scenario: string }
  | { type: 'reset' }

type Stage = 'analysis' | 'review' | 'functional' | 'research'

/** Clears everything that depends on a changed input, from `stage` onward. */
function invalidate(state: AssessmentState, stage: Stage): AssessmentState {
  const next = { ...state, inputKey: state.inputKey + 1, research: idleResearch }
  if (stage === 'research') return next
  next.functional = idle()
  if (stage === 'functional') return next
  next.plan = idle()
  next.reviewConfirmed = false
  if (stage === 'review') return next
  return {
    ...next,
    analysisKey: state.analysisKey + 1,
    analysis: idle(),
    reviews: {},
    followUps: {},
    checkAnswers: {},
    identity: null,
  }
}

function updateReview(state: AssessmentState, id: string, patch: Partial<ReviewDraft>): AssessmentState {
  const current = state.reviews[id] ?? emptyReview
  return { ...state, reviews: { ...state.reviews, [id]: { ...current, ...patch } } }
}

export function assessmentReducer(state: AssessmentState, action: Action): AssessmentState {
  switch (action.type) {
    case 'device/set':
      if (state.deviceType === action.deviceType) return state
      // Views differ per device, so photos are cleared too (the provider revokes their URLs).
      return { ...invalidate(state, 'analysis'), deviceType: action.deviceType, photos: [], location: state.location }

    case 'photos/set': {
      const others = state.photos.filter((p) => p.slot !== action.slot)
      return { ...invalidate(state, 'analysis'), photos: [...others, action.photo], photoProblems: clearSlot(state, action.slot) }
    }
    case 'photos/addDetail':
      return { ...invalidate(state, 'analysis'), photos: [...state.photos, ...action.photos] }
    case 'photos/remove': {
      const removed = state.photos.find((p) => p.id === action.id)
      return {
        ...invalidate(state, 'analysis'),
        photos: state.photos.filter((p) => p.id !== action.id),
        photoProblems: removed ? clearSlot(state, removed.slot) : state.photoProblems,
      }
    }

    case 'analysis/start':
      return { ...invalidate(state, 'analysis'), analysis: { status: 'processing', data: null, error: null } }
    case 'analysis/success':
      if (action.key !== state.analysisKey) return state
      return {
        ...state,
        analysis: { status: 'complete', data: action.result, error: null },
        photoProblems: { slotProblems: [], imageIssues: [] },
      }
    case 'analysis/failure':
      if (action.key !== state.analysisKey) return state
      return {
        ...state,
        analysis: { status: 'failed', data: null, error: action.error },
        photoProblems: { slotProblems: action.slotProblems ?? [], imageIssues: action.imageIssues ?? [] },
      }

    case 'review/respond':
      return updateReview(invalidate(state, 'review'), action.id, { response: action.response })
    case 'review/note':
      return updateReview(invalidate(state, 'review'), action.id, { note: action.note })
    case 'review/addExtra': {
      const current = state.reviews[action.id] ?? emptyReview
      return updateReview(state, action.id, { extraPhotos: [...current.extraPhotos, ...action.photos] })
    }
    case 'review/removeExtra': {
      const current = state.reviews[action.id] ?? emptyReview
      return updateReview(state, action.id, { extraPhotos: current.extraPhotos.filter((p) => p.id !== action.photoId) })
    }
    case 'followUp/start': {
      const seq = (state.reviews[action.id] ?? emptyReview).followUpSeq + 1
      return updateReview(invalidate(state, 'review'), action.id, { followUpStatus: 'processing', followUpError: null, followUpSeq: seq })
    }
    case 'followUp/success': {
      // Stale or out-of-order responses never overwrite newer evidence.
      if (action.key !== state.analysisKey || action.seq !== state.reviews[action.id]?.followUpSeq) return state
      const next = updateReview(invalidate(state, 'review'), action.id, { followUpStatus: 'complete', extraPhotos: [] })
      const history = [...(state.followUps[action.id] ?? []), action.result]
      return { ...next, followUps: { ...next.followUps, [action.id]: history } }
    }
    case 'followUp/failure':
      // A failed re-check keeps the whole history, including any earlier risk.
      if (action.key !== state.analysisKey || action.seq !== state.reviews[action.id]?.followUpSeq) return state
      return updateReview(state, action.id, { followUpStatus: 'failed', followUpError: action.error })

    case 'plan/start':
      return { ...state, plan: { status: 'processing', data: null, error: null } }
    case 'plan/success':
      if (action.key !== state.inputKey) return state
      return { ...state, reviewConfirmed: true, plan: { status: 'complete', data: action.plan, error: null } }
    case 'plan/failure':
      if (action.key !== state.inputKey) return state
      return { ...state, plan: { status: 'failed', data: null, error: action.error } }

    case 'checks/answer': {
      const current = state.checkAnswers[action.checkId] ?? { answer: null, note: '' }
      return {
        ...invalidate(state, 'functional'),
        checkAnswers: { ...state.checkAnswers, [action.checkId]: { ...current, answer: action.answer } },
      }
    }
    case 'checks/note': {
      const current = state.checkAnswers[action.checkId] ?? { answer: null, note: '' }
      return {
        ...invalidate(state, 'functional'),
        checkAnswers: { ...state.checkAnswers, [action.checkId]: { ...current, note: action.note } },
      }
    }
    case 'checks/accessory': {
      const current = state.checkAnswers[action.checkId] ?? { answer: null, note: '' }
      return {
        ...invalidate(state, 'functional'),
        checkAnswers: { ...state.checkAnswers, [action.checkId]: { ...current, accessory_check: action.accessory } },
      }
    }
    case 'functional/start':
      return { ...state, functional: { status: 'processing', data: null, error: null } }
    case 'functional/success':
      if (action.key !== state.inputKey) return state
      return { ...state, functional: { status: 'complete', data: action.result, error: null } }
    case 'functional/failure':
      if (action.key !== state.inputKey) return state
      return { ...state, functional: { status: 'failed', data: null, error: action.error } }

    case 'identity/set':
      return { ...invalidate(state, 'research'), identity: action.identity }
    case 'location/set':
      return { ...invalidate(state, 'research'), location: action.location }

    case 'research/start':
      return { ...state, research: { ...idleResearch, status: 'processing' } }
    case 'research/partial':
      if (action.key !== state.inputKey) return state
      return {
        ...state,
        research: {
          ...state.research,
          prices: action.prices ?? state.research.prices,
          services: action.services ?? state.research.services,
        },
      }
    case 'research/success':
      if (action.key !== state.inputKey) return state
      return { ...state, research: { ...state.research, status: 'complete', recommendation: action.recommendation } }
    case 'research/failure':
      if (action.key !== state.inputKey) return state
      return { ...state, research: { ...state.research, status: 'failed', error: action.error } }

    case 'mock/scenario':
      return { ...state, mockScenario: action.scenario }
    case 'reset':
      return createInitialState(state.mockScenario)
  }
}

function clearSlot(state: AssessmentState, slot: string) {
  return {
    slotProblems: state.photoProblems.slotProblems,
    imageIssues: state.photoProblems.imageIssues.filter((i) => i.view !== slot),
  }
}
