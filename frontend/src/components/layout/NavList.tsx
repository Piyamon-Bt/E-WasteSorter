import { Check } from 'lucide-react'
import { sections } from '../../content/sections'
import { useAssessment } from '../../state/AssessmentContext'
import { useNavigation } from '../../state/Navigation'
import { selectCompleted, selectPrerequisites } from '../../state/selectors'
import type { SectionId } from '../../types/assessment'

interface NavListProps {
  /** Called instead of navigating directly (e.g. the drawer closes first). */
  onNavigate?(id: SectionId): void
}

/**
 * Numbered section links. "Current" (in view) and "Completed" (workflow step done)
 * are shown independently — scrolling never marks a step as completed.
 */
export function NavList({ onNavigate }: NavListProps) {
  const { state } = useAssessment()
  const { activeSection, goToSection } = useNavigation()
  const completed = selectCompleted(state)
  const prereq = selectPrerequisites(state)

  return (
    <ol className="space-y-1">
      {sections.map((s) => {
        const current = activeSection === s.id
        const done = completed[s.id]
        const note = done ? 'Completed' : prereq[s.id]
        return (
          <li key={s.id}>
            <a
              href={`#${s.id}`}
              aria-current={current ? 'location' : undefined}
              onClick={(e) => {
                e.preventDefault()
                if (onNavigate) onNavigate(s.id)
                else goToSection(s.id)
              }}
              className={`group relative flex min-h-11 items-center gap-3 rounded-md py-2 pr-2 pl-4 transition-colors ${
                current ? 'text-ink' : 'text-muted hover:text-ink'
              }`}
            >
              <span
                aria-hidden
                className={`absolute top-2 bottom-2 left-0 w-[2px] rounded-full transition-colors ${
                  current ? 'bg-accent' : 'bg-transparent'
                }`}
              />
              <span className="w-6 shrink-0 text-[12px] tabular-nums">{s.number}</span>
              <span className="flex min-w-0 flex-1 flex-col">
                <span className={`text-[15px] ${current ? 'font-medium' : ''}`}>{s.navLabel}</span>
                {note && (
                  <span className="text-[12px] leading-tight text-muted">
                    {done ? (
                      <span className="inline-flex items-center gap-1">
                        <Check aria-hidden className="size-3" /> Completed
                      </span>
                    ) : (
                      note
                    )}
                  </span>
                )}
              </span>
              {current && <span className="sr-only">(currently viewing)</span>}
            </a>
          </li>
        )
      })}
    </ol>
  )
}
