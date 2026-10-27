import { Info } from 'lucide-react'
import type { ReactNode } from 'react'

/** Small inline disclosure / prerequisite note. */
export function Notice({ children, className = '' }: { children: ReactNode; className?: string }) {
  return (
    <p className={`flex items-start gap-2 text-[15px] leading-relaxed text-muted ${className}`}>
      <Info aria-hidden className="mt-[3px] size-4 shrink-0" />
      <span>{children}</span>
    </p>
  )
}
