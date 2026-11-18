import { useEffect, useState } from "react"
import { Link } from "react-router"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { MarketplaceFooter, MarketplaceHeader } from "@/components/marketplace-header"
import { useCustomerAuth } from "../../auth/CustomerAuthContext"
import {
  getCustomerWatchAdvisorSchema,
  runCustomerWatchAdvisor,
} from "../../../lib/es-api"
import type {
  EsConsultationOutput,
  EsDomainSummary,
  EsFactDefinition,
} from "../../../lib/es-types"
import { toast } from "sonner"

const currency = new Intl.NumberFormat("id-ID", {
  style: "currency",
  currency: "IDR",
  maximumFractionDigits: 0,
})

const confidenceChoices = [
  { value: "1", label: "Sangat Yakin (100%)" },
  { value: "0.85", label: "Yakin (85%)" },
  { value: "0.7", label: "Cukup Yakin (70%)" },
  { value: "0.5", label: "Masih Fleksibel (50%)" },
]

export default function ExpertAdvisorPage() {
  const { session, profile } = useCustomerAuth()
  const [domain, setDomain] = useState<EsDomainSummary | null>(null)
  const [questions, setQuestions] = useState<EsFactDefinition[]>([])
  const [answers, setAnswers] = useState<Record<string, string>>({})
  const [cfInputs, setCfInputs] = useState<Record<string, string>>({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [evaluating, setEvaluating] = useState(false)
  const [result, setResult] = useState<EsConsultationOutput | null>(null)

  async function loadSchema() {
    setLoading(true)
    setError(null)
    try {
      const data = await getCustomerWatchAdvisorSchema(session?.access_token ?? null)
      setDomain(data.domain)
      setQuestions(data.questions)
      const defaultAnswers: Record<string, string> = {}
      const defaultCfs: Record<string, string> = {}
      for (const q of data.questions) {
        if (q.opsi_nilai.length > 0) {
          defaultAnswers[q.kode] = q.opsi_nilai[0].value
        } else {
          defaultAnswers[q.kode] = ""
        }
        defaultCfs[q.kode] = "1"
      }
      setAnswers(defaultAnswers)
      setCfInputs(defaultCfs)
    } catch (err) {
      const msg =
        err instanceof Error
          ? err.message
          : "Gagal memuat kuesioner Konsultan Horologi."
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadSchema()
  }, [session?.access_token])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (questions.length === 0) return
    setEvaluating(true)
    try {
      const parsedCfs: Record<string, number> = {}
      for (const [k, v] of Object.entries(cfInputs)) {
        parsedCfs[k] = Number(v || 1)
      }
      const output = await runCustomerWatchAdvisor(session?.access_token ?? null, {
        facts: answers,
        cf_inputs: parsedCfs,
        persist: true,
      })
      setResult(output)
      toast.success("Evaluasi horologi selesai. Lihat rekomendasi di bawah.")
    } catch (err) {
      toast.error(
        err instanceof Error
          ? err.message
          : "Gagal menjalankan analisis rekomendasi jam tangan."
      )
    } finally {
      setEvaluating(false)
    }
  }

  return (
    <>
      <MarketplaceHeader />
      <main className="mx-auto max-w-6xl px-4 py-10 md:py-14">
        <header className="border-b pb-8">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="font-mono text-xs uppercase tracking-wider text-muted-foreground">
              Dewa Jam Horology Expert System
            </p>
            <Badge variant="outline">
              Status Sesi:{" "}
              {profile ? `Pelanggan Terdaftar (${profile.nama})` : "Tamu (Guest Mode)"}
            </Badge>
          </div>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight md:text-4xl">
            Konsultan Horologi & Pencari Spesifikasi Jam
          </h1>
          <p className="mt-3 max-w-2xl text-base text-muted-foreground">
            Jawab enam parameter teknis berikut sesuai aktivitas, ukuran pergelangan, sensitivitas
            kulit, dan preferensi mesin Anda. Sistem pakar kami menurunkan profil ketahanan air
            (ATM), dimensi casing, dan material tali sebelum mencocokkannya ke stok aktif Dewa Jam.
          </p>
        </header>

        {loading ? (
          <section aria-label="Memuat kuesioner horologi" className="mt-8 grid gap-4">
            {[1, 2, 3].map((item) => (
              <Card key={item}>
                <CardContent className="grid gap-3 p-6">
                  <div className="h-5 w-72 animate-pulse rounded bg-muted" />
                  <div className="h-10 w-full animate-pulse rounded bg-muted" />
                </CardContent>
              </Card>
            ))}
          </section>
        ) : error ? (
          <section aria-live="polite" className="mt-8">
            <Card className="border-destructive/40 bg-destructive/5">
              <CardHeader>
                <CardTitle className="text-base text-destructive">
                  Tidak Dapat Memuat Kuesioner Horologi
                </CardTitle>
              </CardHeader>
              <CardContent className="flex flex-wrap items-center justify-between gap-4 text-sm">
                <p className="text-muted-foreground">{error}</p>
                <Button type="button" variant="outline" onClick={() => void loadSchema()}>
                  Coba Lagi
                </Button>
              </CardContent>
            </Card>
          </section>
        ) : questions.length === 0 ? (
          <section aria-live="polite" className="mt-8">
            <Card>
              <CardContent className="p-8 text-center text-sm text-muted-foreground">
                Daftar pertanyaan konsultasi belum tersedia saat ini.
              </CardContent>
            </Card>
          </section>
        ) : (
          <div className="mt-8 grid gap-8 lg:grid-cols-12">
            <section className="lg:col-span-7" aria-label="Kuesioner preferensi jam tangan">
              <form onSubmit={(e) => void handleSubmit(e)} className="grid gap-5">
                {questions.map((q, index) => {
                  const selectId = `cust-q-${q.kode}`
                  const cfId = `cust-cf-${q.kode}`
                  const selectedVal = answers[q.kode] ?? ""
                  return (
                    <Card key={q.kode}>
                      <CardHeader className="pb-3">
                        <div className="flex items-center justify-between gap-2">
                          <span className="font-mono text-xs text-muted-foreground">
                            Parameter 0{index + 1} · {q.nama}
                          </span>
                          <span className="font-mono text-[11px] text-muted-foreground">
                            {q.kode}
                          </span>
                        </div>
                        <CardTitle className="text-base leading-snug">
                          <label htmlFor={selectId}>{q.pertanyaan || q.nama}</label>
                        </CardTitle>
                      </CardHeader>
                      <CardContent className="grid gap-3">
                        <div className="grid gap-2 sm:grid-cols-2">
                          {q.opsi_nilai.map((opt) => {
                            const isSelected = selectedVal === opt.value
                            return (
                              <button
                                key={opt.value}
                                type="button"
                                onClick={() =>
                                  setAnswers((prev) => ({ ...prev, [q.kode]: opt.value }))
                                }
                                aria-pressed={isSelected}
                                className={
                                  isSelected
                                    ? "min-h-11 rounded-md border-2 border-foreground bg-foreground/5 px-3 py-2.5 text-left text-sm font-medium"
                                    : "min-h-11 rounded-md border bg-background px-3 py-2.5 text-left text-sm text-muted-foreground transition hover:border-foreground/40 hover:text-foreground"
                                }
                              >
                                {opt.label}
                              </button>
                            )
                          })}
                        </div>

                        <div className="flex flex-wrap items-center justify-between gap-2 border-t pt-2.5 text-xs">
                          <label htmlFor={cfId} className="text-muted-foreground">
                            Tingkat kepastian preferensi ini:
                          </label>
                          <select
                            id={cfId}
                            className="h-9 rounded border bg-background px-2.5 text-xs"
                            value={cfInputs[q.kode] ?? "1"}
                            onChange={(e) =>
                              setCfInputs((prev) => ({ ...prev, [q.kode]: e.target.value }))
                            }
                          >
                            {confidenceChoices.map((ch) => (
                              <option key={ch.value} value={ch.value}>
                                {ch.label}
                              </option>
                            ))}
                          </select>
                        </div>
                      </CardContent>
                    </Card>
                  )
                })}

                <div className="flex flex-wrap items-center justify-between gap-4 rounded-lg border bg-muted/25 p-4">
                  <p className="text-xs text-muted-foreground">
                    Domain aktif: <span className="font-mono">{domain?.kode}</span>. Hasil evaluasi
                    dihitung menggunakan Forward Chaining dan Certainty Factor.
                  </p>
                  <Button type="submit" disabled={evaluating} className="min-h-11 px-6">
                    {evaluating
                      ? "Menganalisis Spesifikasi..."
                      : "Analisis & Cari Jam Tangan"}
                  </Button>
                </div>
              </form>
            </section>

            <aside className="lg:col-span-5" aria-label="Hasil diagnosis horologi">
              {!result ? (
                <Card className="sticky top-24 border-dashed">
                  <CardHeader>
                    <CardTitle className="text-lg">Ringkasan Spesifikasi & Rekomendasi</CardTitle>
                  </CardHeader>
                  <CardContent className="grid gap-3 text-sm text-muted-foreground">
                    <p>
                      Pilih jawaban pada enam parameter di sebelah kiri lalu tekan tombol{" "}
                      <strong className="text-foreground">Analisis & Cari Jam Tangan</strong>.
                    </p>
                    <div className="rounded-md border bg-muted/20 p-3 font-mono text-xs">
                      <p className="font-semibold text-foreground">Tahapan Mesin Pakar:</p>
                      <ol className="mt-1.5 list-inside list-decimal space-y-1">
                        <li>Menurunkan profil ketahanan air minimum (ATM).</li>
                        <li>Menentukan rentang diameter casing sesuai pergelangan.</li>
                        <li>Menyaring material strap yang aman bagi kulit.</li>
                        <li>Menghitung Certainty Factor dan mencocokkan stok riil.</li>
                      </ol>
                    </div>
                  </CardContent>
                </Card>
              ) : (
                <div className="grid gap-5" aria-live="polite">
                  <Card className="border-foreground/30">
                    <CardHeader className="border-b bg-muted/20 pb-4">
                      <div className="flex items-center justify-between gap-2">
                        <span className="font-mono text-xs uppercase text-muted-foreground">
                          Profil Teknis Anda
                        </span>
                        <Badge variant="secondary">
                          Aktor: {result.actor_type === "customer" ? "Customer" : "Guest"}
                        </Badge>
                      </div>
                      <CardTitle className="text-lg">
                        Spesifikasi Antara (Intermediate Facts)
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="grid gap-2.5 pt-4 text-xs">
                      {Object.entries(result.inferred_facts).map(([k, info]) => (
                        <div
                          key={k}
                          className="flex items-center justify-between rounded border bg-muted/15 px-3 py-2"
                        >
                          <span className="font-mono text-muted-foreground">{k}</span>
                          <span className="font-mono font-semibold">
                            {String(info.value)} (CF {(info.cf * 100).toFixed(0)}%)
                          </span>
                        </div>
                      ))}
                    </CardContent>
                  </Card>

                  {result.results.map((res) => (
                    <Card key={res.conclusion_code} className="border-foreground/25">
                      <CardHeader className="pb-3">
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <Badge variant="default">Rekomendasi #{res.urutan}</Badge>
                          <span className="font-mono text-sm font-bold">
                            Keyakinan {(res.cf_combined * 100).toFixed(1)}% ({res.confidence_level})
                          </span>
                        </div>
                        <CardTitle className="mt-2 text-xl">{res.conclusion_title}</CardTitle>
                      </CardHeader>
                      <CardContent className="grid gap-4 text-sm">
                        <p className="leading-relaxed text-muted-foreground">{res.explanation}</p>

                        <details className="rounded border bg-muted/20 p-3 text-xs">
                          <summary className="font-mono font-medium text-foreground">
                            Alasan Pakar ({res.fired_rules.length} Rule Terpenuhi)
                          </summary>
                          <ul className="mt-2 space-y-1.5 text-muted-foreground">
                            {res.fired_rules.map((tr) => (
                              <li key={tr.rule_code} className="font-mono">
                                [{tr.rule_code}] {tr.rule_name} (CF Rule {tr.cf_rule.toFixed(2)})
                              </li>
                            ))}
                          </ul>
                        </details>

                        <div className="grid gap-2.5 border-t pt-3">
                          <h3 className="font-mono text-xs font-semibold uppercase text-muted-foreground">
                            Produk Tersedia di Katalog ({res.matched_products.length})
                          </h3>
                          {res.matched_products.length === 0 ? (
                            <p className="text-xs text-muted-foreground">
                              Belum ada stok produk dengan kategori ini saat ini.
                            </p>
                          ) : (
                            res.matched_products.map((prod) => (
                              <div
                                key={prod.product_id}
                                className="flex items-center justify-between gap-3 rounded-md border p-3"
                              >
                                <div>
                                  <p className="font-medium">{prod.nama}</p>
                                  <p className="font-mono text-xs text-muted-foreground">
                                    {currency.format(prod.harga)} · Stok {prod.stok}
                                  </p>
                                  <p className="mt-0.5 text-[11px] text-muted-foreground">
                                    {prod.match_reasons.join(" · ")}
                                  </p>
                                </div>
                                <Link to={`/product/${prod.product_id}`}>
                                  <Button type="button" size="sm" variant="outline">
                                    Lihat Jam
                                  </Button>
                                </Link>
                              </div>
                            ))
                          )}
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              )}
            </aside>
          </div>
        )}
      </main>
      <MarketplaceFooter />
    </>
  )
}
