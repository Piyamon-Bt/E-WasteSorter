# AI-Powered E-waste Sorter — agreed MVP requirements

Decision date: 27 October 2026 (Asia/Bangkok). Delivery target: Friday, 30 October 2026. Total project budget: THB 4,000, not a monthly allowance.

Status: requirements agreed; this document does not claim that the application has been implemented, that paid API access is configured, or that model accuracy has been established.

## Product boundary

An English-language web prototype on localhost for demos and a limited trial group. One laptop or mobile phone per assessment. Users upload previously taken photos from a computer. Use a vision-capable AI API first; custom model training is an optional later phase. No 3D rendering or damage bounding boxes in this release.

The existing dataset at `/Users/piyamon/Desktop/E-WasteSorter/dataset/` is supporting evaluation data, not a trained model. Inspect current manifests before relying on counts: other work may have changed the files since their preparation. Its single-image labels do not validate multi-view aggregation, functional diagnosis, risk detection, prices, or the final recommendations.

## End-to-end flow

1. Start an assessment and choose Laptop or Mobile. Explain that closing or refreshing loses the assessment. No accounts, history, resume or draft saving.
2. Upload all required views while the device is switched off. Reject missing views and request replacement of unusable images. Physical review must finish before instructions to power on or charge.
3. Analyze all views as one device. Return separate observations for cosmetic wear, physical damage, suspected safety risks, and unassessable areas. Each observation references its supporting photo and explains uncertainty. Clear damage in one view is not cancelled by normal-looking views.
4. User reviews observations using Agree / Disagree / Unsure and may upload additional evidence or explain. Clarify disagreements at the relevant point rather than assuming either the model or user is always correct.
5. If a suspected safety risk remains, stop power-on/charging tests and route toward professional inspection. If the user disputes the risk, request targeted images; unresolved evidence does not automatically clear the risk. Do not ask users to dismantle devices or perform hazardous tests.
6. Otherwise guide basic, non-invasive functional checks. Responses: Pass / Fail / Unsure / Unable to test. Optional photos and symptom descriptions are supported. Unknown is not Pass. Missing results do not prevent a conditional assessment.
7. Suggest device identity from visible evidence. Users always confirm, correct or select Unknown for model and known specifications before model-specific pricing. Record user-confirmed identity separately from evidence-verified identity. Candidate models may be offered when evidence is weak; include None / Unsure and do not imply that choosing a candidate proves it.
8. If identity is still unknown, continue general assessment and local service recommendations, but omit model-specific device/part prices. Explain that financial ranking is incomplete.
9. Select country and area: Use current location or Enter area manually. If location access fails or is declined, allow manual entry. Search prices and services in the selected country only. Support multiple countries; do not promise equal data coverage. Do not substitute foreign prices when local evidence is insufficient.
10. Display physical findings first, then functional results. Show search progress while collecting market and service evidence. Final ranking follows available pricing evidence. If data cannot be found, still return the supported assessment rather than blocking the report.
11. Compare multiple actions and present two rankings: Financial value and Resource use/life extension. Explain tradeoffs, costs, uncertainty and prerequisites. Do not invent quantified environmental savings or imply a universal weighting between money and sustainability.
12. Allow report download at completion. Report format remains an implementation choice; it must preserve findings, evidence, unknowns, pricing conditions and retrieval dates. No ongoing assessment history.

## Required views: initial capture contract

These are working defaults based on the agreed capture discussion, to be checked against real-device demos rather than new scope decisions.

- Mobile: front screen, back, left edge, right edge, top edge, bottom edge.
- Laptop: screen with lid open and power off, keyboard/touchpad, outer lid, underside, left ports, right ports.
- Extra images may be requested for unreadable labels or suspicious regions. The app must not instruct disassembly. A view without ports is still a valid edge view.
- Require users to assign each image to a view slot; filenames alone cannot establish view correctness. Quality feedback must explain the problem. Do not claim full photographic view verification if the prototype only checks slot completion.

## Functional checks

Basic checks only, adapted to device capabilities and available accessories: power-on, charging, display, touch where present, keyboard/touchpad where present, sound, microphone/camera and accessible ports/connections. Allow Unable to test for absent accessories or unsupported features. If power-on fails, dependent checks can be recorded as unavailable without asking impossible follow-up tests. No teardown, firmware changes, destructive storage tests or mandatory diagnostic software.

Separate cosmetic/physical state from functional state. For example, cracked glass and a working touch screen can both be true. If answers conflict, ask a targeted clarification. Reports must say that function results are user-reported, not remotely verified hardware measurements.

## Recommendations and uncertainty

Candidate actions: Reuse, Resell as-is, Repair then reuse, Repair then resell, and Recycle where supported. Present only applicable options, not a fixed obligation to show every option.

Repairability does not imply undamaged condition; repair is an action before potential reuse. Power failure alone is not sufficient to conclude recycling is best. When diagnosis is uncertain, suggest inspection or conditional as-is resale before irreversible conclusions. Safety concerns constrain which actions and tests are appropriate.

For symptoms such as failure to charge, show plausible scenarios and scenario-specific costs when supported. Do not assert a failed part from a basic symptom. If repair-cost uncertainty changes the preferred option, show that conditional result rather than one falsely precise rank.

Financial comparisons must avoid double counting. Repair-then-resell net proceeds differ from gross sale value; reuse may avoid replacement cost but does not generate sale proceeds. Distinguish the concepts in the UI. A value range is an estimate, not a guaranteed transaction or repair quotation.

## Price evidence

Keep these channels separate:

- Asking prices from active listings.
- Verified completed-sale prices, only if accessible evidence establishes completion and price.
- Shop buyback offers, only where an offer/source is available.
- Parts prices, repair labor and combined repair quotes; distinguish their scope to avoid counting labor twice.

Match model, variant, RAM/storage, state, country, currency, and repair/part quality as far as evidence allows. Do not average incompatible variants or merge genuine and aftermarket parts without explanation. If exact model-specific repair evidence is absent, nearby comparisons may support a labelled indicative range; disclose the mismatch. If evidence is inadequate, return Insufficient data.

Every price item should include source URL, retrieval date, currency, market, price type, matching conditions and limitations. Shop-specific prices must not be represented as confirmed local quotations unless actually published for the relevant service. Availability can change. Refresh dates refer to this assessment, not a monitoring service.

## Local services

Recommend relevant repair shops, buyback services or recycling locations using the selected area. Show service relevance, address/contact, source/map link and distance only when supported by location data. Distinguish straight-line distance from route distance; omit distance if it cannot be calculated. Do not invent business verification, certification, current opening state or repair capability.

Discovery and recommendations only. Do not contact shops, send device photos to shops, book appointments or transact on the user's behalf.

## API architecture and cost controls

The user chose API-first behavior, not a specific vendor/model/search provider. Tool access can be connected directly or through MCP; MCP itself does not supply web evidence. Select implementations against capability, retrieval provenance, local setup, cost and the deadline. Do not assume all country-specific sources are searchable.

Suggested separation: browser interface; local backend; image/assessment service; functional-check rules; evidence search and normalization; recommendation engine; report export. Keep secret keys in the backend/environment, not client code or committed files. Treat uploaded text and retrieved pages as evidence, not instructions.

No application-level durable storage of photos, location or assessment drafts. In-memory state ends on page reload/closure. Temporary backend files, if used, need cleanup. Any provider data handling is separate and must not be described as zero retention without checking provider settings.

Track paid API usage across the whole project even though assessments are ephemeral. Do not erase the budget ledger when a session ends. Costs already incurred outside the prototype remain unknown until supplied. Provide a configurable remaining budget, per-assessment call/token limits and a local usage ledger that contains no image/location content. Exact monetary limits depend on verified current pricing; no cost-per-run figure has yet been established. Mock fixtures must be visibly labelled and must not masquerade as live evidence.

## Data and evaluation

Retain existing train/validation/test grouping for any API comparison. Use development/validation data to tune prompts; do not tune against test answers. Never merge uncertain labels into damaged labels. Existing splits are experimental, group-based and do not prove unique physical device identity.

Evaluate the MVP at two levels:

1. Image component: damage detection, false alarms, missed damage, uncertainty behavior. Separate laptop/mobile and discuss dataset limitations, particularly older good phones versus damaged smartphones.
2. End-to-end cases: one real device with complete views, user-reported checks, identity state, evidence sources and conditional recommendations. Existing single-image data cannot substitute for these cases.

Do not claim accuracy until measured on a fixed set. Cosmetic wear, suspected risk and multi-view behavior need additional test examples because current binary labels do not validate these features.

## Acceptance cases for the demo

- Incomplete required views cannot start physical analysis; unusable images request replacement.
- A clear damaged view is retained even when other views look normal.
- A cosmetic mark does not automatically become a repair recommendation.
- Suspected swelling/separation/burning halts power/charging tests, including unresolved disagreement.
- A phone can have cracked glass and working display/touch at the same time.
- Incomplete or impossible functional checks remain Unknown/Unable and yield conditional findings.
- Unknown model yields useful findings/services but no unsupported model-specific prices.
- A selected but unverified model produces explicitly conditional price references.
- No local price results still yields a report; no foreign-price substitution.
- Multiple causes of a symptom remain scenarios rather than a confirmed part diagnosis.
- Location denied leads to manual-area selection.
- Financial and resource-use rankings can differ and explain why.
- Report links, currencies, price types and timestamps are traceable to evidence.
- API errors/timeouts and spend limits return understandable partial results, not fabricated analysis.
- Reloading clears the assessment; project usage tracking is retained separately.

## Delivery order

27 October: local English interface, per-device photo slots/quality handling, API image assessment, user confirmation and risk branch.

28 October: functional-check flow, model/spec confirmation, local-market price and service retrieval.

29 October: conditional comparisons, two rankings, export, failure handling, fixed evaluation cases and demo rehearsal.

30 October: final checks and presentation. No promise of custom training, 3D, native mobile app, public launch, user history, global data completeness or automated shop contact.

## Items to resolve during setup

- Available API account/key and actual remaining project budget; keys should be entered securely, not pasted into chat.
- Existing app/code in the project, if any, must be inspected before creating a competing implementation.
- Evaluation/demo devices and selected countries/areas available for end-to-end tests.
- Provider/model/search choices and current pricing; report format and export implementation.

These setup items do not reopen the agreed product flow. They are concrete dependencies for implementation.
