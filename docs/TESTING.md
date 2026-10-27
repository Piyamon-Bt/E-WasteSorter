# Testing

## Automated

```bash
cd backend && .venv/bin/python -m pytest -q        # 54 tests, mock providers and fake clients only
cd frontend && npm test                             # reducer, selectors, identity rules
cd frontend && npm run typecheck && npm run lint && npm run build
```

Backend tests never call real services. Live-mode behavior is tested with fake OpenAI clients and an `httpx.MockTransport` for Google Places. Each test uses a temporary ledger and environment overrides, so a real `backend/.env` cannot leak in.

| Requirement / acceptance case | Test |
|---|---|
| Missing or duplicate views block analysis; unusable images explained | `test_physical.py` |
| One-view damage retained | `test_mock_result_is_labelled_and_keeps_one_view_damage`, `test_one_view_damage_leads_to_repair_options` |
| Cosmetic mark ≠ repair recommendation | `test_cosmetic_only_does_not_recommend_repair` |
| Risk blocks power/charging; disagreement does not clear it; only new photos can | `test_checks.py` (risk tests), `test_follow_up_disagreement_does_not_clear_mock_risk` |
| Cracked glass + working touch both true | `test_cracked_glass_and_working_touch_can_both_be_true` |
| Unknown/Unable stay unknown; power failure → dependents unavailable | `test_unknown_and_unable_stay_unknown_not_pass`, `test_power_failure_makes_dependent_checks_unavailable` |
| Conflicting answers ask for clarification | `test_conflicting_display_and_touch_ask_for_clarification` |
| Unknown model → services but no model prices | `test_unknown_model_skips_prices_but_keeps_services` |
| Selected unverified model → conditional | `test_selected_unverified_model_is_conditional`, frontend identity tests |
| No local prices → report, no foreign substitution | `test_no_local_prices_still_reports_without_foreign_substitution`, `test_uncited_foreign_or_wrong_currency_records_are_dropped` |
| Symptom → scenarios, not diagnosis | `test_charging_failure_is_scenarios_not_diagnosis`, `test_charging_symptom_gives_alternative_scenarios` |
| Power failure alone ≠ recycle | `test_power_failure_alone_does_not_force_recycling` |
| Location denied → manual area | `test_location_denied_manual_area_works_and_distance_only_with_coords` |
| Financial arithmetic, no double-counted labor | `test_financial_arithmetic_and_no_double_counted_labor`, `test_net_proceeds_are_gross_minus_repair_cost` |
| Rankings differ and explain | `test_rankings_can_differ_and_explain` |
| Report provenance and mock labels | `test_report_is_traceable_and_labelled` |
| Timeout / invalid response / quota / auth | `test_price_research_provider_errors_are_reported`, `test_invalid_response_is_reported`, `test_physical_live_timeout_returns_http_error`, `test_places_auth_error_is_reported` |
| Budget and per-assessment limits, retries budgeted | `test_budget_limit_stops_calls_before_spending`, `test_per_assessment_call_limit`, `test_timeouts_are_retried_within_budget`, `test_usage.py` |
| Zero paid calls in mock mode | `test_mock_mode_never_builds_live_providers` |
| No silent live fallback | `test_live_without_keys_gives_actionable_error_not_mock` |
| Reload clears assessment; ledger retained | frontend `reset` test, `test_ledger_persists_across_restarts_and_holds_metadata_only`, `test_backend_stores_no_assessment_state` |

## Mock scenarios (top bar → Scenario)

| Scenario | What it demonstrates |
|---|---|
| Normal condition | Cosmetic wear only → no repair options |
| Visible damage (default) | Damage in the front view only; repair scenarios and costs; rankings differ |
| Suspected battery swelling | Power/charging tests stopped; disagreement and re-check stay unresolved; constrained options |
| No readable identity | Weak identity evidence; choose “I don’t know the model” for the unknown-model path |
| No local price data | Insufficient data, but the report still completes |
| Provider failure | Price search times out and service search hits a quota error; physical results remain |

Incomplete checks: answer some checks Unsure / Unable to test, or leave them blank, then save. Countries other than Thailand have no simulated prices, which shows that foreign prices are not substituted.

## Demo script (about 5 minutes)

1. Scenario **Visible damage** → Mobile phone → add 6 photos → Analyze. The damage references the Front screen only.
2. Agree with both observations → Continue. Answer all checks Pass → Save. Note the “cracked glass and working touch are both true” finding.
3. Pick the suggested candidate → Confirm. Thailand, area “Bangkok” → Search.
4. Results: price types and simulated sources, services, options with gross / repair / net, two different rankings → Download report.
5. Start Over → scenario **Suspected battery swelling** → Laptop. Disagree with the risk → Continue. Checks are stopped for safety.
6. Reload the page: everything is cleared. `curl localhost:8000/api/usage` shows the ledger is unchanged (mock calls are free and not recorded).

## Evaluation (not yet done)

The image component should be evaluated with the existing `dataset/splits/external_condition` validation set for prompt tuning and the test set once, at the end, without tuning on test answers. Report laptop and mobile separately, including false alarms, missed damage and abstentions. See `audit/AUDIT_2026-10-27_TH.md` for the known shortcut (mobile damage photos are all 150×150) that inflates naive scores. End-to-end evaluation needs real devices with complete views; single-image dataset labels cannot replace it. No accuracy figure exists yet.
