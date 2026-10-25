export type Metrics = {
  matched_samples: number
  mae_mw: number | null
  rmse_mw: number | null
  bias_mw: number | null
  wape_percent: number | null
  mean_wind_shortfall_mw: number | null
}

export type Period = {
  start_time: string
  actual_mw: number | null
  forecast_mw: number | null
  publish_time: string | null
  error_mw: number | null
  absolute_error_mw: number | null
  wind_shortfall_mw: number | null
}

export type Overview = {
  delivery_date: string
  selection_mode: 'latest_available_at_cutoff' | 'exact_vintage'
  publication_cutoff: string
  selected_vintage: string | null
  metrics: Metrics
  periods: Period[]
  quality: Record<string, number>
}

export type Vintage = Metrics & { publish_time: string; available_at_cutoff: boolean }
export type VintagesResponse = { delivery_date: string; decision_cutoff: string; vintages: Vintage[] }
export type Quality = {
  delivery_date: string
  requested_range: string
  retrieved_at: string | null
  actual_records: number
  selected_forecast_records: number
  missing_actual_observations: number
  missing_selected_forecast_observations: number
  matched_sample_count: number
  actual_raw_records: number
  forecast_raw_records: number
  actual_duplicates: number
  forecast_duplicates: number
  deduplication_policy: string
}

export type Metadata = { timezone_strategy: string; default_cutoff_assumption: string; sources: { name: string; url: string }[] }
