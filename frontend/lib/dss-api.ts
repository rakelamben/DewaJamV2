import { ApiError } from "./api"
import type { DssRun, DssScenario } from "./dss-types"

const apiUrl = import.meta.env.VITE_API_URL ?? "http://localhost:8000"

async function request<T>(token: string, path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiUrl}${path}`, {
    ...init,
    headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json", ...init?.headers },
  })
  if (!response.ok) {
    let detail = "Permintaan DSS gagal."
    try { detail = ((await response.json()) as { detail?: string }).detail ?? detail } catch { /* ignore */ }
    throw new ApiError(detail, response.status)
  }
  return (await response.json()) as T
}

export function getDssScenarios(token: string) { return request<DssScenario[]>(token, "/api/dss/scenarios") }
export function getDssRuns(token: string, code: string) { return request<Array<Record<string, unknown>>>(token, `/api/dss/scenarios/${code}/runs`) }
export function getDssRun(token: string, id: string) { return request<DssRun>(token, `/api/dss/runs/${id}`) }
export function runDss(token: string, code: string, payload: { scope: Record<string, unknown>; params: Record<string, unknown>; persist: boolean }) {
  return request<DssRun>(token, `/api/dss/scenarios/${code}/runs`, { method: "POST", body: JSON.stringify(payload) })
}
export function decideDssResult(token: string, id: string, decision: "accepted" | "rejected", note: string | null) {
  return request<Record<string, unknown>>(token, `/api/dss/results/${id}/decision`, { method: "POST", body: JSON.stringify({ decision, note }) })
}
export function getDssWeights(token: string, code: string) { return request<{ weight_sets: Array<Record<string, unknown>> }>(token, `/api/dss/scenarios/${code}/weights`) }
export function createDssWeight(token: string, code: string, payload: { nama: string; pairs: Record<string, number> }) {
  return request<Record<string, unknown>>(token, `/api/dss/scenarios/${code}/weights`, { method: "POST", body: JSON.stringify(payload) })
}
export function activateDssWeight(token: string, id: string) { return request<Record<string, unknown>>(token, `/api/dss/weights/${id}/activate`, { method: "POST" }) }
