import * as Dialog from '@radix-ui/react-dialog'
import { RotateCcw } from 'lucide-react'
import { useState, type ReactNode } from 'react'
import { useAssessment } from '../../state/AssessmentContext'
import { DEFAULT_DEVICE } from '../../state/assessmentReducer'
import { useNavigation } from '../../state/Navigation'
import { Button } from '../ui/Button'

interface StartOverDialogProps {
  trigger?: ReactNode
  /** Replaces the default "scroll to Upload" behaviour after clearing. */
  onReset?(): void
}

/** Confirms before clearing, so an in-progress assessment is never reset by accident. */
export function StartOverDialog({ trigger, onReset }: StartOverDialogProps) {
  const { state, actions } = useAssessment()
  const { goToSection } = useNavigation()
  const [open, setOpen] = useState(false)
  const hasData = state.deviceType !== DEFAULT_DEVICE || state.photos.length > 0 || state.analysis.status !== 'idle'

  const confirm = () => {
    actions.reset()
    setOpen(false)
    if (onReset) onReset()
    else goToSection('device')
  }

  return (
    <Dialog.Root open={open} onOpenChange={setOpen}>
      <Dialog.Trigger asChild>
        {trigger ?? (
          <button
            type="button"
            disabled={!hasData}
            className="inline-flex min-h-11 items-center gap-2 text-[14px] text-muted hover:text-ink disabled:opacity-40"
          >
            <RotateCcw aria-hidden className="size-4" /> Start Over
          </button>
        )}
      </Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-black/20" />
        <Dialog.Content className="fixed top-1/2 left-1/2 z-50 w-[calc(100%-32px)] max-w-sm -translate-x-1/2 -translate-y-1/2 rounded-lg border border-line bg-white p-6 shadow-sm">
          <Dialog.Title className="text-[18px] font-medium text-ink">Start a new assessment?</Dialog.Title>
          <Dialog.Description className="mt-2 text-[15px] text-muted">
            This clears your photos, observations, answers and results. The project usage ledger is kept. This cannot be undone.
          </Dialog.Description>
          <div className="mt-6 flex flex-wrap justify-end gap-2">
            <Dialog.Close asChild>
              <Button variant="secondary">Cancel</Button>
            </Dialog.Close>
            <Button onClick={confirm}>Clear and start over</Button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}
