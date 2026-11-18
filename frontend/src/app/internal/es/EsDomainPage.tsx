import { useEffect, useState } from "react"
import { Link, useParams } from "react-router"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { useAuth } from "../../../auth/AuthContext"
import {
  decideEsResult,
  getEsConsultationDetail,
  getEsConsultations,
  getEsDomainContext,
  runEsConsultation,
} from "../../../../lib/es-api"
import type {
  EsConsultationOutput,
  EsConsultationResult,
  EsDomainCode,
  EsDomainContext,
  EsFactDefinition,
} from "../../../../lib/es-types"
import { toast } from "sonner"

const currency = new Intl.NumberFormat("id-ID", {
  style: "currency",
  currency: "IDR",
  maximumFractionDigits: 0,
})

const userCfOptions = [
  { value: "1", label: "Sangat Yakin (CF 1.0)" },
  { value: "0.85", label: "Yakin (CF 0.85)" },
  { value: "0.7", label: "Cukup Yakin (CF 0.70)" },
  { value: "0.5", label: "Ragu-ragu (CF 0.50)" },
]

function formatFactValue(val: unknown): string {
  if (val === null || val === undefined || val === "") return "-"
  if (typeof val === "boolean") return val ? "Ya" : "Tidak"
  if (typeof val === "number") return Number.isInteger(val) ? String(val) : val.toFixed(2)
  if (typeof val === "object") return JSON.stringify(val)
  return String(val)
}

export default function EsDomainPage() {
  const { domainCode } = useParams()
  const code = (domainCode?.toUpperCase() ?? "") as EsDomainCode
  const { session, profile } = useAuth()

  const [context, setContext] = useState<EsDomainContext | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  const [referenceId, setReferenceId] = useState<string>("")
  const [factValues, setFactValues] = useState<Record<string, unknown>>({})
  const [cfInputs, setCfInputs] = useState<Record<string, string>>({})
  const [createWorkflow, setCreateWorkflow] = useState(false)

  const [consultation, setConsultation] = useState<EsConsultationOutput | null>(null)
  const [history, setHistory] = useState<Array<Record<string, unknown>>>([])
  const [decisionNotes, setDecisionNotes] = useState<Record<string, string>>({})

  const canManageRules = profile?.role === "admin" || profile?.role === "manager"

  async function loadAll() {
    if (!session || !code) {
      setLoading(false)
      return
    }
    setLoading(true)
    setError(null)
    try {
      const [ctx, hist] = await Promise.all([
        getEsDomainContext(session.access_token, code),
        getEsConsultations(session.access_token, code),
      ])
      setContext(ctx)
      setHistory(hist)

      const initialFacts: Record<string, unknown> = {}
      const initialCfs: Record<string, string> = {}
      for (const fact of ctx.user_facts) {
        if (fact.tipe_nilai === "enum" && fact.opsi_nilai.length > 0) {
          initialFacts[fact.kode] = fact.opsi_nilai[0].value
        } else if (fact.tipe_nilai === "boolean") {
          initialFacts[fact.kode] = false
        } else if (fact.tipe_nilai === "number") {
          initialFacts[fact.kode] = 0
        } else {
          initialFacts[fact.kode] = ""
        }
        initialCfs[fact.kode] = "1"
      }
      setFactValues(initialFacts)
      setCfInputs(initialCfs)
      if (ctx.reference_options.length > 0) {
        setReferenceId(ctx.reference_options[0].id)
      } else {
        setReferenceId("")
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Gagal memuat konteks domain Sistem Pakar."
      setError(msg)
      toast.error(msg)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadAll()
  }, [session, code])

  async function handleRun(persist: boolean) {
    if (!session || !context) return
    setSubmitting(true)
    try {
      const parsedFacts: Record<string, unknown> = {}
      for (const fact of context.user_facts) {
        const raw = factValues[fact.kode]
        if (fact.tipe_nilai === "number") {
          parsedFacts[fact.kode] = Number(raw ?? 0)
        } else if (fact.tipe_nilai === "boolean") {
          parsedFacts[fact.kode] = Boolean(raw)
        } else {
          parsedFacts[fact.kode] = raw
        }
      }
      const parsedCfs: Record<string, number> = {}
      for (const [k, v] of Object.entries(cfInputs)) {
        parsedCfs[k] = Number(v || 1)
      }

      const output = await runEsConsultation(session.access_token, code, {
        reference_id: referenceId || null,
        facts: parsedFacts,
        cf_inputs: parsedCfs,
        persist,
        create_workflow: persist && createWorkflow,
      })
      setConsultation(output)
      toast.success(
        persist
          ? "Sesi konsultasi pakar berhasil dijalankan dan disimpan."
          : "Simulasi evaluasi pakar selesai."
      )
      if (persist) {
        const updatedHistory = await getEsConsultations(session.access_token, code)
        setHistory(updatedHistory)
      }
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Gagal menjalankan mesin inferensi.")
    } finally {
      setSubmitting(false)
    }
  }

  async function handleLoadConsultation(consultationId: string) {
    if (!session) return
    setSubmitting(true)
    try {
      const detail = await getEsConsultationDetail(session.access_token, consultationId)
      const rawResults = (detail.results as Array<Record<string, unknown>> | undefined) ?? []
      const mappedResults: EsConsultationResult[] = rawResults.map((row) => ({
        result_id: String(row.result_id ?? ""),
        urutan: Number(row.ranking ?? 1),
        conclusion_code: String(row.kesimpulan_kode ?? ""),
        conclusion_title: String(row.kesimpulan_judul ?? ""),
        explanation: String(row.ringkasan_diagnosis ?? ""),
        cf_combined: Number(row.cf_kombinasi ?? 0),
        confidence_level: (row.tingkat_keyakinan as EsConsultationResult["confidence_level"]) ?? "Sedang",
        recommendation: (row.rekomendasi as Record<string, unknown>) ?? {},
        fired_rules: (row.matched_rules as EsConsultationResult["fired_rules"]) ?? [],
        matched_products: (row.matched_products as EsConsultationResult["matched_products"]) ?? [],
        decision: (row.decision as EsConsultationResult["decision"]) ?? "pending",
        decision_note: (row.decision_note as string | null) ?? null,
        decided_at: (row.decided_at as string | null) ?? null,
      }))
      setConsultation({
        consultation_id: String(detail.consultation_id),
        domain: code,
        domain_name: context?.domain.nama ?? code,
        actor_type: (detail.actor_type as "personnel" | "customer" | "guest") ?? "personnel",
        reference_table: (detail.reference_table as string | null) ?? null,
        reference_id: (detail.reference_id as string | null) ?? null,
        user_facts: (detail.user_facts as Record<string, unknown>) ?? {},
        db_facts: (detail.db_facts as Record<string, unknown>) ?? {},
        inferred_facts:
          (detail.inferred_facts as Record<string, { value: unknown; cf: number }>) ?? {},
        warnings: (detail.warnings as Array<{ code: string; message: string }>) ?? [],
        results: mappedResults,
        persisted: true,
        workflow_request_id: (detail.workflow_request_id as string | null) ?? null,
      })
      toast.success("Riwayat konsultasi berhasil dimuat.")
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Gagal memuat detail riwayat konsultasi.")
    } finally {
      setSubmitting(false)
    }
  }

  async function handleDecide(resultId: string, decision: "accepted" | "rejected") {
    if (!session) return
    const note = (decisionNotes[resultId] ?? "").trim()
    if (decision === "rejected" && !note) {
      toast.error("Catatan alasan wajib diisi saat menolak rekomendasi pakar.")
      return
    }
    try {
      await decideEsResult(session.access_token, resultId, decision, note || null)
      toast.success(
        decision === "accepted"
          ? "Rekomendasi pakar diterima."
          : "Rekomendasi pakar ditolak dengan catatan."
      )
      if (consultation?.consultation_id) {
        await handleLoadConsultation(consultation.consultation_id)
      }
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Gagal menyimpan keputusan.")
    }
  }

  function renderFactInput(fact: EsFactDefinition) {
    const inputId = `fact-input-${fact.kode}`
    const cfId = `fact-cf-${fact.kode}`
    const currentVal = factValues[fact.kode]

    return (
      <div
        key={fact.kode}
        className="grid gap-3 rounded-lg border bg-card p-4"
      >
        <div className="flex flex-wrap items-start justify-between gap-2">
          <label htmlFor={inputId} className="text-sm font-medium leading-snug">
            <span className="mr-2 font-mono text-xs text-muted-foreground">[{fact.kode}]</span>
            {fact.pertanyaan || fact.nama}
          </label>
          <Badge variant="outline" className="font-mono text-[11px]">
            {fact.tipe_nilai}
          </Badge>
        </div>

        <div className="grid gap-3 md:grid-cols-3">
          <div className="md:col-span-2">
            {fact.tipe_nilai === "enum" ? (
              <select
                id={inputId}
                className="h-10 w-full rounded-md border bg-background px-3 text-sm"
                value={String(currentVal ?? "")}
                onChange={(e) =>
                  setFactValues((prev) => ({ ...prev, [fact.kode]: e.target.value }))
                }
              >
                {fact.opsi_nilai.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            ) : fact.tipe_nilai === "boolean" ? (
              <select
                id={inputId}
                className="h-10 w-full rounded-md border bg-background px-3 text-sm"
                value={currentVal ? "true" : "false"}
                onChange={(e) =>
                  setFactValues((prev) => ({
                    ...prev,
                    [fact.kode]: e.target.value === "true",
                  }))
                }
              >
                <option value="false">Tidak (False)</option>
                <option value="true">Ya (True)</option>
              </select>
            ) : fact.tipe_nilai === "number" ? (
              <Input
                id={inputId}
                type="number"
                step="any"
                className="h-10"
                value={String(currentVal ?? 0)}
                onChange={(e) =>
                  setFactValues((prev) => ({ ...prev, [fact.kode]: e.target.value }))
                }
              />
            ) : (
              <Input
                id={inputId}
                type="text"
                className="h-10"
                value={String(currentVal ?? "")}
                onChange={(e) =>
                  setFactValues((prev) => ({ ...prev, [fact.kode]: e.target.value }))
                }
              />
            )}
          </div>

          <div>
            <label htmlFor={cfId} className="mb-1 block text-xs text-muted-foreground">
              Tingkat Keyakinan Observasi
            </label>
            <select
              id={cfId}
              className="h-10 w-full rounded-md border bg-background px-2.5 text-xs"
              value={cfInputs[fact.kode] ?? "1"}
              onChange={(e) =>
                setCfInputs((prev) => ({ ...prev, [fact.kode]: e.target.value }))
              }
            >
              {userCfOptions.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>
    )
  }

  return (
    <main className="grid gap-6 p-4 md:p-6">
      <header className="flex flex-wrap items-start justify-between gap-4 border-b pb-5">
        <div>
          <Link
            to="/internal/es"
            className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
          >
            Kembali ke Pusat Sistem Pakar
          </Link>
          <p className="mt-2 font-mono text-xs uppercase tracking-wider text-muted-foreground">
            Domain Kode: {code}
          </p>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight">
            {context?.domain.nama ?? "Memuat Domain Sistem Pakar..."}
          </h1>
          <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
            {context?.domain.deskripsi ??
              "Formulir observasi fakta lapangan dan mesin inferensi Forward Chaining."}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Button
            type="button"
            variant="outline"
            onClick={() => void loadAll()}
            disabled={loading || submitting}
          >
            Muat Ulang Data
          </Button>
          {canManageRules && (
            <Link to={`/internal/es/${code}/rules`}>
              <Button type="button" variant="secondary">
                Kelola Basis Aturan ({context?.rules.length ?? 0} Rule)
              </Button>
            </Link>
          )}
        </div>
      </header>

      {loading ? (
        <section aria-label="Memuat kuesioner pakar" className="grid gap-4">
          <Card>
            <CardContent className="grid gap-4 p-6">
              <div className="h-6 w-64 animate-pulse rounded bg-muted" />
              <div className="h-20 w-full animate-pulse rounded bg-muted" />
              <div className="h-20 w-full animate-pulse rounded bg-muted" />
            </CardContent>
          </Card>
        </section>
      ) : error || !context ? (
        <section aria-live="polite">
          <Card className="border-destructive/40 bg-destructive/5">
            <CardHeader>
              <CardTitle className="text-base text-destructive">
                Domain Sistem Pakar Tidak Dapat Dimuat
              </CardTitle>
            </CardHeader>
            <CardContent className="flex flex-wrap items-center justify-between gap-4 text-sm">
              <p className="text-muted-foreground">{error ?? "Domain tidak ditemukan."}</p>
              <Button type="button" variant="outline" onClick={() => void loadAll()}>
                Coba Lagi
              </Button>
            </CardContent>
          </Card>
        </section>
      ) : (
        <div className="grid gap-6 lg:grid-cols-3">
          <section className="grid content-start gap-6 lg:col-span-2" aria-label="Formulir konsultasi pakar">
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">
                  1. Konteks Referensi & Fakta Observasi Lapangan
                </CardTitle>
                <p className="text-sm text-muted-foreground">
                  Pilih objek operasional yang sedang diperiksa (jika tersedia) agar sistem mengekstrak fakta
                  basis data secara otomatis, lalu lengkapi hasil observasi di bawah ini.
                </p>
              </CardHeader>
              <CardContent className="grid gap-4">
                {context.reference_options.length > 0 && (
                  <div className="rounded-lg border bg-muted/25 p-4">
                    <label
                      htmlFor="es-reference-select"
                      className="block text-sm font-medium"
                    >
                      Objek Referensi Operasional ({context.domain.entity_type.toUpperCase()})
                    </label>
                    <p className="mt-0.5 text-xs text-muted-foreground">
                      Data stok, spesifikasi jam, nilai PO, atau realisasi KPI dari objek ini akan ditarik otomatis ke memori kerja mesin pakar.
                    </p>
                    <select
                      id="es-reference-select"
                      className="mt-2 h-10 w-full rounded-md border bg-background px-3 text-sm"
                      value={referenceId}
                      onChange={(e) => setReferenceId(e.target.value)}
                    >
                      <option value="">Tanpa objek spesifik (evaluasi manual)</option>
                      {context.reference_options.map((opt) => (
                        <option key={opt.id} value={opt.id}>
                          {opt.label} {opt.sublabel ? `(${opt.sublabel})` : ""}
                        </option>
                      ))}
                    </select>
                  </div>
                )}

                {context.user_facts.length === 0 ? (
                  <p className="rounded-md border p-4 text-sm text-muted-foreground">
                    Domain ini belum memiliki daftar pertanyaan observasi pengguna.
                  </p>
                ) : (
                  <div className="grid gap-3">
                    {context.user_facts.map((fact) => renderFactInput(fact))}
                  </div>
                )}

                <div className="rounded-lg border bg-muted/20 p-3.5">
                  <label
                    htmlFor="es-create-workflow"
                    className="flex items-start gap-2.5 text-sm"
                  >
                    <input
                      id="es-create-workflow"
                      type="checkbox"
                      className="mt-1 size-4"
                      checked={createWorkflow}
                      onChange={(e) => setCreateWorkflow(e.target.checked)}
                    />
                    <span>
                      <strong className="font-medium">
                        Ajukan eskalasi otomatis ke Workflow Approval
                      </strong>
                      <span className="block text-xs text-muted-foreground">
                        Jika diaktifkan saat menyimpan diagnosis, sistem akan membuat tiket persetujuan di modul OAS Workflow untuk ditindaklanjuti Manajer.
                      </span>
                    </span>
                  </label>
                </div>

                <div className="flex flex-wrap items-center gap-3 pt-2">
                  <Button
                    type="button"
                    onClick={() => void handleRun(false)}
                    disabled={submitting}
                    className="min-h-10"
                  >
                    {submitting ? "Mengevaluasi..." : "Jalankan Simulasi Diagnosis"}
                  </Button>
                  <Button
                    type="button"
                    variant="secondary"
                    onClick={() => void handleRun(true)}
                    disabled={submitting}
                    className="min-h-10"
                  >
                    Simpan Hasil Konsultasi
                  </Button>
                </div>
              </CardContent>
            </Card>

            {consultation && (
              <section aria-live="polite" className="grid gap-5">
                <Card className="border-foreground/30">
                  <CardHeader className="gap-2 border-b bg-muted/20">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <span className="font-mono text-xs uppercase text-muted-foreground">
                        Hasil Inferensi Forward Chaining
                      </span>
                      <div className="flex flex-wrap gap-1.5">
                        <Badge variant={consultation.persisted ? "default" : "secondary"}>
                          {consultation.persisted ? "Tersimpan di Audit Log" : "Mode Simulasi"}
                        </Badge>
                        {consultation.workflow_request_id && (
                          <Badge variant="destructive">Tiket Workflow Dibuat</Badge>
                        )}
                      </div>
                    </div>
                    <CardTitle className="text-xl">
                      2. Kesimpulan Pakar, Certainty Factor & Jejak Aturan
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="grid gap-5 pt-5">
                    {Object.keys(consultation.db_facts).length > 0 && (
                      <div className="rounded-md border bg-muted/25 p-3.5">
                        <h3 className="font-mono text-xs font-semibold uppercase text-muted-foreground">
                          Fakta Otomatis dari Basis Data (DB Derived Facts)
                        </h3>
                        <dl className="mt-2 grid grid-cols-2 gap-2 text-xs sm:grid-cols-3">
                          {Object.entries(consultation.db_facts).map(([k, v]) => (
                            <div key={k} className="rounded border bg-background p-2">
                              <dt className="font-mono text-[11px] text-muted-foreground">{k}</dt>
                              <dd className="mt-0.5 font-medium">{formatFactValue(v)}</dd>
                            </div>
                          ))}
                        </dl>
                      </div>
                    )}

                    {Object.keys(consultation.inferred_facts).length > 0 && (
                      <div className="rounded-md border bg-muted/25 p-3.5">
                        <h3 className="font-mono text-xs font-semibold uppercase text-muted-foreground">
                          Fakta Antara Hasil Inferensi Tahap 1 (Intermediate Inferred Facts)
                        </h3>
                        <dl className="mt-2 grid grid-cols-1 gap-2 text-xs sm:grid-cols-2">
                          {Object.entries(consultation.inferred_facts).map(([k, item]) => (
                            <div key={k} className="rounded border bg-background p-2.5">
                              <dt className="font-mono text-[11px] text-muted-foreground">{k}</dt>
                              <dd className="mt-0.5 font-semibold">
                                {formatFactValue(item.value)}{" "}
                                <span className="font-mono text-xs font-normal text-muted-foreground">
                                  (CF {(item.cf * 100).toFixed(1)}%)
                                </span>
                              </dd>
                            </div>
                          ))}
                        </dl>
                      </div>
                    )}

                    {consultation.warnings.length > 0 && (
                      <div className="grid gap-2">
                        {consultation.warnings.map((w, idx) => (
                          <div
                            key={idx}
                            className="rounded-md border border-amber-400/60 bg-amber-500/10 p-3 text-sm"
                          >
                            <p className="font-mono text-xs font-semibold">{w.code}</p>
                            <p className="mt-0.5">{w.message}</p>
                          </div>
                        ))}
                      </div>
                    )}

                    {consultation.results.length === 0 ? (
                      <div className="rounded-lg border p-6 text-center text-sm text-muted-foreground">
                        Tidak ada aturan kesimpulan akhir yang terpenuhi untuk kombinasi fakta ini.
                        Coba sesuaikan input fakta observasi di atas.
                      </div>
                    ) : (
                      <div className="grid gap-4">
                        {consultation.results.map((res) => (
                          <article
                            key={res.conclusion_code}
                            className="grid gap-4 rounded-lg border bg-card p-4 shadow-2xs"
                          >
                            <div className="flex flex-wrap items-start justify-between gap-3 border-b pb-3">
                              <div>
                                <div className="flex flex-wrap items-center gap-2">
                                  <Badge variant="default">Prioritas #{res.urutan}</Badge>
                                  <span className="font-mono text-xs text-muted-foreground">
                                    {res.conclusion_code}
                                  </span>
                                </div>
                                <h3 className="mt-1.5 text-lg font-semibold">
                                  {res.conclusion_title}
                                </h3>
                              </div>
                              <div className="text-right">
                                <p className="font-mono text-xl font-bold">
                                  {(res.cf_combined * 100).toFixed(1)}%
                                </p>
                                <Badge variant="outline" className="mt-0.5">
                                  Keyakinan: {res.confidence_level} (CF {res.cf_combined.toFixed(3)})
                                </Badge>
                              </div>
                            </div>

                            <p className="text-sm leading-relaxed">{res.explanation}</p>

                            {Object.keys(res.recommendation).length > 0 && (
                              <div className="rounded-md border bg-muted/30 p-3.5 text-sm">
                                <h4 className="font-mono text-xs font-semibold uppercase text-muted-foreground">
                                  Rekomendasi Tindakan & SOP Operasional
                                </h4>
                                <dl className="mt-2 grid gap-2 sm:grid-cols-2">
                                  {Object.entries(res.recommendation).map(([rk, rv]) => (
                                    <div key={rk}>
                                      <dt className="font-mono text-xs text-muted-foreground">
                                        {rk}
                                      </dt>
                                      <dd className="font-medium">
                                        {Array.isArray(rv) ? rv.join(", ") : formatFactValue(rv)}
                                      </dd>
                                    </div>
                                  ))}
                                </dl>
                              </div>
                            )}

                            {res.matched_products.length > 0 && (
                              <div className="grid gap-2.5">
                                <h4 className="font-mono text-xs font-semibold uppercase text-muted-foreground">
                                  Produk / Aksesoris Kompatibel di Stok Aktif ({res.matched_products.length})
                                </h4>
                                <div className="grid gap-2.5 sm:grid-cols-2">
                                  {res.matched_products.map((prod) => (
                                    <div
                                      key={prod.product_id}
                                      className="flex flex-col justify-between rounded-md border p-3 text-sm"
                                    >
                                      <div>
                                        <div className="flex items-center justify-between gap-2">
                                          <span className="font-mono text-xs text-muted-foreground">
                                            {prod.sku}
                                          </span>
                                          <Badge variant="secondary">Stok: {prod.stok}</Badge>
                                        </div>
                                        <p className="mt-1 font-medium">{prod.nama}</p>
                                        <p className="mt-0.5 text-xs text-muted-foreground">
                                          {prod.match_reasons.join(" · ")}
                                        </p>
                                      </div>
                                      <p className="mt-2 font-mono text-sm font-semibold">
                                        {currency.format(prod.harga)}
                                      </p>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}

                            <details className="rounded-md border bg-muted/15 p-3 text-xs">
                              <summary className="font-mono font-medium">
                                Lihat Jejak Inferensi ({res.fired_rules.length} Aturan Terpicu)
                              </summary>
                              <div className="mt-3 grid gap-2.5">
                                {res.fired_rules.map((tr) => (
                                  <div
                                    key={tr.rule_code}
                                    className="rounded border bg-background p-2.5"
                                  >
                                    <div className="flex flex-wrap items-center justify-between gap-2">
                                      <span className="font-mono font-semibold">
                                        [{tr.rule_code}] {tr.rule_name}
                                      </span>
                                      <span className="font-mono text-muted-foreground">
                                        CF Pakar {tr.cf_expert.toFixed(2)} × CF Premis{" "}
                                        {tr.cf_premise.toFixed(2)} = CF Rule {tr.cf_rule.toFixed(3)}
                                      </span>
                                    </div>
                                    <ul className="mt-1.5 list-inside list-disc space-y-0.5 text-muted-foreground">
                                      {tr.matched_clauses.map((cl, cIdx) => (
                                        <li key={cIdx} className="font-mono">
                                          IF {cl.fact} {cl.op} {formatFactValue(cl.expected)} (aktual:{" "}
                                          {formatFactValue(cl.actual)}, CF user: {cl.cf_user})
                                        </li>
                                      ))}
                                    </ul>
                                  </div>
                                ))}
                              </div>
                            </details>

                            {res.result_id && (
                              <div className="grid gap-3 border-t pt-3">
                                <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
                                  <span className="text-muted-foreground">
                                    Status Keputusan Petugas:
                                  </span>
                                  <Badge
                                    variant={
                                      res.decision === "accepted"
                                        ? "default"
                                        : res.decision === "rejected"
                                          ? "destructive"
                                          : "outline"
                                    }
                                  >
                                    {res.decision ?? "pending"}
                                  </Badge>
                                </div>
                                {res.decision === "pending" ? (
                                  <div className="grid gap-2 sm:grid-cols-3">
                                    <div className="sm:col-span-2">
                                      <label
                                        htmlFor={`note-${res.result_id}`}
                                        className="sr-only"
                                      >
                                        Catatan keputusan rekomendasi
                                      </label>
                                      <Input
                                        id={`note-${res.result_id}`}
                                        placeholder="Catatan tindakan atau alasan penolakan..."
                                        value={decisionNotes[res.result_id] ?? ""}
                                        onChange={(e) =>
                                          setDecisionNotes((prev) => ({
                                            ...prev,
                                            [res.result_id!]: e.target.value,
                                          }))
                                        }
                                      />
                                    </div>
                                    <div className="flex gap-2">
                                      <Button
                                        type="button"
                                        size="sm"
                                        className="flex-1"
                                        onClick={() =>
                                          void handleDecide(res.result_id!, "accepted")
                                        }
                                      >
                                        Terima
                                      </Button>
                                      <Button
                                        type="button"
                                        size="sm"
                                        variant="destructive"
                                        className="flex-1"
                                        onClick={() =>
                                          void handleDecide(res.result_id!, "rejected")
                                        }
                                      >
                                        Tolak
                                      </Button>
                                    </div>
                                  </div>
                                ) : (
                                  res.decision_note && (
                                    <p className="text-xs text-muted-foreground">
                                      Catatan: {res.decision_note}
                                    </p>
                                  )
                                )}
                              </div>
                            )}
                          </article>
                        ))}
                      </div>
                    )}
                  </CardContent>
                </Card>
              </section>
            )}
          </section>

          <aside className="grid content-start gap-6" aria-label="Riwayat konsultasi domain">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Riwayat Sesi Konsultasi</CardTitle>
                <p className="text-xs text-muted-foreground">
                  Klik salah satu sesi tersimpan untuk meninjau ulang kesimpulan dan jejak aturan.
                </p>
              </CardHeader>
              <CardContent className="grid gap-2.5">
                {history.length === 0 ? (
                  <p className="rounded-md border border-dashed p-4 text-center text-xs text-muted-foreground">
                    Belum ada sesi konsultasi yang disimpan pada domain ini.
                  </p>
                ) : (
                  history.map((item) => {
                    const cid = String(item.consultation_id ?? "")
                    const topResult = item.top_result as Record<string, unknown> | null
                    const createdAt = item.created_at
                      ? new Date(String(item.created_at)).toLocaleString("id-ID")
                      : "-"
                    return (
                      <button
                        key={cid}
                        type="button"
                        onClick={() => void handleLoadConsultation(cid)}
                        className="grid gap-1 rounded-md border bg-background p-3 text-left text-xs transition hover:border-foreground/40 hover:bg-muted/30"
                      >
                        <div className="flex items-center justify-between gap-2">
                          <span className="font-mono text-[11px] text-muted-foreground">
                            {createdAt}
                          </span>
                          <Badge variant="outline" className="text-[10px]">
                            {String(item.results_count ?? 0)} konklusi
                          </Badge>
                        </div>
                        <p className="font-medium text-foreground">
                          {topResult
                            ? String(topResult.kesimpulan_judul ?? topResult.kesimpulan_kode)
                            : "Tidak ada aturan terpicu"}
                        </p>
                        {topResult && (
                          <p className="font-mono text-[11px] text-muted-foreground">
                            CF {(Number(topResult.cf_kombinasi ?? 0) * 100).toFixed(1)}% · Status:{" "}
                            {String(topResult.decision ?? "pending")}
                          </p>
                        )}
                      </button>
                    )
                  })
                )}
              </CardContent>
            </Card>
          </aside>
        </div>
      )}
    </main>
  )
}
