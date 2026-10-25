import type { Period, Vintage } from '../types'
import { dateTime, mw, signedMw } from '../lib/format'
import { EmptyState } from './State'

export function PeriodTable({ periods }: { periods: Period[] }) {
  if (!periods.length) return <EmptyState title="No delivery observations" detail="The source returned no actual or selected forecast timestamps for this window." />
  return <div className="table-wrap"><table><thead><tr><th>Delivery period</th><th>Actual</th><th>Forecast</th><th>Error</th><th>Absolute error</th><th>Published</th></tr></thead><tbody>{periods.map((period) => <tr key={period.start_time}><td>{dateTime(period.start_time)}</td><td>{mw(period.actual_mw)}</td><td>{mw(period.forecast_mw)}</td><td className={period.error_mw !== null && period.error_mw > 0 ? 'positive' : 'negative'}>{signedMw(period.error_mw)}</td><td>{mw(period.absolute_error_mw)}</td><td>{period.publish_time ? dateTime(period.publish_time) : '—'}</td></tr>)}</tbody></table></div>
}

export function VintageTable({ vintages, select }: { vintages: Vintage[]; select: (value: string) => void }) {
  if (!vintages.length) return <EmptyState title="No eligible forecast vintages" detail="No publication for this date was available at the current decision cutoff." />
  return <div className="table-wrap"><table><thead><tr><th>Published</th><th>Matched</th><th>MAE</th><th>RMSE</th><th>Bias</th><th /></tr></thead><tbody>{vintages.map((vintage) => <tr key={vintage.publish_time}><td>{dateTime(vintage.publish_time)}</td><td>{vintage.matched_samples}</td><td>{mw(vintage.mae_mw)}</td><td>{mw(vintage.rmse_mw)}</td><td className={(vintage.bias_mw ?? 0) > 0 ? 'positive' : 'negative'}>{signedMw(vintage.bias_mw)}</td><td><button className="link-button" onClick={() => select(vintage.publish_time)}>Inspect</button></td></tr>)}</tbody></table></div>
}
