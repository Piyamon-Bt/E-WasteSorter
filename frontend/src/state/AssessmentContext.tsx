import { createContext, useContext, useEffect, useMemo, useReducer, useRef, type ReactNode } from 'react'
import { api, ApiError, type RequestContext } from '../services/api'
import type { CheckAnswer, ConfirmedIdentity, DeviceType, PriceResearch, ServicesResult, UserResponse } from '../types/api'
import type { SlotPhoto } from '../types/assessment'
import { useAnnouncer } from './Announcer'
import {
  assessmentReducer,
  createInitialState,
  type Action,
  type AssessmentState,
  type LocationState,
} from './assessmentReducer'
import { selectReviews, selectSnapshot } from './selectors'

interface AssessmentActions {
  setDevice(deviceType: DeviceType): void
  setSlotPhoto(slot: string, photo: SlotPhoto): void
  addDetailPhotos(photos: SlotPhoto[]): void
  removePhoto(id: string): void
  startAnalysis(): void
  respond(observationId: string, response: UserResponse): void
  setReviewNote(observationId: string, note: string): void
  addExtraPhotos(observationId: string, photos: SlotPhoto[]): void
  removeExtraPhoto(observationId: string, photoId: string): void
  requestFollowUp(observationId: string): void
  confirmReview(): void
  answerCheck(checkId: string, answer: CheckAnswer): void
  setCheckNote(checkId: string, note: string): void
  submitChecks(): void
  setIdentity(identity: ConfirmedIdentity): void
  setLocation(location: LocationState): void
  startResearch(): void
  downloadReport(): Promise<void>
  setMockScenario(scenario: string): void
  reset(): void
}

interface AssessmentContextValue {
  state: AssessmentState
  actions: AssessmentActions
}

const Ctx = createContext<AssessmentContextValue | null>(null)

const message = (err: unknown) => (err instanceof Error ? err.message : 'Something went wrong.')

function revokeAll(s: AssessmentState) {
  s.photos.forEach((p) => URL.revokeObjectURL(p.url))
  Object.values(s.reviews).forEach((r) => r.extraPhotos.forEach((p) => URL.revokeObjectURL(p.url)))
}

export function AssessmentProvider({ children }: { children: ReactNode }) {
  const [state, rawDispatch] = useReducer(assessmentReducer, null, createInitialState)
  const { announce } = useAnnouncer()
  const stateRef = useRef(state)

  // Keep a synchronous copy so async flows read the latest state and keys.
  const dispatch = useMemo(
    () => (action: Action) => {
      stateRef.current = assessmentReducer(stateRef.current, action)
      rawDispatch(action)
    },
    [],
  )

  // Release every object URL when the app unmounts.
  useEffect(() => () => revokeAll(stateRef.current), [])

  const actions = useMemo<AssessmentActions>(() => {
    const ctx = (): RequestContext => ({
      assessmentId: stateRef.current.assessmentId,
      mockScenario: stateRef.current.mockScenario,
    })

    const a: AssessmentActions = {
      setDevice(deviceType) {
        if (stateRef.current.deviceType !== deviceType) revokeAll(stateRef.current)
        dispatch({ type: 'device/set', deviceType })
      },
      setSlotPhoto(slot, photo) {
        stateRef.current.photos.filter((p) => p.slot === slot).forEach((p) => URL.revokeObjectURL(p.url))
        dispatch({ type: 'photos/set', slot, photo })
      },
      addDetailPhotos(photos) {
        dispatch({ type: 'photos/addDetail', photos })
      },
      removePhoto(id) {
        const photo = stateRef.current.photos.find((p) => p.id === id)
        dispatch({ type: 'photos/remove', id })
        if (photo) URL.revokeObjectURL(photo.url)
      },

      startAnalysis() {
        const s = stateRef.current
        if (!s.deviceType || s.analysis.status === 'processing') return
        dispatch({ type: 'analysis/start' })
        const key = stateRef.current.analysisKey
        announce('Analysis started.')
        api
          .assessPhysical(s.deviceType, s.photos, ctx())
          .then((result) => {
            dispatch({ type: 'analysis/success', key, result })
            announce('Analysis complete. Observations are ready to review.')
          })
          .catch((err: unknown) => {
            const e = err instanceof ApiError ? err : null
            dispatch({
              type: 'analysis/failure',
              key,
              error: message(err),
              slotProblems: e?.slotProblems,
              imageIssues: e?.imageIssues,
            })
            announce(`Analysis failed. ${message(err)}`)
          })
      },

      respond(id, response) {
        dispatch({ type: 'review/respond', id, response })
      },
      setReviewNote(id, note) {
        dispatch({ type: 'review/note', id, note })
      },
      addExtraPhotos(id, photos) {
        dispatch({ type: 'review/addExtra', id, photos })
      },
      removeExtraPhoto(id, photoId) {
        const photo = stateRef.current.reviews[id]?.extraPhotos.find((p) => p.id === photoId)
        dispatch({ type: 'review/removeExtra', id, photoId })
        if (photo) URL.revokeObjectURL(photo.url)
      },
      requestFollowUp(id) {
        const s = stateRef.current
        const observation = s.analysis.data?.observations.find((o) => o.id === id)
        const review = s.reviews[id]
        if (!s.deviceType || !observation || !review?.response) return
        const originals = s.photos.filter((p) => observation.views.includes(p.slot))
        const extras = review.extraPhotos
        dispatch({ type: 'followUp/start', id })
        const key = stateRef.current.analysisKey
        api
          .followUp(s.deviceType, observation, review.response, review.note, originals, extras, ctx())
          .then((result) => {
            extras.forEach((p) => URL.revokeObjectURL(p.url))
            dispatch({ type: 'followUp/success', key, id, result })
            announce('Re-check complete.')
          })
          .catch((err: unknown) => dispatch({ type: 'followUp/failure', key, id, error: message(err) }))
      },

      confirmReview() {
        const s = stateRef.current
        if (!s.deviceType || !s.analysis.data) return
        dispatch({ type: 'plan/start' })
        const key = stateRef.current.inputKey
        api
          .checkPlan(s.deviceType, s.analysis.data.observations, selectReviews(s))
          .then((plan) => {
            dispatch({ type: 'plan/success', key, plan })
            if (plan.safety.blocked) {
              announce('Functional checks are stopped because of a suspected safety risk.')
              // Record the blocked outcome so the flow can continue without power-on tests.
              a.submitChecks()
            }
          })
          .catch((err: unknown) => dispatch({ type: 'plan/failure', key, error: message(err) }))
      },

      answerCheck(checkId, answer) {
        dispatch({ type: 'checks/answer', checkId, answer })
      },
      setCheckNote(checkId, note) {
        dispatch({ type: 'checks/note', checkId, note })
      },
      submitChecks() {
        const s = stateRef.current
        if (!s.deviceType || !s.analysis.data) return
        const responses = Object.entries(s.checkAnswers).map(([check_id, a]) => ({ check_id, ...a }))
        dispatch({ type: 'functional/start' })
        const key = stateRef.current.inputKey
        api
          .evaluateChecks(s.deviceType, s.analysis.data.observations, selectReviews(s), responses)
          .then((result) => dispatch({ type: 'functional/success', key, result }))
          .catch((err: unknown) => dispatch({ type: 'functional/failure', key, error: message(err) }))
      },

      setIdentity(identity) {
        dispatch({ type: 'identity/set', identity })
      },
      setLocation(location) {
        dispatch({ type: 'location/set', location })
      },

      startResearch() {
        const s = stateRef.current
        if (!s.deviceType || !s.analysis.data || !s.identity || !s.location) return
        if (s.research.status === 'processing') return
        dispatch({ type: 'research/start' })
        const key = stateRef.current.inputKey
        const followUps = s.followUps
        const observations = s.analysis.data.observations
          .filter((o) => followUps[o.id]?.outcome !== 'not_supported')
          .map((o) => followUps[o.id]?.revised_observation ?? o)
        const failed = (s.functional.data?.outcomes ?? []).filter((o) => o.status === 'fail').map((o) => o.check_id)
        const loc = s.location
        announce('Searching local prices and services.')

        const prices = api
          .prices(
            {
              device_type: s.deviceType,
              identity: s.identity,
              country: loc.country,
              area: loc.area || null,
              condition_summary: observations.filter((o) => o.kind !== 'unassessable').map((o) => `${o.kind}: ${o.part}`),
              damaged_parts: observations.filter((o) => o.kind === 'physical_damage').map((o) => o.part),
              failed_checks: failed,
            },
            ctx(),
          )
          .then((p: PriceResearch) => (dispatch({ type: 'research/partial', key, prices: p }), p))
        const services = api
          .services(
            {
              device_type: s.deviceType,
              country: loc.country,
              area: loc.area || null,
              latitude: loc.latitude,
              longitude: loc.longitude,
            },
            ctx(),
          )
          .then((r: ServicesResult) => (dispatch({ type: 'research/partial', key, services: r }), r))

        Promise.allSettled([prices, services])
          .then(([p, sv]) => {
            const errors = [p, sv].filter((r) => r.status === 'rejected').map((r) => message((r as PromiseRejectedResult).reason))
            const snapshot = selectSnapshot(stateRef.current)
            if (!snapshot || key !== stateRef.current.inputKey) return
            return api.recommend(snapshot).then((recommendation) => {
              // Partial results: keep the error visible next to the recommendation.
              if (errors.length) dispatch({ type: 'research/failure', key, error: errors.join(' ') })
              dispatch({ type: 'research/success', key, recommendation })
              announce('Results are ready.')
            })
          })
          .catch((err: unknown) => dispatch({ type: 'research/failure', key, error: message(err) }))
      },

      async downloadReport() {
        const s = stateRef.current
        const snapshot = selectSnapshot(s)
        if (!snapshot) return
        const text = await api.report(snapshot, s.research.recommendation)
        const url = URL.createObjectURL(new Blob([text], { type: 'text/markdown' }))
        const a = document.createElement('a')
        a.href = url
        a.download = `ewaste-assessment-${new Date().toISOString().slice(0, 10)}.md`
        a.click()
        URL.revokeObjectURL(url)
      },

      setMockScenario(scenario) {
        dispatch({ type: 'mock/scenario', scenario })
      },
      reset() {
        revokeAll(stateRef.current)
        dispatch({ type: 'reset' })
        announce('Assessment cleared.')
      },
    }
    return a
  }, [announce, dispatch])

  const value = useMemo(() => ({ state, actions }), [state, actions])
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}

// oxlint-disable-next-line react/only-export-components
export function useAssessment() {
  const ctx = useContext(Ctx)
  if (!ctx) throw new Error('useAssessment must be used within AssessmentProvider')
  return ctx
}
