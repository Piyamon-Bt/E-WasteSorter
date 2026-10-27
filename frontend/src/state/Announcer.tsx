import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react'

interface AnnouncerValue {
  announce(message: string): void
}

const Ctx = createContext<AnnouncerValue>({ announce: () => {} })

/** A single polite live region for meaningful async changes. */
export function AnnouncerProvider({ children }: { children: ReactNode }) {
  const [message, setMessage] = useState('')

  const announce = useCallback((text: string) => {
    // Clear first so repeating the same text is still announced.
    setMessage('')
    window.setTimeout(() => setMessage(text), 50)
  }, [])

  const value = useMemo(() => ({ announce }), [announce])
  return (
    <Ctx.Provider value={value}>
      {children}
      <div className="sr-only" role="status" aria-live="polite" aria-atomic="true">
        {message}
      </div>
    </Ctx.Provider>
  )
}

// oxlint-disable-next-line react/only-export-components
export function useAnnouncer() {
  return useContext(Ctx)
}
