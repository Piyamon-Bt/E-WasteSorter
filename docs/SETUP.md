# Setup

## Prerequisites

- Python 3.10+ and Node.js 20+
- For live mode: an OpenAI API account with billing, and a Google Cloud project with billing and **Places API (New)** enabled

## Install and start

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
.venv/bin/uvicorn app.main:app --reload --port 8000
```

```bash
cd frontend
npm install
npm run dev -- --port 5288 --strictPort
```

Optional: copy `frontend/.env.example` to `frontend/.env` to point the browser at a different backend URL (`VITE_API_BASE_URL`).

## Environment variables (backend/.env)

| Variable | Default | Meaning |
|---|---|---|
| `APP_MODE` | `mock` | `mock` = simulated, no paid calls. `live` = real providers |
| `OPENAI_API_KEY` | empty | OpenAI key (live mode) |
| `OPENAI_MODEL` | `gpt-6.1-terra` | Model for images and price research |
| `GOOGLE_MAPS_API_KEY` | empty | Google key with Places API (New) |
| `FRONTEND_ORIGIN` | `http://localhost:5288` | The only origin allowed by CORS |
| `REQUEST_TIMEOUT_SECONDS` | `90` | Per provider request |
| `MAX_RETRIES` | `1` | Extra attempts after the first. Each attempt is budgeted |
| `MAX_UPLOAD_MB` | `10` | Per photo |
| `MAX_IMAGES_PER_REQUEST` | `12` | 6 required views + up to 6 detail photos |
| `MIN_IMAGE_SIDE_PX` | `480` | Smaller photos must be replaced |
| `API_IMAGE_MAX_SIDE_PX` | `1600` | Downscale before sending to the AI provider |
| `MAX_CALLS_PER_ASSESSMENT` | `12` | Paid calls per assessment (in memory) |
| `MAX_TOKENS_PER_ASSESSMENT` | `250000` | Token cap per assessment |
| `MAX_OUTPUT_TOKENS` | `4000` | Per OpenAI call |
| `MAX_WEB_SEARCH_CALLS` | `6` | Per price research request (`max_tool_calls`) |
| `PROJECT_BUDGET_THB` | `4000` | Total project budget (not monthly) |
| `PRIOR_SPEND_THB` | `0` | Spend already made outside this app |
| `USD_TO_THB` | `35` | **Assumption**: set your real rate |
| `OPENAI_INPUT_USD_PER_1M` / `OPENAI_OUTPUT_USD_PER_1M` | `1.00` / `5.00` | gpt-6.1-terra list price, checked 27 Oct 2026 |
| `OPENAI_WEB_SEARCH_USD_PER_1K` | `10.00` | Web search tool calls; search content tokens are billed as input |
| `ESTIMATED_TOKENS_PER_IMAGE` | `2500` | Conservative estimate per image |
| `ESTIMATED_SEARCH_CONTENT_TOKENS` | `8000` | Conservative estimate per search call |
| `PLACES_INCLUDE_CONTACT_FIELDS` | `true` | `true` = phone + website (Enterprise SKU), `false` = Pro SKU |
| `PLACES_PRO_USD_PER_1K` / `PLACES_ENTERPRISE_USD_PER_1K` | `32.00` / `35.00` | Text Search list prices, checked 27 Oct 2026 |
| `USAGE_LEDGER_PATH` | `data/usage_ledger.jsonl` | Relative to `backend/` |

Re-check prices on https://developers.openai.com/api/docs/pricing and https://developers.google.com/maps/billing-and-pricing/pricing before live use. The ledger is conservative: it ignores free usage tiers.

## Getting keys and billing

**OpenAI**
1. Sign in at https://platform.openai.com, add a payment method or credits under Billing, and set a monthly usage limit below your remaining budget.
2. Create a project API key, then paste it into `backend/.env` (`OPENAI_API_KEY=`). Do not paste keys into chat or commit them.
3. Check that your project can use `gpt-6.1-terra` (Limits / Models page). If it can't, set `OPENAI_MODEL` to an available vision model that supports web search, and update the pricing variables.

**Google Places API (New)**
1. In https://console.cloud.google.com create or select a project and link a billing account.
2. Enable **Places API (New)** (APIs & Services → Library).
3. Create an API key (APIs & Services → Credentials). Restrict it to *Places API (New)*. Because the key is used server-side, use an IP restriction rather than an HTTP-referrer restriction.
4. Set a budget alert and, if you want, quota caps for Text Search.
5. Put the key in `backend/.env` (`GOOGLE_MAPS_API_KEY=`).

## Switching to live mode

1. Set `APP_MODE=live` and both keys in `backend/.env`.
2. Set `PRIOR_SPEND_THB` to any amount already spent elsewhere, and `USD_TO_THB` to your rate.
3. Restart the backend.
4. Check readiness: `curl -s http://localhost:8000/api/health`. `key_configured: true` only means a key is present. `connection_verified` stays `false` until you run the smoke test.

## Live smoke test

This makes real, billed calls (roughly 3–10 calls). Watch `GET /api/usage` before and after.

```bash
cd backend
curl -s http://localhost:8000/api/usage
```

1. In the browser, run one **mobile** assessment with 6 real photos of a powered-off phone. Expected result: the top bar says Live mode, and observations reference your photo slots with no “Simulated” labels.
2. Disagree with one observation, add one close-up and re-check. Expected result: a follow-up outcome (upheld / revised / not supported / unresolved).
3. Complete the checks, confirm a model you know, choose Thailand and an area, then search. Expected results:
   - Price records link to real Thai pages with THB amounts and retrieval dates, or the app reports insufficient data.
   - Records without a cited URL are counted as discarded.
   - Services show Google Maps links and attribution.
4. Download the report. Check that links, currencies, price types and timestamps match the UI.
5. `curl -s http://localhost:8000/api/usage` shows the new ledger entries, and `backend/data/usage_ledger.jsonl` has no image, location or finding content.
6. Failure check: set `GOOGLE_MAPS_API_KEY=invalid`, restart, search again. Expected result: services show an `auth` problem, prices still appear, and no mock data is shown.

Record the outcome (date, model, which steps passed) before claiming live verification.

## Returning to mock mode

Set `APP_MODE=mock` and restart. Keys can stay in the file; mock mode never uses them.
