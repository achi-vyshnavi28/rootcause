// Typed client for the RootCause API (backend/api/main.py).

export interface Candidate {
  dimension: string
  segment: string
  value_a: number
  value_b: number
  change: number
  abnormal_change: number
  share_of_change: number
  query_id: string
}

export interface Report {
  type: string
  summary: string
  root_cause_explanation?: string
  next_checks?: string[]
  suggested_experiment?: string
  confidence?: string
  evidence?: {
    metric: string
    period_a: [string, string]
    period_b: [string, string]
    overall_change?: { value_a: number; value_b: number; delta: number; pct_change: number }
    top_candidates?: Candidate[]
  }
  unsupported_numbers?: unknown[]
}

export interface Query {
  query_id: string
  purpose: string
  sql_executed: string
  row_count: number
  duration_ms: number
}

export interface Run {
  run_id: string
  question: string
  dataset: string
  status: string
  report: Report
  queries?: Query[]
  usage?: { calls: number; cost_usd: number; latency_s: number }
  duration_s?: number
  cached?: boolean
}

export interface RunRow {
  run_id: string
  question: string
  dataset: string
  status: string
  created_at: string
  duration_s: number
}

export interface AuditCheck {
  intact: boolean
  entries: number
  problems: unknown[]
}

// local dev: Vite proxies /api; deployed: VITE_API_URL or VITE_API_HOST
const HOST = import.meta.env.VITE_API_HOST
const BASE = import.meta.env.VITE_API_URL ?? (HOST ? `https://${HOST}` : '/api')

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, init)
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(typeof body.detail === 'string' ? body.detail : `${res.status} ${res.statusText}`)
  }
  return res.json() as Promise<T>
}

export const api = {
  datasets: () => request<Record<string, string>>('/datasets'),
  ask: (question: string, dataset: string) =>
    request<Run>('/ask', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ question, dataset }) }),
  runs: () => request<RunRow[]>('/runs?limit=15'),
  run: (id: string) => request<Run>(`/runs/${encodeURIComponent(id)}`),
  audit: (id: string) => request<Query[]>(`/runs/${encodeURIComponent(id)}/audit`),
  verify: () => request<AuditCheck>('/audit/verify'),
}

// rates (cancellation rate, late share) read better as percentages
export const fmtMetric = (n: number, metric = '') =>
  /rate|share|pct|percent/i.test(metric) ? `${(n * 100).toFixed(2)}%` : fmt(n)

export const fmt = (n: number) => (Math.abs(n) >= 1000 ? n.toLocaleString('en-IN', { maximumFractionDigits: 0 }) : String(Math.round(n * 100) / 100))
