# Architecture

```
Browser (React, in-memory state)
   │  multipart photos / JSON          no keys in the browser
   ▼
FastAPI backend (localhost:8000)
   routers/      thin HTTP layer
   services/     business rules (plain Python)
   providers/    external calls: openai_provider, google_places_provider, mock_provider
   fixtures/     simulated data for mock mode
   data/         usage ledger (cost metadata only)
```

## Flow and responsibilities

| Step | Frontend component | Backend endpoint | Service |
|---|---|---|---|
| 1. Device type + required views | `DevicePicker`, `PhotoUploader` | — | — |
| 2. Physical assessment (all views together) | `AnalysisStatus` | `POST /api/assessments/physical` | `image_assessment` |
| 3. Review: Agree / Disagree / Unsure, targeted re-check | `ReviewPanel` | `POST /api/assessments/follow-up` | `image_assessment` |
| 4. Safety gate + functional checks | `FunctionalityForm` | `POST /api/checks/plan`, `POST /api/checks/evaluate` | `functional_checks` |
| 5. Model / specs confirmation | `IdentityForm` (`lib/identity.ts`) | — | — |
| 6. Country / area / current location | `LocationForm` | — | — |
| 7. Prices, services, options, rankings, report | `ResultsSummary` | `POST /api/market/prices`, `POST /api/services/nearby`, `POST /api/recommendations`, `POST /api/report` | `price_research`, `local_services`, `recommendations`, `report_export` |
| Mode, readiness, budget | `ModeBanner` | `GET /api/health`, `GET /api/usage` | `usage_tracking` |

### Services (backend/app/services)

- **image_assessment** — follow-ups re-check the *current effective* observation and receive the earlier follow-up history as risk context; validates slot assignment (every required view exactly once, optional `detail` photos), the image count and per-file size (checked before files are read, for both the physical and follow-up endpoints), decoding, minimum resolution, darkness/overexposure (blocking) and blur (warning). Re-encodes images to JPEG ≤1600 px, which strips EXIF/GPS. Dispatches to the mock or OpenAI provider. A follow-up result can only withdraw an observation when new photos were supplied.
- **functional_checks** — `resolve_observations` applies reviews and the **whole follow-up history** of each observation (`ObservationReview.follow_ups`, oldest first): revisions apply in order and keep the original id, and the state (accepted / disputed / withdrawn / unreviewed) follows the latest result. `safety_state` remembers every time a risk was asserted, either originally or by any follow-up revision. That risk blocks power/charging until the **most recent** follow-up, coming after the latest risk assertion, is an explicit `not_supported` result based on at least one usable new photo. Disagreement, `unresolved`, `upheld`, a failed request, or a later revision away from the risk kind never clear it. Check plans per device; evaluation handles Unknown/Unable, power-failure dependencies, contradictions and the charging accessory question.
- **price_research** — skips model-specific search for an unknown identity, searches only the selected country, and reports provider failures as issues with partial results.
- **local_services** — Places Text Search per need (repair, buyback, recycling); filters results by address country, since location bias is not a strict filter; straight-line distance only when coordinates were given.
- **recommendations** — plain-Python rules:
  - *Repair scenarios*: one scenario per intervention, with `needs` listing every finding it might address. Alternatives under one need are possible causes, never a diagnosis.
  - *Repair cost*: the range over every combination of one cause per need, with a shared intervention paid once. Per part quality, a combined quote **or** part + labor is used, never both; genuine and aftermarket are named alternatives. The cost is *complete* only if every combination is fully priced. Unpriced causes or part prices without labor make it incomplete, and the option becomes conditional.
  - *Sale channels*: completed sales, buyback offers and asking prices are computed separately per device condition, never pooled. Only `exact`/`close` matches are used. Sale options are compared on one common channel, picked in that order. An asking-price basis, or options with no common channel, is conditional. With unknown function, as-is resale shows both condition scenarios and is not ranked.
  - *Financial ranking*: `order` holds only options with complete evidence; `conditional` holds options with numbers but incomplete evidence. Reuse is shown as avoided cost, not ranked.
  - *Evidence gaps*: missing or incomplete functional checks, contradictory answers, disputed damage and (for repairs) unconfirmed alternative causes keep sale options `conditional`, with the assumptions written in `financial_note`. A priced repair does not prove the device will work afterwards. Only options whose evidence is actually sufficient are `complete` and enter the definitive order.
  - *Charger/cable*: the charging check asks whether a known-working charger was used. If so, the accessory is ruled out. Otherwise a replacement charger is a possible cause priced only from accessory evidence (a purchase price, no labor), never assumed free. The free "try a known-working charger" step is listed as a prerequisite, not as a zero repair cost.
  - *Recycle* is not offered as a ranked option: this MVP cannot establish end-of-life evidence, and price evidence alone does not show it. When the lowest repair cost is at least the highest working-device value, this is reported as an economic finding ("repair may not be financially worthwhile"). General disposal guidance is returned separately (`disposal_guidance`).
  - *Resource ranking*: qualitative life-extension order over the options present.
- **report_export** — Markdown report with findings, evidence, unknowns, price types, URLs, retrieval dates and simulated labels.
- **usage_tracking** — project budget ledger and per-assessment call/token limits (see below).

### Providers (backend/app/providers)

Mock and live providers return the same Pydantic schemas (`app/schemas`).

- **openai_provider** — Responses API. `responses.parse` with Structured Outputs for the physical assessment and follow-up (image input as `input_image` data URLs, `detail: high`, `store=False`). `responses.create` with the `web_search` tool (`user_location.country` = selected country, `include=["web_search_call.action.sources"]`, `max_tool_calls`) for prices. A price record is kept only if its URL appears in the response's `url_citation` annotations or search sources, and its market and currency match the selected country. SDK retries are off; the provider retries within the budget itself.
- **google_places_provider** — `POST https://places.googleapis.com/v1/places:searchText` via httpx, with an explicit field mask. Phone/website fields (Enterprise SKU) can be turned off with `PLACES_INCLUDE_CONTACT_FIELDS=false` (Pro SKU).
- **mock_provider** — fictional fixtures. It never reads image contents and never records paid usage.

Live failures never fall back to mock data. Missing keys produce `not_configured` errors that name the missing variable.

## Budget protection

1. Before every paid attempt (including retries), `UsageTracker.reserve` estimates a worst case: input tokens (≈2,500 per image, plus ≈8,000 per web search), `MAX_OUTPUT_TOKENS`, and search or Places fees from configured pricing.
2. The call is refused (`budget_limit`) if the estimate exceeds `PROJECT_BUDGET_THB − PRIOR_SPEND_THB − recorded spend − in-flight reservations`, or if the per-assessment call or token limits would be exceeded. Reservations are lock-protected, so concurrent calls can't both use the last of the budget.
3. After the call, the ledger records reported usage when the provider returns it. Otherwise (errors, timeouts) it records the worst-case estimate, because the request may still be billed.

These are estimates. The app cannot see spend outside itself or provider-side billing rules (e.g. free tiers), so it does not promise an exact billing cutoff.

## State and privacy

- Frontend: `useReducer` state only (`state/assessmentReducer.ts`). There is no `localStorage` or persistence, and object URLs are revoked on removal or reset. Keys (`analysisKey`, `inputKey`) discard stale responses after inputs change.
- Backend: stateless apart from the in-memory per-assessment counters and the ledger. Uploaded files are read into memory and closed. Request bodies are not logged.
- CORS allows only `FRONTEND_ORIGIN`.
- Prompts tell the model to treat text in images, user notes and web pages as untrusted evidence, not instructions.

## Frontend

The UI is the existing AIMS_Demo (“ReLoop”) React 19 + Vite + Tailwind v4 app, extended from 5 to 7 sections. Kept from the original: layout, sidebar, progress rail, typography, motion, the Radix dialog and decorative 3D device models. Removed: the old mock analysis service, the old frontend recommendation rules (now in the backend) and the damage-box overlay (out of scope for this release).
