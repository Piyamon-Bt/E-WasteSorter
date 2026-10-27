import { useAssessment } from '../../state/AssessmentContext'
import { useBackend } from '../../state/Backend'

/** Persistent mode notice at the top of the page. Always visible in demo mode. */
export function ModeBanner() {
  const { status, health, error, isMock, retry } = useBackend()
  const { state, actions } = useAssessment()

  if (status === 'unreachable') {
    return (
      <div role="alert" data-print="hide" className="sticky top-[var(--header-h)] z-20 border-b border-danger bg-white px-4 py-2 text-[14px] text-danger lg:top-0">
        {error} Start it with <code>uvicorn app.main:app --port 8000</code> in <code>backend/</code>.{' '}
        <button type="button" className="underline" onClick={retry}>
          Retry
        </button>
      </div>
    )
  }

  if (!isMock) {
    return (
      <div data-print="hide" className="sticky top-[var(--header-h)] z-20 border-b border-line bg-white px-4 py-2 text-[13px] text-muted lg:top-0">
        Live mode — results come from {health?.openai.model ?? 'the configured AI model'} and Google Places. Provider
        calls are billed.
      </div>
    )
  }

  const scenarios = health?.mock_scenarios ?? {}
  return (
    <div className="sticky top-[var(--header-h)] z-20 flex flex-wrap items-center gap-x-4 gap-y-1 border-b border-ink bg-ink px-4 py-2 text-[14px] text-white lg:top-0">
      <strong className="font-medium">Demo mode — simulated results</strong>
      <span className="hidden text-neutral-300 sm:inline">No paid API calls. Findings, prices and shops are fictional.</span>
      {Object.keys(scenarios).length > 0 && (
        <label data-print="hide" className="flex min-w-0 items-center gap-2 text-[13px] text-neutral-300 sm:ml-auto">
          Scenario
          <select
            value={state.mockScenario ?? 'visible_damage'}
            onChange={(e) => actions.setMockScenario(e.target.value)}
            className="min-h-9 min-w-0 max-w-[14rem] rounded-md border border-neutral-500 bg-ink px-2 text-white"
          >
            {Object.entries(scenarios).map(([id, label]) => (
              <option key={id} value={id}>
                {label}
              </option>
            ))}
          </select>
        </label>
      )}
    </div>
  )
}

export function ModeBadge() {
  const { isMock, status } = useBackend()
  return (
    <p className="inline-flex items-center gap-2 rounded-full border border-line px-3 py-1 text-[12px] text-muted">
      <span aria-hidden className={`size-1.5 rounded-full ${status === 'unreachable' ? 'bg-danger' : 'bg-accent'}`} />
      {status === 'unreachable' ? 'Backend offline' : isMock ? 'Demo mode' : 'Live mode'}
    </p>
  )
}
