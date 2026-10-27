import { AlertTriangle, Loader2 } from 'lucide-react'
import { answerLabels, checkStatusLabels } from '../../content/labels'
import { useAssessment } from '../../state/AssessmentContext'
import { useNavigation } from '../../state/Navigation'
import type { AccessoryCheck, CheckAnswer } from '../../types/api'
import { Button } from '../ui/Button'
import { ChoiceGroup } from '../ui/ChoiceGroup'
import { Notice } from '../ui/Notice'

const accessoryOptions: { value: AccessoryCheck; label: string }[] = [
  { value: 'known_working', label: 'One I know works' },
  { value: 'unverified', label: 'Only the original / not sure' },
]

const answerOptions = (Object.keys(answerLabels) as CheckAnswer[]).map((value) => ({ value, label: answerLabels[value] }))

export function FunctionalityForm() {
  const { state, actions } = useAssessment()
  const { goToSection } = useNavigation()
  const { plan, functional } = state

  if (plan.status === 'processing') {
    return (
      <p className="flex items-center gap-3 text-[16px]">
        <Loader2 aria-hidden className="size-4 animate-spin motion-reduce:animate-none" /> Preparing checks…
      </p>
    )
  }
  if (plan.status !== 'complete' || !plan.data) {
    return (
      <div className="space-y-5">
        <Notice>Functional checks open after you finish reviewing the observations.</Notice>
        <Button variant="secondary" onClick={() => goToSection('review')}>
          Go to Review
        </Button>
      </div>
    )
  }

  const { safety, checks, guidance } = plan.data
  if (safety.blocked) {
    return (
      <div className="space-y-6">
        <div role="alert" className="rounded-lg border border-danger p-5">
          <p className="flex items-center gap-2 text-[17px] font-medium text-danger">
            <AlertTriangle aria-hidden className="size-5" /> Do not power on or charge this device
          </p>
          <ul className="mt-3 space-y-1 text-[15px] text-ink">
            {safety.risks.map((r) => (
              <li key={r.observation_id}>
                {r.part}: {r.explanation}
              </li>
            ))}
          </ul>
          <ul className="mt-4 space-y-1 text-[15px] text-ink">
            {safety.guidance.map((g) => (
              <li key={g} className="flex gap-2">
                <span aria-hidden>–</span>
                {g}
              </li>
            ))}
          </ul>
        </div>
        <p className="text-[15px] text-muted">
          Functional checks are skipped. The assessment continues with physical findings and professional-inspection
          guidance.
        </p>
        <Button onClick={() => goToSection('identity')} disabled={functional.status !== 'complete'}>
          Continue to model
        </Button>
      </div>
    )
  }

  const powerFailed = state.checkAnswers.power_on?.answer === 'fail'

  return (
    <div className="space-y-10">
      <ul className="space-y-1 text-[15px] text-muted">
        {guidance.map((g) => (
          <li key={g} className="flex gap-2">
            <span aria-hidden>–</span>
            {g}
          </li>
        ))}
      </ul>

      <div className="space-y-8">
        {checks.map((c) => {
          const unavailable = c.depends_on_power && powerFailed
          const answer = state.checkAnswers[c.id]
          return (
            <div key={c.id} className={unavailable ? 'opacity-50' : ''}>
              {unavailable ? (
                <>
                  <p className="text-[16px] font-medium text-ink">{c.label}</p>
                  <p className="text-[15px] text-muted">Unavailable: the device did not power on.</p>
                </>
              ) : (
                <>
                  <ChoiceGroup
                    legend={c.label}
                    hint={c.instructions}
                    name={`check-${c.id}`}
                    value={answer?.answer ?? null}
                    options={answerOptions}
                    onChange={(a) => actions.answerCheck(c.id, a)}
                  />
                  {(answer?.answer === 'fail' || answer?.answer === 'unsure') && (
                    <label className="mt-3 block text-[14px] text-muted">
                      Describe what happened (optional)
                      <input
                        value={answer.note}
                        maxLength={500}
                        onChange={(e) => actions.setCheckNote(c.id, e.target.value)}
                        className="mt-1 min-h-11 w-full rounded-md border border-line px-3 text-[15px] text-ink"
                      />
                    </label>
                  )}
                  {c.id === 'charging' && answer?.answer === 'fail' && (
                    <div className="mt-4">
                      <ChoiceGroup
                        legend="Which charger and cable did you test with?"
                        hint="If you used one you know works, a replacement charger is ruled out. Otherwise, try a known-working one before buying anything."
                        name="charging-accessory"
                        value={answer.accessory_check ?? null}
                        options={accessoryOptions}
                        onChange={(v) => actions.setAccessoryCheck(c.id, v)}
                      />
                    </div>
                  )}
                </>
              )}
            </div>
          )
        })}
      </div>

      <div className="space-y-3">
        <Button onClick={actions.submitChecks} disabled={functional.status === 'processing'}>
          {functional.status === 'complete' ? 'Update results' : 'Save check results'}
        </Button>
        <p className="text-[14px] text-muted">You can save with unanswered checks; the results stay conditional.</p>
        {functional.status === 'failed' && (
          <p role="alert" className="text-[15px] text-danger">
            {functional.error}
          </p>
        )}
      </div>

      {functional.status === 'complete' && functional.data && (
        <div className="space-y-4">
          <h3 className="text-[17px] font-medium text-ink">Recorded results (user-reported)</h3>
          <ul className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-1 text-[15px]">
            {functional.data.outcomes.map((o) => (
              <li key={o.check_id} className="contents">
                <span className="text-muted">{o.label}</span>
                <span className="text-ink">{checkStatusLabels[o.status]}</span>
              </li>
            ))}
          </ul>
          {functional.data.clarifications.length > 0 && (
            <div role="alert" className="rounded-md border border-line p-4">
              <p className="text-[15px] font-medium text-ink">Please clarify</p>
              <ul className="mt-2 space-y-1 text-[15px] text-ink">
                {functional.data.clarifications.map((c) => (
                  <li key={c}>{c}</li>
                ))}
              </ul>
            </div>
          )}
          {functional.data.conditional_findings.length > 0 && (
            <ul className="space-y-1 text-[15px] text-muted">
              {functional.data.conditional_findings.map((f) => (
                <li key={f}>{f}</li>
              ))}
            </ul>
          )}
          <p className="text-[14px] text-muted">{functional.data.disclaimer}</p>
          <Button onClick={() => goToSection('identity')}>Continue to model</Button>
        </div>
      )}
    </div>
  )
}
