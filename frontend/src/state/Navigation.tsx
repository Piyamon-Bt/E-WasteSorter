import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import { sections } from '../content/sections'
import { usePrefersReducedMotion } from '../hooks/useMediaQuery'
import type { SectionId } from '../types/assessment'

interface NavigationValue {
  /** Section currently in view — purely presentational, never affects assessment data. */
  activeSection: SectionId
  goToSection(id: SectionId, opts?: { push?: boolean }): void
}

const Ctx = createContext<NavigationValue | null>(null)
const ids = sections.map((s) => s.id)
const isSectionId = (v: string): v is SectionId => (ids as string[]).includes(v)

export function NavigationProvider({ children }: { children: ReactNode }) {
  const [activeSection, setActiveSection] = useState<SectionId>('device')
  const reduced = usePrefersReducedMotion()

  const scrollTo = useCallback(
    (id: SectionId) => {
      const el = document.getElementById(id)
      if (!el) return
      el.scrollIntoView({ behavior: reduced ? 'auto' : 'smooth', block: 'start' })
      // Move focus to the heading so keyboard and screen-reader users land in the section.
      el.querySelector<HTMLElement>('[data-section-heading]')?.focus({ preventScroll: true })
    },
    [reduced],
  )

  const goToSection = useCallback(
    (id: SectionId, { push = true } = {}) => {
      if (push && window.location.hash !== `#${id}`) {
        history.pushState(null, '', `#${id}`)
      }
      scrollTo(id)
    },
    [scrollTo],
  )

  // Back/forward support for hash navigation.
  useEffect(() => {
    history.scrollRestoration = 'manual'
    const onPop = () => {
      const hash = window.location.hash.slice(1)
      if (isSectionId(hash)) scrollTo(hash)
      else window.scrollTo({ top: 0, behavior: reduced ? 'auto' : 'smooth' })
    }
    window.addEventListener('popstate', onPop)
    // Honour a hash on first load.
    const initial = window.location.hash.slice(1)
    if (isSectionId(initial)) {
      requestAnimationFrame(() => document.getElementById(initial)?.scrollIntoView())
    }
    return () => window.removeEventListener('popstate', onPop)
  }, [scrollTo, reduced])

  // Track the visible section with IntersectionObserver (no per-scroll state updates).
  useEffect(() => {
    const visible = new Set<SectionId>()
    const pick = () => {
      const first = ids.find((id) => visible.has(id))
      if (first) setActiveSection(first)
    }
    const band = new IntersectionObserver(
      (entries) => {
        for (const e of entries) {
          const id = e.target.id
          if (!isSectionId(id)) continue
          if (e.isIntersecting) visible.add(id)
          else visible.delete(id)
        }
        pick()
      },
      // A thin horizontal band 30–40% down the viewport.
      { rootMargin: '-30% 0px -60% 0px' },
    )
    const sentinel = document.getElementById('page-end')
    const end = new IntersectionObserver((entries) => {
      if (entries.some((e) => e.isIntersecting)) setActiveSection(ids[ids.length - 1])
      else pick()
    })
    ids.forEach((id) => {
      const el = document.getElementById(id)
      if (el) band.observe(el)
    })
    if (sentinel) end.observe(sentinel)
    return () => {
      band.disconnect()
      end.disconnect()
    }
  }, [])

  const value = useMemo(() => ({ activeSection, goToSection }), [activeSection, goToSection])
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}

// oxlint-disable-next-line react/only-export-components
export function useNavigation() {
  const ctx = useContext(Ctx)
  if (!ctx) throw new Error('useNavigation must be used within NavigationProvider')
  return ctx
}
