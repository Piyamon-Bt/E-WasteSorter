import * as Dialog from '@radix-ui/react-dialog'
import { Menu, X } from 'lucide-react'
import { useRef, useState } from 'react'
import { sectionById } from '../../content/sections'
import { useNavigation } from '../../state/Navigation'
import type { SectionId } from '../../types/assessment'
import { ModeBadge } from './ModeBanner'
import { NavList } from './NavList'
import { StartOverDialog } from './StartOverDialog'
import { Wordmark } from './Wordmark'

/** Compact top header with an accessible navigation drawer (<1024px). */
export function MobileNavigation() {
  const { activeSection, goToSection } = useNavigation()
  const [open, setOpen] = useState(false)
  const pending = useRef<SectionId | null>(null)
  const current = sectionById[activeSection]

  return (
    <header
      data-print="hide"
      className="fixed inset-x-0 top-0 z-40 flex h-[var(--header-h)] items-center justify-between border-b border-line bg-white px-4 lg:hidden"
    >
      <Wordmark />
      <p className="truncate px-3 text-[13px] text-muted" aria-live="off">
        <span className="tabular-nums">{current.number}</span>
        <span className="mx-1.5" aria-hidden>
          ·
        </span>
        {current.navLabel}
      </p>
      <Dialog.Root open={open} onOpenChange={setOpen}>
        <Dialog.Trigger asChild>
          <button
            type="button"
            className="-mr-2 inline-flex size-11 items-center justify-center rounded-md text-ink"
            aria-label="Open navigation"
          >
            <Menu aria-hidden className="size-5" />
          </button>
        </Dialog.Trigger>
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 z-50 bg-black/20" />
          <Dialog.Content
            className="fixed inset-y-0 right-0 z-50 flex w-[min(320px,85vw)] flex-col border-l border-line bg-white px-5 py-5"
            onCloseAutoFocus={(e) => {
              // Navigate after the drawer has closed and scroll lock is released.
              const target = pending.current
              pending.current = null
              if (target) {
                e.preventDefault()
                goToSection(target)
              }
            }}
          >
            <div className="flex items-center justify-between">
              <Dialog.Title className="text-[15px] font-medium text-ink">Sections</Dialog.Title>
              <Dialog.Close asChild>
                <button
                  type="button"
                  className="-mr-2 inline-flex size-11 items-center justify-center rounded-md"
                  aria-label="Close navigation"
                >
                  <X aria-hidden className="size-5" />
                </button>
              </Dialog.Close>
            </div>
            <Dialog.Description className="sr-only">
              Jump to any stage of the assessment.
            </Dialog.Description>
            <nav aria-label="Assessment sections" className="mt-6 -ml-4">
              <NavList
                onNavigate={(id) => {
                  pending.current = id
                  setOpen(false)
                }}
              />
            </nav>
            <div className="mt-auto flex flex-col items-start gap-3">
              <ModeBadge />
              <StartOverDialog
                onReset={() => {
                  pending.current = 'device'
                  setOpen(false)
                }}
              />
            </div>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </header>
  )
}
