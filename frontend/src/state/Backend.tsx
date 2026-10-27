import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { api, ApiError } from '../services/api'
import type { Health } from '../types/api'

interface BackendValue {
  status: 'loading' | 'ready' | 'unreachable'
  health: Health | null
  error: string | null
  isMock: boolean
  retry(): void
}

const Ctx = createContext<BackendValue | null>(null)

/** Reads the backend mode and readiness once. Not part of the assessment, so reset keeps it. */
export function BackendProvider({ children }: { children: ReactNode }) {
  const [health, setHealth] = useState<Health | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    let active = true
    api
      .health()
      .then((h) => active && (setHealth(h), setError(null)))
      .catch((err: unknown) => active && setError(err instanceof ApiError ? err.message : 'The backend is not reachable.'))
    return () => {
      active = false
    }
  }, [attempt])

  const retry = useCallback(() => {
    setError(null)
    setAttempt((n) => n + 1)
  }, [])

  const value = useMemo<BackendValue>(
    () => ({
      status: health ? 'ready' : error ? 'unreachable' : 'loading',
      health,
      error,
      // Until the backend answers, assume demo mode so nothing is presented as live.
      isMock: health ? health.mode === 'mock' : true,
      retry,
    }),
    [health, error, retry],
  )
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}

// oxlint-disable-next-line react/only-export-components
export function useBackend() {
  const ctx = useContext(Ctx)
  if (!ctx) throw new Error('useBackend must be used within BackendProvider')
  return ctx
}
