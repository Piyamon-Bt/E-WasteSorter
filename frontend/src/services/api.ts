// HTTP client for the local backend. API keys never reach the browser.

import type {
  AssessmentSnapshot,
  CheckResponse,
  ConfirmedIdentity,
  DeviceType,
  FollowUpResult,
  FunctionalEvaluation,
  FunctionalPlan,
  Health,
  ImageQualityIssue,
  Observation,
  ObservationReview,
  PhysicalAssessment,
  PriceResearch,
  RecommendationResult,
  ServicesResult,
  UserResponse,
} from '../types/api'
import type { SlotPhoto } from '../types/assessment'

export const API_BASE = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? 'http://localhost:8000'

/** A backend error with a user-readable message and optional photo problems. */
export class ApiError extends Error {
  status: number
  slotProblems: string[]
  imageIssues: ImageQualityIssue[]

  constructor(status: number, message: string, slotProblems: string[] = [], imageIssues: ImageQualityIssue[] = []) {
    super(message)
    this.status = status
    this.slotProblems = slotProblems
    this.imageIssues = imageIssues
  }
}

export interface RequestContext {
  assessmentId: string
  mockScenario: string | null
  signal?: AbortSignal
}

async function request<T>(path: string, init: RequestInit, ctx?: RequestContext): Promise<T> {
  const headers = new Headers(init.headers)
  if (ctx) {
    headers.set('X-Assessment-Id', ctx.assessmentId)
    if (ctx.mockScenario) headers.set('X-Mock-Scenario', ctx.mockScenario)
  }
  let res: Response
  try {
    res = await fetch(`${API_BASE}${path}`, { ...init, headers, signal: ctx?.signal })
  } catch (err) {
    if (err instanceof DOMException && err.name === 'AbortError') throw err
    throw new ApiError(0, 'The backend is not reachable. Check that it is running on ' + API_BASE + '.')
  }
  if (!res.ok) {
    let detail: { message?: string; slot_problems?: string[]; image_issues?: ImageQualityIssue[] } = {}
    try {
      const body = await res.json()
      detail = typeof body.detail === 'object' && body.detail ? body.detail : { message: String(body.detail ?? '') }
    } catch {
      // Non-JSON error body: fall through to the generic message.
    }
    throw new ApiError(
      res.status,
      detail.message || `Request failed (HTTP ${res.status}).`,
      detail.slot_problems ?? [],
      detail.image_issues ?? [],
    )
  }
  return path === '/api/report' ? ((await res.text()) as T) : ((await res.json()) as T)
}

const json = (body: unknown): RequestInit => ({
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(body),
})

export const api = {
  health: () => request<Health>('/api/health', { method: 'GET' }),

  assessPhysical(deviceType: DeviceType, photos: SlotPhoto[], ctx: RequestContext) {
    const form = new FormData()
    form.append('device_type', deviceType)
    for (const p of photos) {
      form.append('views', p.slot)
      form.append('files', p.file, p.file.name)
    }
    return request<PhysicalAssessment>('/api/assessments/physical', { method: 'POST', body: form }, ctx)
  },

  followUp(
    deviceType: DeviceType,
    observation: Observation,
    history: FollowUpResult[],
    response: UserResponse,
    note: string,
    originals: SlotPhoto[],
    extras: SlotPhoto[],
    ctx: RequestContext,
  ) {
    const form = new FormData()
    form.append('device_type', deviceType)
    form.append('observation', JSON.stringify(observation))
    form.append('history', JSON.stringify(history))
    form.append('response', response)
    form.append('note', note)
    for (const p of originals) {
      form.append('views', p.slot)
      form.append('files', p.file, p.file.name)
    }
    for (const p of extras) {
      form.append('views', 'followup')
      form.append('files', p.file, p.file.name)
    }
    return request<FollowUpResult>('/api/assessments/follow-up', { method: 'POST', body: form }, ctx)
  },

  checkPlan: (deviceType: DeviceType, observations: Observation[], reviews: ObservationReview[]) =>
    request<FunctionalPlan>('/api/checks/plan', json({ device_type: deviceType, observations, reviews })),

  evaluateChecks: (
    deviceType: DeviceType,
    observations: Observation[],
    reviews: ObservationReview[],
    responses: CheckResponse[],
  ) =>
    request<FunctionalEvaluation>(
      '/api/checks/evaluate',
      json({ device_type: deviceType, observations, reviews, responses }),
    ),

  prices: (
    body: {
      device_type: DeviceType
      identity: ConfirmedIdentity
      country: string
      area: string | null
      condition_summary: string[]
      damaged_parts: string[]
      failed_checks: string[]
      accessory_ruled_out: boolean
    },
    ctx: RequestContext,
  ) => request<PriceResearch>('/api/market/prices', json(body), ctx),

  services: (
    body: {
      device_type: DeviceType
      country: string
      area: string | null
      latitude: number | null
      longitude: number | null
    },
    ctx: RequestContext,
  ) => request<ServicesResult>('/api/services/nearby', json(body), ctx),

  recommend: (snapshot: AssessmentSnapshot) => request<RecommendationResult>('/api/recommendations', json(snapshot)),

  report: (snapshot: AssessmentSnapshot, recommendation: RecommendationResult | null) =>
    request<string>('/api/report', json({ snapshot, recommendation })),
}
