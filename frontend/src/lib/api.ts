import type { Metadata, Overview, Quality, VintagesResponse } from '../types'

const baseUrl = (import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000').replace(/\/$/, '')

async function request<T>(path: string): Promise<T> {
  const response = await fetch(`${baseUrl}${path}`)
  if (!response.ok) {
    const payload = await response.json().catch(() => null) as { detail?: string } | null
    throw new Error(payload?.detail ?? `Request failed (${response.status})`)
  }
  return response.json() as Promise<T>
}

export const api = {
  overview: (date: string, cutoff?: string, vintage?: string) => request<Overview>(`/api/overview?${new URLSearchParams({ delivery_date: date, ...(cutoff ? { cutoff } : {}), ...(vintage ? { vintage } : {}) })}`),
  vintages: (date: string, cutoff?: string) => request<VintagesResponse>(`/api/forecast-vintages?${new URLSearchParams({ delivery_date: date, ...(cutoff ? { cutoff } : {}) })}`),
  quality: (date: string) => request<Quality>(`/api/data-quality?${new URLSearchParams({ delivery_date: date })}`),
  metadata: () => request<Metadata>('/api/metadata'),
}
