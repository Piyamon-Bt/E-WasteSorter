import { ModeBadge } from './ModeBanner'
import { NavList } from './NavList'
import { StartOverDialog } from './StartOverDialog'
import { Wordmark } from './Wordmark'

/** Fixed desktop sidebar (≥1024px). */
export function AppSidebar() {
  return (
    <aside
      data-print="hide"
      className="fixed inset-y-0 left-0 z-30 hidden w-[var(--sidebar-w)] flex-col border-r border-line bg-white px-5 py-8 lg:flex"
    >
      <Wordmark />
      <nav aria-label="Assessment sections" className="mt-12 -ml-4">
        <NavList />
      </nav>
      <div className="mt-auto flex flex-col items-start gap-3">
        <ModeBadge />
        <StartOverDialog />
      </div>
    </aside>
  )
}
