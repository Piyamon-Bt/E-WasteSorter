// Response and request shapes of the local backend (backend/app/schemas).
// Keep in sync with the Pydantic models.

export type DeviceType = 'laptop' | 'mobile'
export type ResultSource = 'simulated' | 'live'

export interface ProviderIssue {
  step: string
  code: 'timeout' | 'quota' | 'auth' | 'invalid_response' | 'budget_limit' | 'not_configured' | 'provider_error'
  message: string
}

export interface Money {
  min: number
  max: number
  currency: string
}

// ---- Health ----

export interface Health {
  status: string
  mode: 'mock' | 'live'
  openai: { key_configured: boolean; model: string; connection_verified: boolean }
  google_places: { key_configured: boolean; connection_verified: boolean }
  mock_scenarios: Record<string, string>
  limits: { max_upload_mb: number; max_images_per_request: number; min_image_side_px: number }
  notes: string[]
}

// ---- Physical assessment ----

export type ObservationKind = 'cosmetic_wear' | 'physical_damage' | 'suspected_safety_risk' | 'unassessable'
export type UserResponse = 'agree' | 'disagree' | 'unsure'

export interface Observation {
  id: string
  kind: ObservationKind
  part: string
  description: string
  views: string[]
  visible_evidence: string
  uncertainty: 'low' | 'medium' | 'high'
  uncertainty_reason: string
  risk_type: string | null
}

export interface IdentityCandidate {
  brand: string | null
  model: string | null
  evidence: string
}

export interface IdentitySuggestion {
  evidence_strength: 'none' | 'weak' | 'moderate' | 'strong'
  candidates: IdentityCandidate[]
  visible_specs: string[]
  notes: string
}

export interface PhysicalAssessment {
  source: ResultSource
  model: string | null
  device_type: DeviceType
  observations: Observation[]
  unassessable_areas: string[]
  identity: IdentitySuggestion
  summary: string
  view_check: 'slot_assignment_only'
}

export interface ImageQualityIssue {
  view: string
  filename: string
  problem: string
  blocking: boolean
}

export interface FollowUpResult {
  observation_id: string
  outcome: 'upheld' | 'revised' | 'not_supported' | 'unresolved'
  revised_observation: Observation | null
  explanation: string
  extra_images: number
  source: ResultSource
  model: string | null
}

export interface ObservationReview {
  observation_id: string
  response: UserResponse | null
  note: string
  /** Every follow-up result for this observation, oldest first. */
  follow_ups: FollowUpResult[]
}

// ---- Functional checks ----

export type CheckAnswer = 'pass' | 'fail' | 'unsure' | 'unable'
export type CheckStatus = CheckAnswer | 'not_answered' | 'unavailable_power_failed' | 'blocked_by_safety'

export interface RiskStatus {
  observation_id: string
  part: string
  status: 'confirmed_by_user' | 'unresolved' | 'identified_in_follow_up' | 'cleared_after_follow_up'
  explanation: string
}

export interface SafetyState {
  blocked: boolean
  risks: RiskStatus[]
  guidance: string[]
}

export interface CheckDefinition {
  id: string
  label: string
  instructions: string
  depends_on_power: boolean
}

export interface FunctionalPlan {
  device_type: DeviceType
  safety: SafetyState
  checks: CheckDefinition[]
  guidance: string[]
}

/** Charging check only: whether the test used a charger and cable known to work. */
export type AccessoryCheck = 'known_working' | 'unverified'

export interface CheckResponse {
  check_id: string
  answer: CheckAnswer | null
  note: string
  accessory_check?: AccessoryCheck | null
}

export interface CheckOutcome {
  check_id: string
  label: string
  status: CheckStatus
  note: string
  accessory_check: AccessoryCheck | null
}

export interface FunctionalEvaluation {
  outcomes: CheckOutcome[]
  clarifications: string[]
  conditional_findings: string[]
  complete: boolean
  blocked_by_safety: boolean
  disclaimer: string
}

// ---- Identity, prices, services ----

export interface ConfirmedIdentity {
  status: 'confirmed' | 'candidate_selected' | 'unknown'
  brand: string | null
  model: string | null
  variant: string | null
  storage: string | null
  ram: string | null
  evidence_verified: boolean
}

export type PriceType =
  | 'asking_price'
  | 'completed_sale'
  | 'buyback_offer'
  | 'part_price'
  | 'repair_labor'
  | 'repair_quote'

export interface PriceRecord {
  price_type: PriceType
  item: string
  amount_min: number
  amount_max: number
  currency: string
  market: string
  device_state: string
  part_quality: string
  scenario_id: string | null
  source_url: string
  source_title: string
  retrieved_at: string
  match_level: 'exact' | 'close' | 'indicative'
  matching_conditions: string
  limitations: string
  simulated: boolean
}

/** One repair intervention; `needs` lists every finding it might address (priced once). */
export interface RepairScenario {
  id: string
  needs: string[]
  title: string
  description: string
}

export interface PriceResearch {
  source: ResultSource
  model: string | null
  country: string
  identity_label: string
  status: 'complete' | 'partial' | 'insufficient_data' | 'skipped_unknown_identity' | 'failed'
  retrieved_at: string
  records: PriceRecord[]
  channels: { price_type: PriceType; status: 'found' | 'insufficient_data' | 'not_searched'; note: string }[]
  repair_scenarios: RepairScenario[]
  issues: ProviderIssue[]
  dropped_records: number
  notes: string[]
}

export interface LocalService {
  name: string
  category: 'repair' | 'buyback' | 'recycling'
  address: string | null
  phone: string | null
  website: string | null
  maps_url: string | null
  place_id: string | null
  business_status: string | null
  distance_km: number | null
  distance_kind: 'straight_line' | null
  relevance: string
  simulated: boolean
}

export interface ServicesResult {
  source: ResultSource
  country: string
  area_label: string
  retrieved_at: string
  services: LocalService[]
  issues: ProviderIssue[]
  attribution: string
  notes: string[]
}

export interface LocationChoice {
  country: string
  area: string | null
  used_device_location: boolean
}

// ---- Recommendations ----

export type Action = 'reuse' | 'resell_as_is' | 'repair_then_reuse' | 'repair_then_resell' | 'recycle'

/** One sale channel for one device condition. Channels are never pooled. */
export interface SaleChannelEstimate {
  price_type: PriceType
  device_state: string
  range: Money
  records: number
  used_for_calculation: boolean
}

export interface ActionOption {
  action: Action
  title: string
  summary: string
  prerequisites: string[]
  tradeoffs: string[]
  uncertainty: string[]
  sale_channels: SaleChannelEstimate[]
  sale_basis: PriceType | null
  gross_sale: Money | null
  repair_cost: Money | null
  repair_cost_complete: boolean
  net_proceeds: Money | null
  avoided_cost: Money | null
  financial_status: 'complete' | 'conditional' | 'insufficient'
  financial_note: string
}

export interface Ranking {
  basis: 'financial_value' | 'resource_use'
  order: Action[]
  conditional: Action[]
  unranked: Action[]
  explanation: string[]
  complete: boolean
}

export interface RecommendationResult {
  options: ActionOption[]
  financial_ranking: Ranking
  resource_ranking: Ranking
  safety_constrained: boolean
  conditional_findings: string[]
  rankings_differ: string | null
  disclaimers: string[]
  disposal_guidance: string[]
}

export interface AssessmentSnapshot {
  device_type: DeviceType
  physical: PhysicalAssessment
  reviews: ObservationReview[]
  functional: FunctionalEvaluation | null
  identity: ConfirmedIdentity
  location: LocationChoice | null
  prices: PriceResearch | null
  services: ServicesResult | null
}
