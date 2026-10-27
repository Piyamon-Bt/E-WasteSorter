import { useState } from 'react'
import { useAssessment } from '../../state/AssessmentContext'
import { useNavigation } from '../../state/Navigation'
import { buildIdentity, emptyFields, NONE, type Fields } from '../../lib/identity'
import { Button } from '../ui/Button'
import { Notice } from '../ui/Notice'

export function IdentityForm() {
  const { state, actions } = useAssessment()
  const { goToSection } = useNavigation()
  const [picked, setPicked] = useState<string>(NONE)
  const [fields, setFields] = useState<Fields>(emptyFields)
  const suggestion = state.analysis.data?.identity

  if (state.functional.status !== 'complete' || !suggestion) {
    return (
      <div className="space-y-5">
        <Notice>Confirm the model after the functional checks.</Notice>
        <Button variant="secondary" onClick={() => goToSection('functionality')}>
          Go to Functional checks
        </Button>
      </div>
    )
  }

  function pick(value: string) {
    setPicked(value)
    const c = value === NONE ? null : suggestion!.candidates[Number(value)]
    setFields(c ? { ...fields, brand: c.brand ?? '', model: c.model ?? '' } : fields)
  }

  function confirm() {
    actions.setIdentity(buildIdentity(suggestion!, picked, fields))
    goToSection('location')
  }

  function unknown() {
    actions.setIdentity({ status: 'unknown', brand: null, model: null, variant: null, storage: null, ram: null, evidence_verified: false })
    goToSection('location')
  }

  const current = state.identity
  const input = (key: keyof Fields, label: string, placeholder = '') => (
    <label className="block text-[14px] text-muted">
      {label}
      <input
        value={fields[key]}
        placeholder={placeholder}
        maxLength={80}
        onChange={(e) => setFields({ ...fields, [key]: e.target.value })}
        className="mt-1 min-h-11 w-full rounded-md border border-line px-3 text-[15px] text-ink"
      />
    </label>
  )

  return (
    <div className="space-y-8">
      <div>
        <h3 className="text-[17px] font-medium text-ink">What the photos suggest</h3>
        <p className="mt-1 text-[15px] text-muted">
          Evidence strength: <span className="text-ink">{suggestion.evidence_strength}</span>. {suggestion.notes}
        </p>
        {suggestion.visible_specs.length > 0 && (
          <p className="mt-1 text-[15px] text-muted">Visible labels: {suggestion.visible_specs.join('; ')}</p>
        )}
      </div>

      <fieldset>
        <legend className="mb-2 text-[16px] font-medium text-ink">Possible models</legend>
        <div className="space-y-2">
          {suggestion.candidates.map((c, i) => (
            <label key={i} className="flex min-h-11 items-start gap-3 text-[15px]">
              <input type="radio" name="identity-candidate" className="mt-1.5" checked={picked === String(i)} onChange={() => pick(String(i))} />
              <span>
                <span className="text-ink">{[c.brand, c.model].filter(Boolean).join(' ') || 'Unnamed candidate'}</span>
                <span className="block text-[14px] text-muted">{c.evidence}</span>
              </span>
            </label>
          ))}
          <label className="flex min-h-11 items-center gap-3 text-[15px]">
            <input type="radio" name="identity-candidate" checked={picked === NONE} onChange={() => pick(NONE)} />
            None of these / Unsure
          </label>
        </div>
        <p className="mt-2 text-[14px] text-muted">Choosing a candidate does not prove the model.</p>
      </fieldset>

      <div className="grid gap-4 sm:grid-cols-2">
        {input('brand', 'Brand')}
        {input('model', 'Model')}
        {input('variant', 'Variant (optional)', 'e.g. Pro, 2021')}
        {input('storage', 'Storage (optional)', 'e.g. 128 GB')}
        {input('ram', 'RAM (optional)', 'e.g. 8 GB')}
      </div>

      <div className="flex flex-wrap gap-3">
        <Button onClick={confirm} disabled={!fields.brand.trim() || !fields.model.trim()}>
          Confirm these details
        </Button>
        <Button variant="secondary" onClick={unknown}>
          I don’t know the model
        </Button>
      </div>
      <p className="text-[14px] text-muted">
        With an unknown model you still get findings and local services, but no model-specific prices.
      </p>
      {current && (
        <p className="text-[15px] text-ink" aria-live="polite">
          Recorded:{' '}
          {current.status === 'unknown'
            ? 'Unknown model.'
            : `${[current.brand, current.model, current.variant, current.storage, current.ram].filter(Boolean).join(' ')} (${
                current.evidence_verified ? 'matches strong photo evidence' : 'user-confirmed, not verified from photos'
              }).`}
        </p>
      )}
    </div>
  )
}
