// Functional English labels shared across components.

import type { Action, CheckAnswer, CheckStatus, ObservationKind, PriceType, UserResponse } from '../types/api'

export const kindLabels: Record<ObservationKind, string> = {
  suspected_safety_risk: 'Suspected safety risk',
  physical_damage: 'Physical damage',
  cosmetic_wear: 'Cosmetic wear',
  unassessable: 'Not assessable',
}

export const kindOrder: ObservationKind[] = ['suspected_safety_risk', 'physical_damage', 'cosmetic_wear', 'unassessable']

export const responseLabels: Record<UserResponse, string> = {
  agree: 'Agree',
  disagree: 'Disagree',
  unsure: 'Unsure',
}

export const answerLabels: Record<CheckAnswer, string> = {
  pass: 'Pass',
  fail: 'Fail',
  unsure: 'Unsure',
  unable: 'Unable to test',
}

export const checkStatusLabels: Record<CheckStatus, string> = {
  ...answerLabels,
  not_answered: 'Not answered',
  unavailable_power_failed: 'Unavailable (did not power on)',
  blocked_by_safety: 'Stopped for safety',
}

export const priceTypeLabels: Record<PriceType, string> = {
  asking_price: 'Asking price (active listing)',
  completed_sale: 'Completed sale',
  buyback_offer: 'Buyback offer',
  part_price: 'Part price',
  repair_labor: 'Repair labor',
  repair_quote: 'Repair quote (part + labor)',
}

export const actionLabels: Record<Action, string> = {
  reuse: 'Keep using it (reuse)',
  resell_as_is: 'Resell as-is',
  repair_then_reuse: 'Repair, then keep using',
  repair_then_resell: 'Repair, then resell',
  recycle: 'Recycle',
}

export const serviceCategoryLabels = {
  repair: 'Repair',
  buyback: 'Buyback',
  recycling: 'Recycling',
} as const

/** Countries offered in the picker. Any ISO 3166-1 alpha-2 code can also be typed. */
export const countries: { code: string; name: string }[] = [
  { code: 'TH', name: 'Thailand' },
  { code: 'MY', name: 'Malaysia' },
  { code: 'SG', name: 'Singapore' },
  { code: 'VN', name: 'Vietnam' },
  { code: 'ID', name: 'Indonesia' },
  { code: 'PH', name: 'Philippines' },
  { code: 'JP', name: 'Japan' },
  { code: 'KR', name: 'South Korea' },
  { code: 'IN', name: 'India' },
  { code: 'AU', name: 'Australia' },
  { code: 'GB', name: 'United Kingdom' },
  { code: 'DE', name: 'Germany' },
  { code: 'US', name: 'United States' },
  { code: 'CA', name: 'Canada' },
]

export function formatMoney(m: { min: number; max: number; currency: string } | null): string {
  if (!m) return 'Insufficient data'
  const f = (n: number) => n.toLocaleString('en-US', { maximumFractionDigits: 0 })
  return m.min === m.max ? `${m.currency} ${f(m.min)}` : `${m.currency} ${f(m.min)} – ${f(m.max)}`
}

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleString('en-GB', { dateStyle: 'medium', timeStyle: 'short' })
}
