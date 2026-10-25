import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import App from '../App'
import { EmptyState } from '../components/State'

const fetchMock = vi.fn()
global.fetch = fetchMock

const overview = { delivery_date: '2026-01-01', selection_mode: 'latest_available_at_cutoff', publication_cutoff: '2025-12-31T12:00:00Z', selected_vintage: null, metrics: { matched_samples: 1, mae_mw: 100, rmse_mw: 100, bias_mw: -100, wape_percent: 2, mean_wind_shortfall_mw: 100 }, periods: [{ start_time: '2026-01-01T00:00:00Z', actual_mw: 1000, forecast_mw: 900, publish_time: '2025-12-31T12:00:00Z', error_mw: -100, absolute_error_mw: 100, wind_shortfall_mw: 100 }], quality: {} }

describe('App', () => {
  beforeEach(() => { fetchMock.mockReset() })
  it('shows a loading state while requests are outstanding', () => { fetchMock.mockImplementation(() => new Promise(() => {})); render(<App />); expect(screen.getByRole('status')).toHaveTextContent('Retrieving BMRS data') })
  it('renders dashboard data from the API', async () => { fetchMock.mockResolvedValue({ ok: true, json: async () => overview }); render(<App />); expect(await screen.findByText('Wind forecast control room')).toBeInTheDocument(); expect((await screen.findAllByText('100 MW')).length).toBeGreaterThan(0) })
  it('renders an empty state without converting gaps to zero', () => { render(<EmptyState title="No matched observations" detail="Missing observations remain visible." />); expect(screen.getByText('No matched observations')).toBeInTheDocument(); expect(screen.getByText('Missing observations remain visible.')).toBeInTheDocument() })
  it('shows an API error state', async () => { fetchMock.mockResolvedValue({ ok: false, json: async () => ({ detail: 'upstream unavailable' }) }); render(<App />); expect(await screen.findByRole('alert')).toHaveTextContent('upstream unavailable') })
})
