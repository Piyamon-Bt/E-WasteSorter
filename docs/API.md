# Backend API

Base URL `http://localhost:8000`. Interactive docs: http://localhost:8000/docs (FastAPI/OpenAPI).

Calls that may use a paid provider need the header `X-Assessment-Id` (8–64 chars, random per assessment; the frontend uses a UUID). In mock mode, `X-Mock-Scenario` selects a fixture: `normal`, `visible_damage` (default), `suspected_risk`, `unknown_model`, `missing_market_data`, `provider_failure`. Live mode ignores it.

Error bodies look like `{"detail": {"message": "...", "issue": {"step", "code", "message"}}}`. Codes: `timeout`, `quota`, `auth`, `invalid_response`, `budget_limit`, `not_configured`, `provider_error`.

## GET /api/health

Mode and readiness without secrets.

```bash
curl -s http://localhost:8000/api/health
```

```json
{"status":"ok","mode":"mock","openai":{"key_configured":false,"model":"gpt-6.1-terra","connection_verified":false},
 "google_places":{"key_configured":false,"connection_verified":false},"mock_scenarios":{"normal":"..."}, "limits":{...}}
```

## GET /api/usage

Project budget summary from the ledger (estimates).

## POST /api/assessments/physical

`multipart/form-data`: `device_type` (`laptop`|`mobile`), repeated `views` + `files` pairs in the same order. Required views:

- mobile: `front back left right top bottom`
- laptop: `screen keyboard lid underside left right`
- optional extra photos: `detail` (repeatable)

```bash
curl -s -X POST http://localhost:8000/api/assessments/physical \
  -H "X-Assessment-Id: demo-assessment-0001" -H "X-Mock-Scenario: visible_damage" \
  -F device_type=mobile \
  -F views=front -F files=@front.jpg -F views=back -F files=@back.jpg \
  -F views=left -F files=@left.jpg -F views=right -F files=@right.jpg \
  -F views=top -F files=@top.jpg -F views=bottom -F files=@bottom.jpg
```

200 → `PhysicalAssessment`: `source` (`simulated`|`live`), `observations[]` (`id`, `kind` = `cosmetic_wear`|`physical_damage`|`suspected_safety_risk`|`unassessable`, `part`, `description`, `views`, `visible_evidence`, `uncertainty`, `uncertainty_reason`, `risk_type`), `unassessable_areas`, `identity` (`evidence_strength`, `candidates`, `visible_specs`, `notes`), `summary`, `view_check: "slot_assignment_only"`.

422 → photos need attention: `slot_problems[]` (missing/duplicate/unknown slots) and `image_issues[]` (`view`, `filename`, `problem`, `blocking`).

## POST /api/assessments/follow-up

`multipart/form-data`: `device_type`, `observation` (JSON of the **current effective** observation, original id kept), `history` (JSON list of earlier `FollowUpResult`s for this observation, oldest first; default `[]`), `response` (`agree`|`disagree`|`unsure`), `note`, and `views`/`files`. Original supporting photos use their slot id; new photos use `followup`. The total number of photos (original + new) is limited by `MAX_IMAGES_PER_REQUEST`, and each file by `MAX_UPLOAD_MB`. Both limits are checked before images are processed or a provider is called; over-limit requests return 422. Returns `FollowUpResult` (`outcome` = `upheld`|`revised`|`not_supported`|`unresolved`, `revised_observation`, `explanation`, `extra_images`).

## POST /api/checks/plan

```json
{"device_type":"mobile","observations":[...],"reviews":[{"observation_id":"obs-2","response":"disagree","note":"","follow_ups":[]}]}
```

Returns `safety` (`blocked`, `risks[]` with `confirmed_by_user`|`unresolved`|`cleared_after_follow_up`, `guidance`), `checks[]` (empty when blocked) and `guidance`.

## POST /api/checks/evaluate

The same body plus `responses: [{"check_id":"power_on","answer":"pass|fail|unsure|unable|null","note":"","accessory_check":null}]`. `accessory_check` applies to `charging` only: `known_working` or `unverified`. Returns `outcomes[]` (`status` adds `not_answered`, `unavailable_power_failed`, `blocked_by_safety`), `clarifications`, `conditional_findings`, `complete`, `disclaimer`.

## POST /api/market/prices

```json
{"device_type":"mobile","identity":{"status":"confirmed","brand":"Brand","model":"Model","variant":null,"storage":"128 GB","ram":null,"evidence_verified":false},
 "country":"TH","area":"Bangkok","condition_summary":["physical_damage: Front glass"],"damaged_parts":["Front glass"],"failed_checks":["charging"],"accessory_ruled_out":false}
```

Returns `PriceResearch`:
- `status`: `complete`, `insufficient_data`, `skipped_unknown_identity` or `failed`.
- `records[]`: each has `price_type`, `item`, `amount_min`/`amount_max`, `currency`, `market`, `device_state`, `part_quality`, `scenario_id`, `source_url`, `source_title`, `retrieved_at`, `match_level`, `matching_conditions`, `limitations` and `simulated`.
- `channels[]`, `repair_scenarios[]` (each `id`, `needs[]` (every finding the intervention might address; priced once), `title`, `description`), `issues[]`, `dropped_records` and `notes`.

## POST /api/services/nearby

```json
{"device_type":"laptop","country":"TH","area":"Chiang Mai","latitude":null,"longitude":null,"needs":["repair","buyback","recycling"]}
```

Returns `ServicesResult`:
- `services[]`: each has `name`, `category`, `address`, `phone`, `website`, `maps_url`, `place_id`, `business_status`, `distance_km`, `distance_kind` (`straight_line` or null), `relevance` and `simulated`.
- Also `issues`, `attribution`, `notes` and `retrieved_at`.

## POST /api/recommendations

Body: `AssessmentSnapshot`, which has `device_type`, `physical`, `reviews`, `functional`, `identity`, `location`, `prices` and `services`. Returns:
- `options[]`: each has:
  - `sale_channels[]` — one entry per channel and device condition (`price_type`, `device_state`, `range`, `records`, `used_for_calculation`); channels are never pooled.
  - `sale_basis` — the channel used for `gross_sale`.
  - `gross_sale`, `repair_cost`, `repair_cost_complete`, `net_proceeds`, `avoided_cost`.
  - `financial_status` — `complete`, `conditional` or `insufficient`.
  - `financial_note`, `prerequisites`, `tradeoffs` and `uncertainty`.
- `financial_ranking` and `resource_ranking`: each has `order` (definitive), `conditional` (numbers on incomplete evidence), `unranked`, `explanation` and `complete`.
- `disposal_guidance[]` — general end-of-life guidance, kept separate from the options.
- `safety.risks[].status` (from `/api/checks/plan`) can also be `identified_in_follow_up`.
- `safety_constrained`, `conditional_findings`, `rankings_differ` and `disclaimers`.

## POST /api/report

Body `{"snapshot": AssessmentSnapshot, "recommendation": RecommendationResult|null}`. Returns `text/markdown` as an attachment.
