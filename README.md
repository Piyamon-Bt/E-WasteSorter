# E-waste Sorter (MVP prototype)

A localhost web prototype that assesses **one laptop or mobile phone** from photos, guides basic functional checks, and compares **Reuse, Resell as-is, Repair then reuse, Repair then resell and Recycle** using local price and service evidence. It produces two separate rankings, **financial value** and **resource use / life extension**, plus a downloadable Markdown report.

It runs in two modes:

- **Mock mode** (default): no API keys and zero paid calls. Results are clearly labelled simulated fixtures.
- **Live mode**: OpenAI Responses API (`gpt-6.1-terra`) for image assessment and web-search price research, plus Google Places API (New) for nearby services. Needs your own keys and billing.

> Status: the mock workflow is implemented and tested locally. The live integrations are implemented and checked offline against the official SDK request format, but **not verified against the real services**, because no credentials were available. No model accuracy has been measured.

## Requirements

- macOS/Linux with Python 3.10+ and Node.js 20+ (tested with Python 3.10 and the Node version used by Vite 8)

## Start (mock mode)

Terminal 1 — backend (http://localhost:8000):

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
.venv/bin/uvicorn app.main:app --reload --port 8000
```

Terminal 2 — frontend (http://localhost:5288):

```bash
cd frontend
npm install
npm run dev -- --port 5288 --strictPort
```

Open http://localhost:5288. A black **“Demo mode — simulated results”** bar stays at the top. Use its **Scenario** menu to switch between the mock cases (normal, visible damage, suspected risk, unknown model, missing market data, provider failure).

If you use a different frontend port, set `FRONTEND_ORIGIN` in `backend/.env` to match (CORS only allows that origin).

## Switch to live mode

1. Get keys (see [docs/SETUP.md](docs/SETUP.md)): an OpenAI API key with billing enabled, and a Google Cloud API key with **Places API (New)** enabled on a billing-enabled project.
2. Edit `backend/.env` (never commit it):
   ```env
   APP_MODE=live
   OPENAI_API_KEY=sk-...
   OPENAI_MODEL=gpt-6.1-terra
   GOOGLE_MAPS_API_KEY=...
   PROJECT_BUDGET_THB=4000
   PRIOR_SPEND_THB=0       # spend already made outside this app
   USD_TO_THB=35           # set your real exchange rate
   ```
3. Restart the backend. The top bar changes to “Live mode”.
4. Run the live smoke test in [docs/SETUP.md](docs/SETUP.md#live-smoke-test) before demoing.

## Run the tests

```bash
cd backend && .venv/bin/python -m pytest -q
cd frontend && npm test && npm run typecheck && npm run lint && npm run build
```

## Documentation

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — components and service responsibilities
- [docs/SETUP.md](docs/SETUP.md) — environment variables, keys, billing, live smoke test
- [docs/API.md](docs/API.md) — backend endpoints with examples
- [docs/TESTING.md](docs/TESTING.md) — automated tests, mock scenarios, demo script
- [docs/LIMITATIONS.md](docs/LIMITATIONS.md) — what is not done or not verified
- [docs/EWASTE_MVP_REQUIREMENTS.md](docs/EWASTE_MVP_REQUIREMENTS.md) — agreed requirements

## Project layout

```
backend/    FastAPI app (routers, services, providers, fixtures, tests)
frontend/   React + Vite + Tailwind UI (copied from AIMS_Demo and extended)
dataset/    Existing image dataset and splits (not modified, not used for training)
audit/      Earlier dataset audit notes
docs/       Requirements and project documentation
```

## Privacy and cost in one paragraph

Assessments live only in the browser's memory. Reloading or closing the page clears them; there are no accounts, history or drafts. The backend processes photos in memory, strips metadata by re-encoding them, and stores nothing except a local **usage ledger** (`backend/data/usage_ledger.jsonl`) with token counts and estimated costs only. The ledger stays across sessions so the THB 4,000 project budget is tracked. Paid calls are blocked before they start when the remaining budget or per-assessment limits would be exceeded. Provider-side data handling is governed by each provider's own settings; this app does not claim zero retention.
# E-WasteSorter
