import type { ReactNode } from 'react'

export function KpiCard({ label, value, hint, accent = 'cyan' }: { label: string; value: ReactNode; hint: string; accent?: 'cyan' | 'amber' | 'red' }) {
  return <article className={`kpi-card ${accent}`}><p>{label}</p><strong>{value}</strong><span>{hint}</span></article>
}
