import { useId } from 'react'

export interface ChoiceOption<T extends string> {
  value: T
  label: string
}

interface ChoiceGroupProps<T extends string> {
  legend: string
  hint?: string
  name: string
  value: T | null
  options: ChoiceOption<T>[]
  onChange(value: T): void
  error?: string
  id?: string
}

/** Native radio group styled as compact segmented choices. */
export function ChoiceGroup<T extends string>({
  legend,
  hint,
  name,
  value,
  options,
  onChange,
  error,
  id,
}: ChoiceGroupProps<T>) {
  const uid = useId()
  const hintId = hint ? `${uid}-hint` : undefined
  const errorId = error ? `${uid}-error` : undefined
  return (
    <fieldset
      id={id}
      aria-describedby={[hintId, errorId].filter(Boolean).join(' ') || undefined}
      aria-invalid={error ? true : undefined}
      className="min-w-0"
    >
      <legend className="mb-1 text-[16px] font-medium text-ink">{legend}</legend>
      {hint && (
        <p id={hintId} className="mb-3 text-[15px] text-muted">
          {hint}
        </p>
      )}
      <div className={`flex flex-wrap gap-2 ${hint ? '' : 'mt-3'}`}>
        {options.map((opt) => {
          const checked = value === opt.value
          return (
            <label key={opt.value} className="relative">
              <input
                type="radio"
                name={name}
                value={opt.value}
                checked={checked}
                onChange={() => onChange(opt.value)}
                className="peer sr-only"
              />
              <span
                className={`flex min-h-11 cursor-pointer items-center rounded-full border px-4 text-[15px] transition-colors peer-focus-visible:outline-2 peer-focus-visible:outline-offset-2 peer-focus-visible:outline-accent ${
                  checked
                    ? 'border-ink bg-ink text-white'
                    : 'border-line bg-white text-ink hover:border-neutral-400'
                }`}
              >
                {opt.label}
              </span>
            </label>
          )
        })}
      </div>
      {error && (
        <p id={errorId} className="mt-2 text-[15px] text-danger">
          {error}
        </p>
      )}
    </fieldset>
  )
}
