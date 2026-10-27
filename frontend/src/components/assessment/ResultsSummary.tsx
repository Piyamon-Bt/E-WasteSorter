import { Check, Download, ExternalLink, Loader2, Printer } from 'lucide-react'
import { useState } from 'react'
import { viewLabel } from '../../content/devices'
import {
  actionLabels,
  checkStatusLabels,
  formatDate,
  formatMoney,
  kindLabels,
  kindOrder,
  priceTypeLabels,
  serviceCategoryLabels,
} from '../../content/labels'
import { effectiveObservation, hasOpenRisk, isWithdrawn } from '../../lib/observations'
import { useAssessment } from '../../state/AssessmentContext'
import { useNavigation } from '../../state/Navigation'
import type { ActionOption, ProviderIssue, Ranking } from '../../types/api'
import { Button } from '../ui/Button'
import { Notice } from '../ui/Notice'

function Heading({ children }: { children: string }) {
  return <h3 className="text-[19px] font-medium text-ink">{children}</h3>
}

function Issues({ issues }: { issues: ProviderIssue[] }) {
  if (!issues.length) return null
  return (
    <ul role="alert" className="space-y-1 text-[15px] text-danger">
      {issues.map((i) => (
        <li key={i.step + i.code}>
          {i.message} <span className="text-muted">({i.code.replace('_', ' ')})</span>
        </li>
      ))}
    </ul>
  )
}

function Progress({ label, done }: { label: string; done: boolean }) {
  return (
    <li className="flex items-center gap-3 text-[16px]">
      {done ? (
        <Check aria-hidden className="size-4" />
      ) : (
        <Loader2 aria-hidden className="size-4 animate-spin motion-reduce:animate-none" />
      )}
      <span className={done ? 'text-ink' : 'text-muted'}>{label}</span>
    </li>
  )
}

const financialStatusLabels = {
  complete: 'Evidence complete',
  conditional: 'Conditional estimate',
  insufficient: 'Insufficient price data',
} as const

function OptionCard({ option }: { option: ActionOption }) {
  const isSale = option.action === 'resell_as_is' || option.action === 'repair_then_resell'
  return (
    <li className="rounded-lg border border-line p-5 print-break-avoid">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h4 className="text-[17px] font-medium text-ink">{option.title}</h4>
        <span className="rounded-full border border-line px-2.5 py-0.5 text-[12px] text-muted">
          {financialStatusLabels[option.financial_status]}
        </span>
      </div>
      <p className="mt-1 text-[15px] text-ink">{option.summary}</p>
      {option.sale_channels.length > 0 && (
        <div className="mt-3">
          <p className="text-[13px] tracking-[0.06em] text-muted uppercase">Sale channels (kept separate)</p>
          <ul className="mt-1 space-y-0.5 text-[14px] text-ink">
            {option.sale_channels.map((c) => (
              <li key={c.price_type + c.device_state}>
                {priceTypeLabels[c.price_type]}, {c.device_state.replaceAll('_', ' ')}: {formatMoney(c.range)}{' '}
                <span className="text-muted">
                  ({c.records} record{c.records === 1 ? '' : 's'}){c.used_for_calculation ? ' · used below' : ''}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
      <dl className="mt-3 grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-[14px]">
        {isSale && (
          <>
            <dt className="text-muted">Gross sale</dt>
            <dd className="text-ink">{formatMoney(option.gross_sale)}</dd>
          </>
        )}
        {option.action.startsWith('repair') && (
          <>
            <dt className="text-muted">Repair cost</dt>
            <dd className="text-ink">
              {formatMoney(option.repair_cost)}
              {option.repair_cost && !option.repair_cost_complete && <span className="text-muted"> (incomplete)</span>}
            </dd>
          </>
        )}
        {isSale ? (
          <>
            <dt className="text-muted">Net proceeds</dt>
            <dd className="font-medium text-ink">{formatMoney(option.net_proceeds)}</dd>
          </>
        ) : option.action !== 'recycle' ? (
          <>
            <dt className="text-muted">Avoided cost (not cash)</dt>
            <dd className="font-medium text-ink">{formatMoney(option.avoided_cost)}</dd>
          </>
        ) : null}
      </dl>
      <p className="mt-2 text-[13px] text-muted">{option.financial_note}</p>
      {[
        ['Before you do this', option.prerequisites],
        ['Tradeoffs', option.tradeoffs],
        ['Uncertainty', option.uncertainty],
      ].map(([title, items]) =>
        (items as string[]).length ? (
          <div key={title as string} className="mt-3">
            <p className="text-[13px] tracking-[0.06em] text-muted uppercase">{title as string}</p>
            <ul className="mt-1 space-y-1 text-[14px] text-ink">
              {(items as string[]).map((x) => (
                <li key={x}>– {x}</li>
              ))}
            </ul>
          </div>
        ) : null,
      )}
    </li>
  )
}

function RankingList({ title, ranking }: { title: string; ranking: Ranking }) {
  return (
    <div className="min-w-0">
      <h4 className="text-[17px] font-medium text-ink">{title}</h4>
      {ranking.order.length ? (
        <ol className="mt-2 list-decimal space-y-1 pl-5 text-[15px] text-ink">
          {ranking.order.map((a) => (
            <li key={a}>{actionLabels[a]}</li>
          ))}
        </ol>
      ) : (
        <p className="mt-2 text-[15px] text-muted">
          {ranking.conditional.length ? 'No definitive ranking: the evidence is incomplete.' : 'Not enough price evidence to rank.'}
        </p>
      )}
      {ranking.conditional.length > 0 && (
        <div className="mt-2">
          <p className="text-[14px] text-muted">Conditional (incomplete evidence):</p>
          <ol className="list-decimal space-y-1 pl-5 text-[15px] text-ink">
            {ranking.conditional.map((a) => (
              <li key={a}>{actionLabels[a]}</li>
            ))}
          </ol>
        </div>
      )}
      {!ranking.complete && <p className="mt-2 text-[14px] text-muted">Incomplete ranking.</p>}
      <ul className="mt-2 space-y-1 text-[13px] text-muted">
        {ranking.explanation.map((e) => (
          <li key={e}>{e}</li>
        ))}
      </ul>
    </div>
  )
}

export function ResultsSummary() {
  const { state, actions } = useAssessment()
  const { goToSection } = useNavigation()
  const [downloadError, setDownloadError] = useState<string | null>(null)
  const { research, analysis, functional, identity } = state

  if (research.status === 'idle' || !analysis.data) {
    return (
      <div className="space-y-5">
        <Notice>Results appear after you choose a market and start the search.</Notice>
        <Button variant="secondary" onClick={() => goToSection('location')}>
          Go to Location
        </Button>
      </div>
    )
  }

  const { prices, services, recommendation } = research
  const reviews = state.reviews
  const followUps = state.followUps
  const observations = [...analysis.data.observations].sort((a, b) => kindOrder.indexOf(a.kind) - kindOrder.indexOf(b.kind))
  const simulated = analysis.data.source === 'simulated' || prices?.source === 'simulated' || services?.source === 'simulated'

  async function download() {
    setDownloadError(null)
    try {
      await actions.downloadReport()
    } catch (err) {
      setDownloadError(err instanceof Error ? err.message : 'The report could not be created.')
    }
  }

  return (
    <div className="space-y-14">
      {simulated && (
        <p className="rounded-md border border-ink px-4 py-3 text-[15px] font-medium text-ink">
          Demo mode — simulated results. Findings, prices and services below are not real evidence.
        </p>
      )}

      {research.status === 'processing' && (
        <ol className="space-y-3" aria-label="Search progress">
          <Progress label="Searching local prices" done={!!prices} />
          <Progress label="Finding nearby services" done={!!services} />
          <Progress label="Comparing options" done={false} />
        </ol>
      )}
      {research.error && (
        <p role="alert" className="text-[15px] text-danger">
          Some results could not be loaded: {research.error}
        </p>
      )}

      {/* 1. Physical findings first */}
      <section className="space-y-4" aria-label="Physical findings">
        <Heading>Physical findings</Heading>
        <ul className="space-y-3">
          {observations.map((o) => {
            const history = followUps[o.id] ?? []
            const f = history[history.length - 1]
            const shown = effectiveObservation(o, history)
            const response = reviews[o.id]?.response
            return (
              <li key={o.id} className={`text-[15px] ${isWithdrawn(history) ? 'text-muted line-through' : 'text-ink'}`}>
                <span className="font-medium">{kindLabels[shown.kind]}:</span> {shown.part} — {shown.description}{' '}
                <span className="text-[13px] text-muted">
                  ({shown.views.map((v) => viewLabel(state.deviceType, v)).join(', ') || 'no photo'}; uncertainty {shown.uncertainty}
                  {response ? `; you: ${response}` : ''}
                  {f ? `; latest re-check: ${f.outcome.replace('_', ' ')}` : ''}
                  {hasOpenRisk(o, history) && shown.kind !== 'suspected_safety_risk' ? '; earlier suspected risk unresolved' : ''})
                </span>
              </li>
            )
          })}
        </ul>
      </section>

      {/* 2. Functional results */}
      <section className="space-y-4" aria-label="Functional results">
        <Heading>Functional results (user-reported)</Heading>
        {functional.data ? (
          <>
            <ul className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-1 text-[15px]">
              {functional.data.outcomes.map((o) => (
                <li key={o.check_id} className="contents">
                  <span className="text-muted">{o.label}</span>
                  <span className="text-ink">{checkStatusLabels[o.status]}</span>
                </li>
              ))}
            </ul>
            <p className="text-[14px] text-muted">{functional.data.disclaimer}</p>
          </>
        ) : (
          <p className="text-[15px] text-muted">Not recorded.</p>
        )}
        {identity && (
          <p className="text-[15px] text-ink">
            Model:{' '}
            {identity.status === 'unknown' ? (
              'Unknown'
            ) : (
              <>
                {[identity.brand, identity.model, identity.variant, identity.storage, identity.ram].filter(Boolean).join(' ')}{' '}
                <span className="text-muted">
                  ({identity.evidence_verified ? 'matches strong photo evidence' : 'user-confirmed, not verified from photos'})
                </span>
              </>
            )}
          </p>
        )}
      </section>

      {/* 3. Prices */}
      <section className="space-y-4" aria-label="Price evidence">
        <Heading>Local price evidence</Heading>
        {!prices ? (
          <p className="text-[15px] text-muted">{research.status === 'processing' ? 'Searching…' : 'Not available.'}</p>
        ) : (
          <>
            <p className="text-[14px] text-muted">
              {prices.country} · {prices.identity_label} · retrieved {formatDate(prices.retrieved_at)} · {prices.source}
            </p>
            <Issues issues={prices.issues} />
            {prices.notes.map((n) => (
              <p key={n} className="text-[15px] text-ink">
                {n}
              </p>
            ))}
            {prices.records.length > 0 && (
              <div className="overflow-x-auto">
                <table className="w-full min-w-[640px] text-left text-[14px]">
                  <thead className="text-muted">
                    <tr>
                      <th className="py-2 pr-3 font-normal">Type</th>
                      <th className="py-2 pr-3 font-normal">Item</th>
                      <th className="py-2 pr-3 font-normal">Price</th>
                      <th className="py-2 pr-3 font-normal">Match</th>
                      <th className="py-2 font-normal">Source</th>
                    </tr>
                  </thead>
                  <tbody>
                    {prices.records.map((r, i) => (
                      <tr key={i} className="border-t border-line align-top">
                        <td className="py-2 pr-3">{priceTypeLabels[r.price_type]}</td>
                        <td className="py-2 pr-3">
                          {r.item}
                          <span className="block text-[12px] text-muted">
                            {r.device_state.replaceAll('_', ' ')}
                            {r.part_quality !== 'not_applicable' ? ` · ${r.part_quality} part` : ''}
                          </span>
                        </td>
                        <td className="py-2 pr-3 whitespace-nowrap">
                          {formatMoney({ min: r.amount_min, max: r.amount_max, currency: r.currency })}
                        </td>
                        <td className="py-2 pr-3">
                          {r.match_level}
                          <span className="block text-[12px] text-muted">{r.matching_conditions}</span>
                        </td>
                        <td className="py-2">
                          <a href={r.source_url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 underline">
                            {r.simulated ? 'Simulated source' : r.source_title || 'Source'} <ExternalLink aria-hidden className="size-3" />
                          </a>
                          <span className="block text-[12px] text-muted">
                            {formatDate(r.retrieved_at)}. {r.limitations}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            {prices.channels.some((c) => c.status === 'insufficient_data') && (
              <p className="text-[14px] text-muted">
                Insufficient data:{' '}
                {prices.channels.filter((c) => c.status === 'insufficient_data').map((c) => priceTypeLabels[c.price_type]).join(', ')}.
              </p>
            )}
            {prices.repair_scenarios.length > 0 && (
              <div>
                <p className="text-[15px] font-medium text-ink">Possible repair scenarios (not diagnoses)</p>
                <ul className="mt-1 space-y-1 text-[14px] text-ink">
                  {prices.repair_scenarios.map((s) => (
                    <li key={s.id}>
                      {s.title} <span className="text-muted">— may address: {s.needs.join('; ')}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </>
        )}
      </section>

      {/* 4. Services */}
      <section className="space-y-4" aria-label="Local services">
        <Heading>Nearby services</Heading>
        {!services ? (
          <p className="text-[15px] text-muted">{research.status === 'processing' ? 'Searching…' : 'Not available.'}</p>
        ) : (
          <>
            <Issues issues={services.issues} />
            {services.services.length === 0 && !services.issues.length && (
              <p className="text-[15px] text-muted">No matching services found in {services.area_label}.</p>
            )}
            <ul className="space-y-4">
              {services.services.map((s, i) => (
                <li key={s.place_id ?? i} className="text-[15px]">
                  <p className="font-medium text-ink">
                    {s.name} <span className="text-[13px] font-normal text-muted">· {serviceCategoryLabels[s.category]}</span>
                  </p>
                  <p className="text-ink">{s.address}</p>
                  <p className="text-[14px] text-muted">
                    {[s.phone, s.distance_km != null ? `${s.distance_km} km straight-line` : null].filter(Boolean).join(' · ')}
                  </p>
                  <p className="text-[13px] text-muted">{s.relevance}</p>
                  <p className="flex flex-wrap gap-x-4 text-[14px]">
                    {s.maps_url && (
                      <a href={s.maps_url} target="_blank" rel="noopener noreferrer" className="underline">
                        Open in Google Maps
                      </a>
                    )}
                    {s.website && (
                      <a href={s.website} target="_blank" rel="noopener noreferrer" className="underline">
                        Website
                      </a>
                    )}
                  </p>
                </li>
              ))}
            </ul>
            {services.notes.map((n) => (
              <p key={n} className="text-[14px] text-muted">
                {n}
              </p>
            ))}
            {services.attribution && <p className="text-[13px] text-muted">{services.attribution}</p>}
            <p className="text-[13px] text-muted">The app never contacts, books or sends photos to these businesses.</p>
          </>
        )}
      </section>

      {/* 5. Options and rankings */}
      <section className="space-y-6" aria-label="Options and rankings">
        <Heading>Options</Heading>
        {!recommendation ? (
          <p className="text-[15px] text-muted">{research.status === 'processing' ? 'Comparing…' : 'Not available.'}</p>
        ) : (
          <>
            <ul className="space-y-1 text-[15px] text-ink">
              {recommendation.conditional_findings.map((c) => (
                <li key={c}>– {c}</li>
              ))}
            </ul>
            <ul className="space-y-4">
              {recommendation.options.map((o) => (
                <OptionCard key={o.action} option={o} />
              ))}
            </ul>
            <div className="grid gap-8 sm:grid-cols-2">
              <RankingList title="Financial value" ranking={recommendation.financial_ranking} />
              <RankingList title="Resource use / life extension" ranking={recommendation.resource_ranking} />
            </div>
            {recommendation.rankings_differ && <p className="text-[15px] text-ink">{recommendation.rankings_differ}</p>}
            {recommendation.disposal_guidance.length > 0 && (
              <div>
                <p className="text-[15px] font-medium text-ink">General disposal guidance</p>
                <p className="text-[13px] text-muted">Not a recommendation; shown for when you decide a device has reached end of life.</p>
                <ul className="mt-1 space-y-1 text-[14px] text-ink">
                  {recommendation.disposal_guidance.map((g) => (
                    <li key={g}>– {g}</li>
                  ))}
                </ul>
              </div>
            )}
            <ul className="space-y-1 text-[13px] text-muted">
              {recommendation.disclaimers.map((d) => (
                <li key={d}>{d}</li>
              ))}
            </ul>
          </>
        )}
      </section>

      <div data-print="hide" className="flex flex-wrap gap-3">
        <Button onClick={() => void download()} disabled={research.status === 'processing'}>
          <Download aria-hidden className="size-4" /> Download report (Markdown)
        </Button>
        <Button variant="secondary" onClick={() => window.print()}>
          <Printer aria-hidden className="size-4" /> Print / Save as PDF
        </Button>
        <Button variant="secondary" onClick={actions.startResearch} disabled={research.status === 'processing'}>
          Search again
        </Button>
      </div>
      {downloadError && (
        <p role="alert" className="text-[15px] text-danger">
          {downloadError}
        </p>
      )}
      <p className="text-[14px] text-muted">
        Nothing is saved. Download the report before closing or refreshing this page.
      </p>
    </div>
  )
}
