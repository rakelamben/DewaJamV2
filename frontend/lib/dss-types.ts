export type DssScenarioCode = "RESTOCK" | "PROMO" | "SUPPLIER"

export type DssCriterion = {
  criteria_id: string
  kode: string
  nama: string
  satuan: string | null
  is_benefit: boolean
  urutan: number
  is_active: boolean
}

export type DssWeightSet = {
  weight_set_id: string
  scenario_id: string
  nama: string
  lambda_max: number | null
  ci: number | null
  cr: number
  status: "draft" | "active" | "archived"
  created_at: string
  activated_at: string | null
}

export type DssScenario = {
  scenario_id: string
  kode: DssScenarioCode
  nama: string
  deskripsi: string | null
  alternative_type: "product" | "supplier"
  criteria: DssCriterion[]
  active_weight_set: DssWeightSet | null
  default_params: Record<string, number>
}

export type DssResult = {
  result_id?: string
  id: string
  type: "product" | "supplier"
  label: string
  group_key: string | null
  ranking: number
  skor: number
  status: string
  input_values: Record<string, number>
  contributions: Record<string, number>
  recommendation: Record<string, unknown>
  decision?: "pending" | "accepted" | "rejected"
  meta?: Record<string, unknown>
}

export type DssRun = {
  run_id?: string
  scenario: DssScenarioCode
  weight_set: { id: string; cr: number }
  scope: Record<string, unknown>
  params: Record<string, unknown>
  warnings: Array<Record<string, unknown>>
  excluded: Array<{ id: string; label: string; reason: string }>
  results: DssResult[]
  persisted: boolean
  workflow_request_id?: string
}
