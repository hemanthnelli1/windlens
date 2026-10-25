import { useEffect, useMemo, useState } from 'react'
import { ActualForecastChart, ErrorChart } from './components/Charts'
import { Filters } from './components/Filters'
import { KpiCard } from './components/KpiCard'
import { EmptyState, ErrorState, LoadingState } from './components/State'
import { PeriodTable, VintageTable } from './components/Tables'
import { api } from './lib/api'
import { dateTime, mw, percent, signedMw } from './lib/format'
import type { Metadata, Overview, Quality, VintagesResponse } from './types'

type Tab = 'overview' | 'explorer' | 'vintages' | 'methodology'
const defaultDate = '2026-01-01'
const asApiCutoff = (value: string) => value ? new Date(value).toISOString() : undefined
const toInput = (value: string) => { const date = new Date(value); const local = new Date(date.getTime() - date.getTimezoneOffset() * 60_000); return local.toISOString().slice(0, 16) }

function App() {
  const [tab, setTab] = useState<Tab>('overview')
  const [deliveryDate, setDeliveryDate] = useState(defaultDate)
  const [cutoffInput, setCutoffInput] = useState('')
  const [vintage, setVintage] = useState<string | undefined>()
  const [overview, setOverview] = useState<Overview | null>(null)
  const [vintages, setVintages] = useState<VintagesResponse | null>(null)
  const [quality, setQuality] = useState<Quality | null>(null)
  const [metadata, setMetadata] = useState<Metadata | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const cutoff = useMemo(() => asApiCutoff(cutoffInput), [cutoffInput])

  useEffect(() => {
    let active = true
    setLoading(true); setError(null)
    Promise.all([api.overview(deliveryDate, cutoff, vintage), api.vintages(deliveryDate, cutoff), api.quality(deliveryDate), api.metadata()])
      .then(([nextOverview, nextVintages, nextQuality, nextMetadata]) => { if (active) { setOverview(nextOverview); setVintages(nextVintages); setQuality(nextQuality); setMetadata(nextMetadata); if (cutoff === undefined) setCutoffInput(toInput(nextOverview.publication_cutoff)) } })
      .catch((reason: unknown) => { if (active) setError(reason instanceof Error ? reason.message : 'An unknown error occurred') })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [deliveryDate, cutoff, vintage])

  const resetCutoff = () => { setCutoffInput(''); setVintage(undefined) }
  const inspectVintage = (published: string) => { setVintage(published); setTab('overview') }
  const selectedTitle = overview?.selection_mode === 'exact_vintage' ? `Exact publication: ${dateTime(overview.selected_vintage ?? '')}` : `Latest available at cutoff: ${overview ? dateTime(overview.publication_cutoff) : '—'}`

  return <div className="app-shell"><a className="skip-link" href="#main">Skip to content</a><aside className="sidebar"><div className="brand"><span className="brand-mark">W</span><div><strong>WindLens</strong><span>UK wind intelligence</span></div></div><nav aria-label="Primary navigation">{([['overview', 'Overview'], ['explorer', 'Forecast Explorer'], ['vintages', 'Vintage Analysis'], ['methodology', 'Methodology & Data Quality']] as [Tab, string][]).map(([id, label]) => <button key={id} className={tab === id ? 'nav-active' : ''} onClick={() => setTab(id)}>{label}</button>)}</nav><div className="sidebar-foot"><span className="live-dot" />BMRS source connected<br /><small>January 2026 scope</small></div></aside><main id="main"><header className="topbar"><div><p className="eyebrow">Energy trading analytics</p><h1>{tab === 'overview' ? 'Wind forecast control room' : tab === 'explorer' ? 'Forecast Explorer' : tab === 'vintages' ? 'Forecast Vintage Analysis' : 'Methodology & Data Quality'}</h1></div><div className="timezone">All timestamps displayed in Europe/London<br /><span>Stored and matched as UTC instants</span></div></header><Filters date={deliveryDate} cutoff={cutoffInput} onDate={(value) => { setDeliveryDate(value); setVintage(undefined) }} onCutoff={(value) => { setCutoffInput(value); setVintage(undefined) }} onReset={resetCutoff} />{loading ? <LoadingState /> : error ? <ErrorState message={error} /> : !overview ? <EmptyState title="No analysis returned" detail="Try another January 2026 delivery date." /> : <>{tab === 'overview' && <OverviewPage overview={overview} title={selectedTitle} />}{tab === 'explorer' && <ExplorerPage overview={overview} />}{tab === 'vintages' && <VintagePage response={vintages} inspect={inspectVintage} />}{tab === 'methodology' && <MethodologyPage quality={quality} metadata={metadata} />}</>}</main></div>
}

function OverviewPage({ overview, title }: { overview: Overview; title: string }) { const metrics = overview.metrics; return <><div className="context-bar"><span>Selection: <strong>{title}</strong></span><span>Data freshness: <strong>retrieved on request</strong></span></div><section className="kpis"><KpiCard label="Mean absolute error" value={mw(metrics.mae_mw)} hint={`${metrics.matched_samples} matched half-hours`} /><KpiCard label="RMSE" value={mw(metrics.rmse_mw)} hint="Sensitive to larger errors" /><KpiCard label="Mean bias" value={signedMw(metrics.bias_mw)} hint="Positive = forecast above actual" accent="amber" /><KpiCard label="Wind shortfall estimate" value={mw(metrics.mean_wind_shortfall_mw)} hint="Wind error only; not total procurement" accent="red" /></section>{overview.periods.length ? <section className="chart-grid"><ActualForecastChart periods={overview.periods} /><ErrorChart periods={overview.periods} /></section> : <EmptyState title="No matched observations at this cutoff" detail="There may be source gaps or no eligible forecast publications. Missing data has not been represented as zero." />}<section className="insight-row"><p><strong>WAPE: {percent(metrics.wape_percent)}</strong> Calculated only when matched actual wind generation sums above zero.</p><p>Forecast quality measures prediction accuracy, not energy cost or procurement savings.</p></section></> }

function ExplorerPage({ overview }: { overview: Overview }) { return <section className="panel"><div className="card-heading"><div><p className="eyebrow">Inspectable half-hourly records</p><h2>Actuals, forecast and error</h2></div><span className="unit-chip">{overview.metrics.matched_samples} matched / {overview.periods.length} periods</span></div><PeriodTable periods={overview.periods} /></section> }

function VintagePage({ response, inspect }: { response: VintagesResponse | null; inspect: (value: string) => void }) { return <section className="panel"><div className="card-heading"><div><p className="eyebrow">Decision-time assessment</p><h2>Publication vintages eligible at cutoff</h2></div></div><p className="prose">Only forecasts published on or before <strong>{response ? dateTime(response.decision_cutoff) : '—'}</strong> are listed. This is a configurable operational assumption, not an asserted market rule.</p><VintageTable vintages={response?.vintages ?? []} select={inspect} /></section> }

function MethodologyPage({ quality, metadata }: { quality: Quality | null; metadata: Metadata | null }) { return <div className="method-grid"><section className="panel"><p className="eyebrow">Data quality</p><h2>Retrieval and coverage</h2>{quality ? <dl className="quality-grid"><dt>Requested range</dt><dd>{quality.requested_range}</dd><dt>Last retrieval</dt><dd>{quality.retrieved_at ? dateTime(quality.retrieved_at) : 'Not yet retrieved'}</dd><dt>Missing actuals</dt><dd>{quality.missing_actual_observations}</dd><dt>Missing selected forecasts</dt><dd>{quality.missing_selected_forecast_observations}</dd><dt>Matched samples</dt><dd>{quality.matched_sample_count}</dd><dt>Duplicate source rows</dt><dd>{quality.actual_duplicates + quality.forecast_duplicates}</dd></dl> : <EmptyState title="No quality status" detail="Load an in-scope delivery date first." />}<p className="prose small">{quality?.deduplication_policy}</p></section><section className="panel"><p className="eyebrow">Methodology</p><h2>Boundaries and definitions</h2><div className="prose"><p>{metadata?.timezone_strategy}</p><p>{metadata?.default_cutoff_assumption}</p><p><strong>MAE</strong> is mean absolute forecast error. <strong>RMSE</strong> is the square root of mean squared error. <strong>Bias</strong> is forecast minus actual. MAPE is intentionally not shown because it can be unstable when actual wind is zero or near zero.</p><p>Wind shortfall is max(actual − forecast, 0) for wind only. It is not a calculation of total electricity procurement need because no demand data is used.</p><p>Sources: {metadata?.sources.map((source) => <a key={source.name} href={source.url} target="_blank" rel="noreferrer">{source.name}</a>)}</p></div></section></div> }

export default App
