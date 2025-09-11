export const API_BASE = import.meta.env.VITE_API_BASE || '/api'

export async function get<T = any>(path: string, opts?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path.startsWith('/') ? path : `/${path}`}`, {
    ...opts,
    headers: { 'Content-Type': 'application/json', ...(opts?.headers || {}) }
  })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export type PulseVitals = {
  discipline_score: number
  patience_index: number
  conviction_rate: number
  profit_efficiency: number
  current_pnl: number
}

