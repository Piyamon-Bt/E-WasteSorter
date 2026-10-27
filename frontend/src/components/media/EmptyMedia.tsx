interface EmptyMediaProps {
  aspectRatio: string
  label?: string
}

/** Quiet, dimension-stable placeholder for media that hasn't been supplied yet. */
export function EmptyMedia({ aspectRatio, label }: EmptyMediaProps) {
  return (
    <div
      aria-hidden
      style={{ aspectRatio }}
      className="flex w-full items-end justify-start rounded-sm border border-line p-4"
    >
      {label && <span className="text-[12px] tracking-wide text-neutral-400">{label}</span>}
    </div>
  )
}
