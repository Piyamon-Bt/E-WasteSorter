// Effective observation and risk history across follow-ups, for display.
// The backend (functional_checks.safety_state) remains the authority for safety gating;
// these helpers follow the same rules so the UI highlights the same risks.

import type { FollowUpResult, Observation } from '../types/api'

const RISK = 'suspected_safety_risk'

/** The latest revision applies; later non-revision results keep it. The original id is kept. */
export function effectiveObservation(original: Observation, history: FollowUpResult[]): Observation {
  let current = original
  for (const f of history) {
    if (f.outcome === 'revised' && f.revised_observation) current = { ...f.revised_observation, id: original.id }
  }
  return current
}

/** True when the original or any follow-up revision asserted a safety risk that has not been cleared. */
export function hasOpenRisk(original: Observation, history: FollowUpResult[]): boolean {
  let lastRisk = original.kind === RISK ? -1 : null
  history.forEach((f, i) => {
    if (f.outcome === 'revised' && f.revised_observation?.kind === RISK) lastRisk = i
  })
  if (lastRisk === null) return false
  const latest = history[history.length - 1]
  const cleared =
    !!latest && history.length - 1 > lastRisk && latest.outcome === 'not_supported' && latest.extra_images > 0
  return !cleared
}

/** Withdrawn when the latest re-check found the issue absent in new photos. */
export function isWithdrawn(history: FollowUpResult[]): boolean {
  const latest = history[history.length - 1]
  return !!latest && latest.outcome === 'not_supported' && latest.extra_images > 0
}
