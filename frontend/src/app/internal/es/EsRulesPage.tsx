import { useEffect, useState } from "react"
import { Link, useParams } from "react-router"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { useAuth } from "../../../auth/AuthContext"
import { createEsRule, getEsDomainRules, updateEsRule } from "../../../../lib/es-api"
import type {
  EsDomainCode,
  EsDomainSummary,
  EsFactDefinition,
  EsKnowledgeReference,
  EsRuleClause,
  EsRuleRow,
} from "../../../../lib/es-types"
import { toast } from "sonner"

const operators: Array<EsRuleClause["op"]> = ["==", "!=", ">=", "<=", ">", "<", "in", "not_in"]

export default function EsRulesPage() {
  const { domainCode } = useParams()
  const code = (domainCode?.toUpperCase() ?? "") as EsDomainCode
  const { session, profile } = useAuth()

  const [domain, setDomain] = useState<EsDomainSummary | null>(null)
  const [facts, setFacts] = useState<EsFactDefinition[]>([])
  const [rules, setRules] = useState<EsRuleRow[]>([])
  const [knowledgeRefs, setKnowledgeRefs] = useState<EsKnowledgeReference[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  const [kode, setKode] = useState("")
  const [nama, setNama] = useState("")
  const [jenisKonklusi, setJenisKonklusi] = useState<"intermediate_fact" | "final_conclusion">(
    "final_conclusion"
  )
  const [kesimpulanKode, setKesimpulanKode] = useState("")
  const [kesimpulanNilai, setKesimpulanNilai] = useState("")
  const [kesimpulanJudul, setKesimpulanJudul] = useState("")
  const [penjelasan, setPenjelasan] = useState("")
  const [cfPakar, setCfPakar] = useState("0.85")
  const [prioritas, setPrioritas] = useState("10")
  const [selectedKnowledgeKey, setSelectedKnowledgeKey] = useState("")
  const [clauses, setClauses] = useState<
    Array<{ fact: string; op: EsRuleClause["op"]; value: string; weight: string }>
  >([{ fact: "", op: "==", value: "", weight: "1" }])

  const canManage = profile?.role === "admin" || profile?.role === "manager"

  async function loadRules() {
    if (!session || !code) {
      setLoading(false)
      return
    }
    setLoading(true)
    setError(null)
    try {
      const data = await getEsDomainRules(session.access_token, code)
      setDomain(data.domain)
      setFacts(data.facts)
      setRules(data.rules)
      setKnowledgeRefs(data.knowledge_references)
      if (data.facts.length > 0 && !clauses[0]?.fact) {
        setClauses([{ fact: data.facts[0].kode, op: "==", value: "", weight: "1" }])
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Gagal memuat basis aturan domain."
      setError(msg)
      toast.error(msg)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadRules()
  }, [session, code])

  function addClauseRow() {
    const defaultFact = facts[0]?.kode ?? ""
    setClauses((prev) => [...prev, { fact: defaultFact, op: "==", value: "", weight: "1" }])
  }

  function removeClauseRow(idx: number) {
    setClauses((prev) => (prev.length > 1 ? prev.filter((_, i) => i !== idx) : prev))
  }

  async function handleCreateRule(e: React.FormEvent) {
    e.preventDefault()
    if (!session || !canManage) return
    if (!kode.trim() || !nama.trim() || !kesimpulanKode.trim() || !kesimpulanJudul.trim() || !penjelasan.trim()) {
      toast.error("Mohon lengkapi kode aturan, nama, kesimpulan, dan penjelasan diagnosis.")
      return
    }

    const parsedClauses: EsRuleClause[] = clauses
      .filter((cl) => cl.fact.trim() !== "")
      .map((cl) => {
        const factDef = facts.find((f) => f.kode === cl.fact)
        let parsedValue: unknown = cl.value
        if (cl.op === "in" || cl.op === "not_in") {
          parsedValue = cl.value
            .split(",")
            .map((s) => s.trim())
            .filter(Boolean)
        } else if (factDef?.tipe_nilai === "number") {
          parsedValue = Number(cl.value)
        } else if (factDef?.tipe_nilai === "boolean") {
          parsedValue = cl.value === "true"
        }
        return {
          fact: cl.fact,
          op: cl.op,
          value: parsedValue,
          weight: Number(cl.weight || 1),
        }
      })

    if (parsedClauses.length === 0) {
      toast.error("Minimal 1 klausa kondisi IF wajib diisi.")
      return
    }

    let knowledgeTable: string | null = null
    let knowledgeId: string | null = null
    if (selectedKnowledgeKey.includes(":")) {
      const [tbl, kid] = selectedKnowledgeKey.split(":")
      knowledgeTable = tbl
      knowledgeId = kid
    }

    setSaving(true)
    try {
      await createEsRule(session.access_token, code, {
        kode: kode.trim().toUpperCase(),
        nama: nama.trim(),
        kondisi: parsedClauses,
        jenis_konklusi: jenisKonklusi,
        kesimpulan_kode: kesimpulanKode.trim(),
        kesimpulan_nilai: jenisKonklusi === "intermediate_fact" ? kesimpulanNilai.trim() : null,
        kesimpulan_judul: kesimpulanJudul.trim(),
        penjelasan: penjelasan.trim(),
        rekomendasi: {},
        cf_pakar: Number(cfPakar),
        prioritas: Number(prioritas || 10),
        knowledge_source_table: knowledgeTable,
        knowledge_source_id: knowledgeId,
        status: "active",
      })
      toast.success("Aturan pakar baru berhasil ditambahkan.")
      setKode("")
      setNama("")
      setKesimpulanKode("")
      setKesimpulanNilai("")
      setKesimpulanJudul("")
      setPenjelasan("")
      await loadRules()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Gagal menyimpan aturan pakar.")
    } finally {
      setSaving(false)
    }
  }

  async function handleStatusChange(ruleId: string, nextStatus: "draft" | "active" | "archived") {
    if (!session || !canManage) return
    setSaving(true)
    try {
      await updateEsRule(session.access_token, ruleId, { status: nextStatus })
      toast.success(`Status aturan diperbarui menjadi ${nextStatus}.`)
      await loadRules()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Gagal memperbarui status aturan.")
    } finally {
      setSaving(false)
    }
  }

  return (
    <main className="grid gap-6 p-4 md:p-6">
      <header className="flex flex-wrap items-start justify-between gap-4 border-b pb-5">
        <div>
          <Link
            to={`/internal/es/${code}`}
            className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
          >
            Kembali ke Formulir Konsultasi Domain
          </Link>
          <p className="mt-2 font-mono text-xs uppercase tracking-wider text-muted-foreground">
            Akuisisi Pengetahuan & Rule Base: {code}
          </p>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight">
            Manajemen Aturan Pakar ({domain?.nama ?? code})
          </h1>
          <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
            Kelola premis IF-THEN, bobot Certainty Factor (CF Pakar), dan tautan dokumen SOP Knowledge
            Management tanpa mengubah kode program.
          </p>
        </div>
        <Button type="button" variant="outline" onClick={() => void loadRules()} disabled={loading}>
          Muat Ulang Aturan
        </Button>
      </header>

      {loading ? (
        <section aria-label="Memuat daftar aturan" className="grid gap-4">
          <Card>
            <CardContent className="grid gap-3 p-6">
              <div className="h-6 w-56 animate-pulse rounded bg-muted" />
              <div className="h-24 w-full animate-pulse rounded bg-muted" />
            </CardContent>
          </Card>
        </section>
      ) : error ? (
        <section aria-live="polite">
          <Card className="border-destructive/40 bg-destructive/5">
            <CardHeader>
              <CardTitle className="text-base text-destructive">
                Basis Aturan Gagal Dimuat
              </CardTitle>
            </CardHeader>
            <CardContent className="flex flex-wrap items-center justify-between gap-4 text-sm">
              <p className="text-muted-foreground">{error}</p>
              <Button type="button" variant="outline" onClick={() => void loadRules()}>
                Coba Lagi
              </Button>
            </CardContent>
          </Card>
        </section>
      ) : (
        <div className="grid gap-6 lg:grid-cols-3">
          <section className="grid content-start gap-4 lg:col-span-2" aria-label="Daftar aturan pakar">
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">
                  Daftar Rule Base ({rules.length} Aturan Terdaftar)
                </CardTitle>
              </CardHeader>
              <CardContent className="grid gap-3">
                {rules.length === 0 ? (
                  <p className="rounded-md border border-dashed p-6 text-center text-sm text-muted-foreground">
                    Belum ada aturan pada domain ini. Tambahkan aturan baru melalui formulir di samping.
                  </p>
                ) : (
                  rules.map((rule) => (
                    <article
                      key={rule.rule_id}
                      className="grid gap-3 rounded-lg border bg-card p-4"
                    >
                      <div className="flex flex-wrap items-start justify-between gap-2">
                        <div>
                          <div className="flex flex-wrap items-center gap-2">
                            <span className="font-mono text-xs font-semibold">[{rule.kode}]</span>
                            <Badge
                              variant={
                                rule.status === "active"
                                  ? "default"
                                  : rule.status === "draft"
                                    ? "secondary"
                                    : "outline"
                              }
                            >
                              {rule.status}
                            </Badge>
                            <Badge variant="outline" className="font-mono text-[11px]">
                              {rule.jenis_konklusi === "intermediate_fact"
                                ? "Fakta Antara (Pass 1)"
                                : "Konklusi Akhir"}
                            </Badge>
                          </div>
                          <h2 className="mt-1 text-base font-semibold">{rule.nama}</h2>
                        </div>
                        <div className="text-right font-mono text-xs">
                          <p className="font-semibold">CF Pakar: {Number(rule.cf_pakar).toFixed(2)}</p>
                          <p className="text-muted-foreground">Prioritas: {rule.prioritas}</p>
                        </div>
                      </div>

                      <div className="rounded border bg-muted/25 p-3 font-mono text-xs">
                        <p className="font-semibold text-muted-foreground">IF:</p>
                        <ul className="mt-1 list-inside list-disc space-y-0.5">
                          {rule.kondisi.map((cl, idx) => (
                            <li key={idx}>
                              {cl.fact} {cl.op} {JSON.stringify(cl.value)} (bobot {cl.weight ?? 1})
                            </li>
                          ))}
                        </ul>
                        <p className="mt-2 font-semibold text-muted-foreground">
                          THEN: {rule.kesimpulan_kode}
                          {rule.kesimpulan_nilai ? ` = "${rule.kesimpulan_nilai}"` : ""} (
                          {rule.kesimpulan_judul})
                        </p>
                      </div>

                      <p className="text-sm text-muted-foreground">{rule.penjelasan}</p>

                      {canManage && (
                        <div className="flex flex-wrap items-center justify-end gap-2 border-t pt-2.5">
                          {rule.status !== "active" && (
                            <Button
                              type="button"
                              size="sm"
                              onClick={() => void handleStatusChange(rule.rule_id, "active")}
                              disabled={saving}
                            >
                              Aktifkan
                            </Button>
                          )}
                          {rule.status !== "draft" && (
                            <Button
                              type="button"
                              size="sm"
                              variant="outline"
                              onClick={() => void handleStatusChange(rule.rule_id, "draft")}
                              disabled={saving}
                            >
                              Jadikan Draft
                            </Button>
                          )}
                          {rule.status !== "archived" && (
                            <Button
                              type="button"
                              size="sm"
                              variant="ghost"
                              onClick={() => void handleStatusChange(rule.rule_id, "archived")}
                              disabled={saving}
                            >
                              Arsipkan
                            </Button>
                          )}
                        </div>
                      )}
                    </article>
                  ))
                )}
              </CardContent>
            </Card>
          </section>

          <aside className="grid content-start gap-4" aria-label="Formulir tambah aturan pakar">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Tambah Aturan Pakar Baru</CardTitle>
                <p className="text-xs text-muted-foreground">
                  Susun klausa kondisi IF beserta bobot CF Pakar antara -1.0 hingga 1.0.
                </p>
              </CardHeader>
              <CardContent>
                {!canManage ? (
                  <p className="text-sm text-muted-foreground">
                    Hanya Manajer atau Admin yang memiliki izin menambah atau mengubah basis aturan pakar.
                  </p>
                ) : (
                  <form onSubmit={(e) => void handleCreateRule(e)} className="grid gap-3.5 text-sm">
                    <div>
                      <label htmlFor="rule-kode" className="mb-1 block text-xs font-medium">
                        Kode Rule (Unik)
                      </label>
                      <Input
                        id="rule-kode"
                        placeholder="Misal: R_CUSTOM_01"
                        value={kode}
                        onChange={(e) => setKode(e.target.value)}
                        required
                      />
                    </div>

                    <div>
                      <label htmlFor="rule-nama" className="mb-1 block text-xs font-medium">
                        Nama Aturan
                      </label>
                      <Input
                        id="rule-nama"
                        placeholder="Deskripsi singkat aturan"
                        value={nama}
                        onChange={(e) => setNama(e.target.value)}
                        required
                      />
                    </div>

                    <div className="grid gap-2 rounded-md border bg-muted/20 p-3">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-semibold">Klausa Premis (IF)</span>
                        <Button
                          type="button"
                          size="sm"
                          variant="outline"
                          onClick={addClauseRow}
                        >
                          + Klausa
                        </Button>
                      </div>
                      {clauses.map((cl, idx) => (
                        <div key={idx} className="grid gap-2 border-t pt-2">
                          <label htmlFor={`clause-fact-${idx}`} className="text-[11px] text-muted-foreground">
                            Fakta #{idx + 1}
                          </label>
                          <select
                            id={`clause-fact-${idx}`}
                            className="h-9 w-full rounded border bg-background px-2 text-xs"
                            value={cl.fact}
                            onChange={(e) =>
                              setClauses((prev) =>
                                prev.map((item, i) =>
                                  i === idx ? { ...item, fact: e.target.value } : item
                                )
                              )
                            }
                          >
                            {facts.map((f) => (
                              <option key={f.kode} value={f.kode}>
                                [{f.sumber_fakta}] {f.kode} - {f.nama}
                              </option>
                            ))}
                          </select>
                          <div className="grid grid-cols-3 gap-1.5">
                            <div>
                              <label htmlFor={`clause-op-${idx}`} className="sr-only">
                                Operator klausa #{idx + 1}
                              </label>
                              <select
                                id={`clause-op-${idx}`}
                                className="h-9 w-full rounded border bg-background px-2 font-mono text-xs"
                                value={cl.op}
                                onChange={(e) =>
                                  setClauses((prev) =>
                                    prev.map((item, i) =>
                                      i === idx
                                        ? { ...item, op: e.target.value as EsRuleClause["op"] }
                                        : item
                                    )
                                  )
                                }
                              >
                                {operators.map((op) => (
                                  <option key={op} value={op}>
                                    {op}
                                  </option>
                                ))}
                              </select>
                            </div>
                            <div className="col-span-2">
                              <label htmlFor={`clause-val-${idx}`} className="sr-only">
                                Nilai pembanding klausa #{idx + 1}
                              </label>
                              <Input
                                id={`clause-val-${idx}`}
                                className="h-9 text-xs"
                                placeholder="Nilai uji..."
                                value={cl.value}
                                onChange={(e) =>
                                  setClauses((prev) =>
                                    prev.map((item, i) =>
                                      i === idx ? { ...item, value: e.target.value } : item
                                    )
                                  )
                                }
                              />
                            </div>
                          </div>
                          {clauses.length > 1 && (
                            <Button
                              type="button"
                              size="sm"
                              variant="ghost"
                              onClick={() => removeClauseRow(idx)}
                            >
                              Hapus Klausa Ini
                            </Button>
                          )}
                        </div>
                      ))}
                    </div>

                    <div>
                      <label htmlFor="rule-jenis" className="mb-1 block text-xs font-medium">
                        Jenis Konklusi (THEN)
                      </label>
                      <select
                        id="rule-jenis"
                        className="h-9 w-full rounded border bg-background px-2.5 text-xs"
                        value={jenisKonklusi}
                        onChange={(e) =>
                          setJenisKonklusi(
                            e.target.value as "intermediate_fact" | "final_conclusion"
                          )
                        }
                      >
                        <option value="final_conclusion">Konklusi Akhir (Rekomendasi / Diagnosis)</option>
                        <option value="intermediate_fact">Fakta Antara (Intermediate Fact)</option>
                      </select>
                    </div>

                    <div>
                      <label htmlFor="rule-kesimpulan-kode" className="mb-1 block text-xs font-medium">
                        Kode Konklusi / Fakta Antara
                      </label>
                      <Input
                        id="rule-kesimpulan-kode"
                        placeholder="Misal: QC_REJECT_SUPPLIER"
                        value={kesimpulanKode}
                        onChange={(e) => setKesimpulanKode(e.target.value)}
                        required
                      />
                    </div>

                    {jenisKonklusi === "intermediate_fact" && (
                      <div>
                        <label htmlFor="rule-kesimpulan-nilai" className="mb-1 block text-xs font-medium">
                          Nilai Fakta Antara
                        </label>
                        <Input
                          id="rule-kesimpulan-nilai"
                          placeholder="Misal: active_water"
                          value={kesimpulanNilai}
                          onChange={(e) => setKesimpulanNilai(e.target.value)}
                          required
                        />
                      </div>
                    )}

                    <div>
                      <label htmlFor="rule-judul" className="mb-1 block text-xs font-medium">
                        Judul Kesimpulan Diagnosis
                      </label>
                      <Input
                        id="rule-judul"
                        placeholder="Judul hasil diagnosis untuk pengguna"
                        value={kesimpulanJudul}
                        onChange={(e) => setKesimpulanJudul(e.target.value)}
                        required
                      />
                    </div>

                    <div>
                      <label htmlFor="rule-penjelasan" className="mb-1 block text-xs font-medium">
                        Penjelasan Pakar & Alasan Teknis
                      </label>
                      <textarea
                        id="rule-penjelasan"
                        rows={3}
                        className="w-full rounded-md border bg-background p-2.5 text-xs"
                        placeholder="Uraikan alasan pakar dan tindakan yang harus diambil..."
                        value={penjelasan}
                        onChange={(e) => setPenjelasan(e.target.value)}
                        required
                      />
                    </div>

                    <div className="grid grid-cols-2 gap-2">
                      <div>
                        <label htmlFor="rule-cf" className="mb-1 block text-xs font-medium">
                          CF Pakar (-1.0 s.d 1.0)
                        </label>
                        <Input
                          id="rule-cf"
                          type="number"
                          min="-1"
                          max="1"
                          step="0.05"
                          value={cfPakar}
                          onChange={(e) => setCfPakar(e.target.value)}
                          required
                        />
                      </div>
                      <div>
                        <label htmlFor="rule-prio" className="mb-1 block text-xs font-medium">
                          Prioritas Evaluasi
                        </label>
                        <Input
                          id="rule-prio"
                          type="number"
                          min="1"
                          max="999"
                          value={prioritas}
                          onChange={(e) => setPrioritas(e.target.value)}
                          required
                        />
                      </div>
                    </div>

                    {knowledgeRefs.length > 0 && (
                      <div>
                        <label htmlFor="rule-kms" className="mb-1 block text-xs font-medium">
                          Tautan Referensi SOP / KMS (Opsional)
                        </label>
                        <select
                          id="rule-kms"
                          className="h-9 w-full rounded border bg-background px-2 text-xs"
                          value={selectedKnowledgeKey}
                          onChange={(e) => setSelectedKnowledgeKey(e.target.value)}
                        >
                          <option value="">Tanpa tautan dokumen KMS</option>
                          {knowledgeRefs.map((kr) => (
                            <option key={`${kr.table}:${kr.id}`} value={`${kr.table}:${kr.id}`}>
                              [{kr.table}] {kr.label}
                            </option>
                          ))}
                        </select>
                      </div>
                    )}

                    <Button type="submit" disabled={saving} className="min-h-10 w-full">
                      {saving ? "Menyimpan..." : "Simpan Aturan ke Rule Base"}
                    </Button>
                  </form>
                )}
              </CardContent>
            </Card>
          </aside>
        </div>
      )}
    </main>
  )
}
