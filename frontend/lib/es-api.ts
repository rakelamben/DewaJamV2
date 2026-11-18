import { ApiError } from "./api"
import type {
  EsConsultationOutput,
  EsDomainCode,
  EsDomainContext,
  EsDomainSummary,
  EsFactDefinition,
  EsKnowledgeReference,
  EsRuleClause,
  EsRuleRow,
} from "./es-types"

const apiUrl = import.meta.env.VITE_API_URL ?? "http://localhost:8000"

async function request<T>(token: string | null, path: string, init?: RequestInit): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(init?.headers as Record<string, string> | undefined),
  }
  if (token) {
    headers.Authorization = `Bearer ${token}`
  }
  const response = await fetch(`${apiUrl}${path}`, {
    ...init,
    headers,
  })
  if (!response.ok) {
    let detail = "Permintaan Sistem Pakar gagal."
    try {
      detail = ((await response.json()) as { detail?: string }).detail ?? detail
    } catch {
      /* ignore */
    }
    throw new ApiError(detail, response.status)
  }
  return (await response.json()) as T
}

export function getEsDomains(token: string) {
  return request<EsDomainSummary[]>(token, "/api/es/domains")
}

export function getEsDomainContext(token: string, code: EsDomainCode) {
  return request<EsDomainContext>(token, `/api/es/domains/${code}`)
}

export function runEsConsultation(
  token: string,
  code: EsDomainCode,
  payload: {
    reference_id?: string | null
    facts: Record<string, unknown>
    cf_inputs?: Record<string, number>
    persist?: boolean
    create_workflow?: boolean
  }
) {
  return request<EsConsultationOutput>(token, `/api/es/domains/${code}/consult`, {
    method: "POST",
    body: JSON.stringify(payload),
  })
}

export function getEsConsultations(token: string, code: EsDomainCode) {
  return request<Array<Record<string, unknown>>>(token, `/api/es/domains/${code}/consultations`)
}

export function getEsConsultationDetail(token: string, consultationId: string) {
  return request<Record<string, unknown>>(token, `/api/es/consultations/${consultationId}`)
}

export function decideEsResult(
  token: string,
  resultId: string,
  decision: "accepted" | "rejected",
  note: string | null
) {
  return request<Record<string, unknown>>(token, `/api/es/results/${resultId}/decision`, {
    method: "POST",
    body: JSON.stringify({ decision, note }),
  })
}

export function getEsDomainRules(token: string, code: EsDomainCode) {
  return request<{
    domain: EsDomainSummary
    facts: EsFactDefinition[]
    rules: EsRuleRow[]
    knowledge_references: EsKnowledgeReference[]
  }>(token, `/api/es/domains/${code}/rules`)
}

export function createEsRule(
  token: string,
  code: EsDomainCode,
  payload: {
    kode: string
    nama: string
    kondisi: EsRuleClause[]
    jenis_konklusi: "intermediate_fact" | "final_conclusion"
    kesimpulan_kode: string
    kesimpulan_nilai?: string | null
    kesimpulan_judul: string
    penjelasan: string
    rekomendasi?: Record<string, unknown>
    cf_pakar: number
    prioritas?: number
    knowledge_source_table?: string | null
    knowledge_source_id?: string | null
    status?: "draft" | "active" | "archived"
  }
) {
  return request<EsRuleRow>(token, `/api/es/domains/${code}/rules`, {
    method: "POST",
    body: JSON.stringify(payload),
  })
}

export function updateEsRule(
  token: string,
  ruleId: string,
  payload: Partial<{
    nama: string
    kondisi: EsRuleClause[]
    jenis_konklusi: "intermediate_fact" | "final_conclusion"
    kesimpulan_kode: string
    kesimpulan_nilai: string | null
    kesimpulan_judul: string
    penjelasan: string
    rekomendasi: Record<string, unknown>
    cf_pakar: number
    prioritas: number
    knowledge_source_table: string | null
    knowledge_source_id: string | null
    status: "draft" | "active" | "archived"
  }>
) {
  return request<EsRuleRow>(token, `/api/es/rules/${ruleId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  })
}

export function getCustomerWatchAdvisorSchema(token?: string | null) {
  return request<{
    domain: EsDomainSummary
    questions: EsFactDefinition[]
  }>(token ?? null, "/api/customer/es/advisor")
}

export function runCustomerWatchAdvisor(
  token: string | null,
  payload: {
    facts: Record<string, unknown>
    cf_inputs?: Record<string, number>
    persist?: boolean
  }
) {
  return request<EsConsultationOutput>(token, "/api/customer/es/advisor", {
    method: "POST",
    body: JSON.stringify(payload),
  })
}
