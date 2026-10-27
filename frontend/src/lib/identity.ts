import type { ConfirmedIdentity, IdentitySuggestion } from '../types/api'

export const NONE = 'none'

export interface Fields {
  brand: string
  model: string
  variant: string
  storage: string
  ram: string
}

export const emptyFields: Fields = { brand: '', model: '', variant: '', storage: '', ram: '' }
const clean = (v: string) => v.trim() || null
const same = (a: string | null, b: string) => (a ?? '').trim().toLowerCase() === b.trim().toLowerCase()

/**
 * Evidence-verified only when the photos gave strong evidence and the user kept that candidate's
 * brand and model unchanged. Everything else is user-confirmed, not verified.
 */
export function buildIdentity(suggestion: IdentitySuggestion, picked: string, f: Fields): ConfirmedIdentity {
  const candidate = picked === NONE ? null : suggestion.candidates[Number(picked)]
  const matchesCandidate = !!candidate && same(candidate.brand, f.brand) && same(candidate.model, f.model)
  return {
    status: matchesCandidate ? 'candidate_selected' : 'confirmed',
    brand: clean(f.brand),
    model: clean(f.model),
    variant: clean(f.variant),
    storage: clean(f.storage),
    ram: clean(f.ram),
    evidence_verified: matchesCandidate && suggestion.evidence_strength === 'strong',
  }
}
