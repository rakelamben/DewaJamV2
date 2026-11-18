export type EsDomainCode =
  | "CUST_WATCH_ADVISOR"
  | "STAFF_POS_CROSSSELL"
  | "WAREHOUSE_QC_INBOUND"
  | "WAREHOUSE_STOCK_ANOMALY"
  | "MGR_KPI_DIAGNOSTIC"
  | "MGR_WORKFLOW_APPROVAL"

export type EsFactOption = {
  value: string
  label: string
}

export type EsFactDefinition = {
  fact_id: string
  domain_id: string
  kode: string
  nama: string
  pertanyaan: string | null
  tipe_nilai: "enum" | "number" | "boolean" | "text"
  sumber_fakta: "user_input" | "db_derived" | "inferred"
  opsi_nilai: EsFactOption[]
  urutan: number
  is_required: boolean
  is_active: boolean
}

export type EsRuleClause = {
  fact: string
  op: "==" | "!=" | ">=" | "<=" | ">" | "<" | "in" | "not_in"
  value: unknown
  weight: number
}

export type EsRuleRow = {
  rule_id: string
  domain_id: string
  kode: string
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
  created_at: string
  updated_at: string
}

export type EsDomainSummary = {
  domain_id: string
  kode: EsDomainCode
  nama: string
  deskripsi: string | null
  target_role: "customer" | "kasir" | "gudang" | "manager"
  entity_type: "product" | "transaction" | "purchase" | "kpi" | "workflow" | "general"
  is_active: boolean
  active_rules_count: number
  user_facts_count: number
}

export type EsReferenceOption = {
  id: string
  label: string
  sublabel?: string
  meta?: Record<string, unknown>
}

export type EsKnowledgeReference = {
  table: string
  id: string
  label: string
  kategori: string | null
}

export type EsDomainContext = {
  domain: EsDomainSummary
  facts: EsFactDefinition[]
  user_facts: EsFactDefinition[]
  db_facts_spec: EsFactDefinition[]
  inferred_facts_spec: EsFactDefinition[]
  rules: EsRuleRow[]
  reference_options: EsReferenceOption[]
  knowledge_references: EsKnowledgeReference[]
}

export type EsFiredRuleTrace = {
  rule_id?: string | null
  rule_code: string
  rule_name: string
  conclusion_type: string
  conclusion_code: string
  conclusion_title: string
  explanation: string
  cf_expert: number
  cf_premise: number
  cf_rule: number
  priority: number
  matched_clauses: Array<{
    fact: string
    op: string
    expected: unknown
    actual: unknown
    cf_user: number
    weight: number
  }>
  knowledge_source_table?: string | null
  knowledge_source_id?: string | null
}

export type EsMatchedProduct = {
  product_id: string
  sku: string
  nama: string
  kategori: string | null
  harga: number
  stok: number
  specs?: Record<string, unknown>
  match_score: number
  match_reasons: string[]
}

export type EsConsultationResult = {
  result_id?: string
  urutan: number
  conclusion_code: string
  conclusion_title: string
  explanation: string
  cf_combined: number
  confidence_level: "Sangat Tinggi" | "Tinggi" | "Sedang" | "Rendah"
  recommendation: Record<string, unknown>
  fired_rules: EsFiredRuleTrace[]
  matched_products: EsMatchedProduct[]
  decision?: "pending" | "accepted" | "rejected"
  decision_note?: string | null
  decided_at?: string | null
}

export type EsConsultationOutput = {
  consultation_id?: string | null
  domain: EsDomainCode
  domain_name: string
  actor_type: "personnel" | "customer" | "guest"
  reference_table: string | null
  reference_id: string | null
  user_facts: Record<string, unknown>
  db_facts: Record<string, unknown>
  inferred_facts: Record<string, { value: unknown; cf: number }>
  warnings: Array<{ code: string; message: string }>
  results: EsConsultationResult[]
  persisted: boolean
  workflow_request_id?: string | null
}
