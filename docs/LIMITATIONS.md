# Limitations and unverified behavior

## Not verified

- **Live providers were never called.** No OpenAI or Google credentials were available. The request shapes were checked offline against the installed OpenAI SDK (3.39.0) and the official docs (27 Oct 2026). Real responses, model availability for your project, citation density, web-search coverage for Thai or other markets, and Places result quality are unknown until the live smoke test in [SETUP.md](SETUP.md#live-smoke-test) is run.
- **No accuracy measurement.** No claim is made about damage detection, false alarms, identity suggestions or price quality. The existing dataset has not been run through the live model.
- **Cost estimates** use list prices checked on 27 Oct 2026 and an assumed exchange rate (`USD_TO_THB=35`). They ignore free tiers and may differ from billed amounts. Spend outside the app is unknown unless entered as `PRIOR_SPEND_THB`.

## Product limits (by design for this MVP)

- One laptop or mobile phone per assessment. Photos are uploaded from a computer. English only.
- **View checks are slot-assignment only.** The app does not verify that a photo shows the named view. Quality checks are heuristics: resolution, brightness, and a blur warning.
- No damage bounding boxes and no 3D damage display. The page keeps the original decorative 3D device models from the AIMS_Demo frontend; they show no assessment data.
- Functional results are user-reported. Identity is user-confirmed. “Evidence-verified” only means the photos gave *strong* identity evidence and the user kept that candidate unchanged.
- Re-checking a risk can clear it only when the AI's re-check of **new** photos says the issue is not present. That decision relies on model judgement, so the UI still advises caution.
- Prices: only cited pages in the selected country are accepted. Asking prices are not completed sales, and selling fees are not included. Ranges that mix genuine and aftermarket parts are labelled, not separated into options.
- The financial ranking covers cash outcomes only (resell as-is, repair then resell). A definitive order needs sale or buyback evidence on a common channel plus a complete repair cost. Anything else is listed as conditional. Reuse is shown as an avoided replacement cost (based on asking prices), not income.
- Repair costs depend on scenario mapping (`CHECK_NEEDS` and part keywords in `recommendations.py`). These map findings to possible causes; they are rules of thumb, not diagnoses. A shared repair (for example a screen assembly for cracked glass plus a touch fault) is counted once, but the app cannot know whether it fixes every finding.
- Recycle is never offered as a ranked option. This MVP has no way to establish end-of-life evidence (for example a professional's irreparability assessment), and price evidence alone is not enough. Uneconomic repairs are reported as an economic finding, and general disposal and battery-handling guidance is shown separately.
- Selling fees, shipping and taxes are not included in net proceeds.
- The resource ranking is a fixed qualitative order over the options present (reuse → repair & reuse → repair & resell → resell). No environmental savings are quantified.
- Local services are discovery only: no contact, booking or photo sharing. Distances are straight-line and shown only when you share your location. Listings do not prove certification, opening hours or repair capability.
- No accounts, history, drafts or resume. Reloading clears the assessment. Per-assessment limits are in memory and reset when the backend restarts; the budget ledger does not.
- Provider data handling (for example OpenAI's or Google's retention) depends on your provider account settings. Requests use `store=False` for OpenAI, but the app does not claim zero retention.

## Known technical gaps

- The frontend mirrors the backend's risk-history rules (`frontend/src/lib/observations.ts`) only for highlighting. The backend remains the authority for blocking checks.
- Re-checks run one at a time per observation. A response that arrives after a newer request was sent for the same observation is ignored.

- The frontend copy of the required views (`frontend/src/content/devices.ts`) must be kept in sync with `REQUIRED_VIEWS` in `backend/app/schemas/physical.py` by hand.
- The country → currency map in `price_research.py` covers common countries only. Other countries accept any currency stated by a cited source, as long as the market matches.
- The mock follow-up keeps a suspected risk unresolved, so the "cleared after follow-up" path is only covered by backend tests, not the mock UI.
- Multipart uploads above about 1 MB may be spooled by Starlette into a temporary file during the request. It is closed (and deleted) when the request finishes.
- The frontend has no component/browser test suite. UI flows were checked manually in a browser in mock mode.
