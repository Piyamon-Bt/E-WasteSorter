import { useRef, type ReactNode } from 'react'
import { ACCEPT_ATTR } from '../../lib/photos'
import { Button } from './Button'

interface FilePickButtonProps {
  children: ReactNode
  onFiles(files: File[]): void
  multiple?: boolean
  disabled?: boolean
  variant?: 'primary' | 'secondary' | 'quiet'
  label?: string
  className?: string
}

/** A button that opens the file chooser for photos. */
export function FilePickButton({ children, onFiles, multiple, disabled, variant = 'secondary', label, className }: FilePickButtonProps) {
  const input = useRef<HTMLInputElement>(null)
  return (
    <>
      <Button variant={variant} disabled={disabled} aria-label={label} className={className} onClick={() => input.current?.click()}>
        {children}
      </Button>
      <input
        ref={input}
        type="file"
        accept={ACCEPT_ATTR}
        multiple={multiple}
        className="sr-only"
        tabIndex={-1}
        aria-hidden
        onChange={(e) => {
          onFiles(Array.from(e.target.files ?? []))
          e.target.value = ''
        }}
      />
    </>
  )
}
