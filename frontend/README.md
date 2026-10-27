# E-waste Sorter — frontend

React 19 · TypeScript · Vite · Tailwind CSS v4 · Motion · Radix Dialog · Lucide · `@google/model-viewer` (decorative device models, lazy-loaded).

Copied from `AIMS_Demo` (the “ReLoop” prototype) and extended into the 7-step E-waste Sorter workflow. The original folder is unchanged.

```bash
npm install
npm run dev -- --port 5288 --strictPort   # http://localhost:5288 (backend must run on :8000)
npm test          # vitest: reducer, selectors, identity rules
npm run typecheck
npm run lint      # oxlint
npm run build
```

Set `VITE_API_BASE_URL` (see `.env.example`) if the backend is not on `http://localhost:8000`. No API keys are used or stored in the frontend.

## Layout

```
src/
  content/   sections.ts (order + copy), devices.ts (required views per device), labels.ts, assets.ts
  services/  api.ts — HTTP client for the backend
  state/     assessmentReducer.ts (in-memory only), AssessmentContext.tsx (async flows),
             selectors.ts, Backend.tsx (mode/readiness), Navigation.tsx, Announcer.tsx
  lib/       photos.ts (browser-side file checks), identity.ts (identity confirmation rules)
  types/     api.ts (mirrors backend schemas), assessment.ts
  components/
    assessment/  DevicePicker, PhotoUploader, AnalysisStatus, ReviewPanel, FunctionalityForm,
                 IdentityForm, LocationForm, ResultsSummary
    layout/      AppSidebar, MobileNavigation, ModeBanner, NavList, ProgressRail, JourneySection…
    media/, ui/
```

Assessment data (photos as object URLs, answers, results) lives only in React state. Nothing goes into `localStorage`, and reloading clears everything. Object URLs are revoked when photos are removed or the assessment is reset.

`content/devices.ts` view ids must match `REQUIRED_VIEWS` in `backend/app/schemas/physical.py`.

Editorial images and 3D models: see `content/assets.ts`. Models in `public/assets/models/` were orientation-fixed with `scripts/fix-glb-mirror.py`.
