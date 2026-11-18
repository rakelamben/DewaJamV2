import { useEffect, useState } from "react"
import { Link } from "react-router"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { useAuth } from "../../../auth/AuthContext"
import { getEsDomains } from "../../../../lib/es-api"
import type { EsDomainSummary } from "../../../../lib/es-types"
import { toast } from "sonner"

const roleLabels: Record<string, string> = {
  customer: "Pelanggan & Guest",
  kasir: "Staf Kasir & POS",
  gudang: "Staf Gudang & QC",
  manager: "Manajer & Eksekutif",
}

const entityLabels: Record<string, string> = {
  product: "Produk & Horologi",
  transaction: "Transaksi POS",
  purchase: "Purchase Order (PO)",
  kpi: "Indikator Kinerja (KPI)",
  workflow: "Persetujuan Workflow",
  general: "Operasional Umum",
}

export default function EsOverviewPage() {
  const { session, profile } = useAuth()
  const [domains, setDomains] = useState<EsDomainSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const canManageRules = profile?.role === "admin" || profile?.role === "manager"

  async function loadDomains() {
    if (!session) {
      setLoading(false)
      return
    }
    setLoading(true)
    setError(null)
    try {
      const data = await getEsDomains(session.access_token)
      setDomains(data)
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Gagal memuat daftar domain Sistem Pakar."
      setError(msg)
      toast.error(msg)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadDomains()
  }, [session])

  return (
    <main className="grid gap-6 p-4 md:p-6">
      <header className="flex flex-wrap items-start justify-between gap-4 border-b pb-5">
        <div className="max-w-2xl">
          <p className="font-mono text-xs uppercase tracking-wider text-muted-foreground">
            ISS / Expert System (Forward Chaining & Certainty Factor)
          </p>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight md:text-3xl">
            Pusat Konsultasi & Diagnosis Sistem Pakar
          </h1>
          <p className="mt-2 text-sm text-muted-foreground">
            Evaluasi fakta lapangan secara terstruktur, gabungkan dengan data operasional otomatis dari basis data,
            dan peroleh kesimpulan terukur beserta jejak aturan (explanation trace).
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            type="button"
            variant="outline"
            onClick={() => void loadDomains()}
            disabled={loading}
            className="min-h-10"
          >
            {loading ? "Memuat..." : "Muat Ulang Domain"}
          </Button>
        </div>
      </header>

      {loading ? (
        <section aria-label="Status pemuatan domain" className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3].map((skeletonId) => (
            <Card key={skeletonId} className="border-dashed">
              <CardHeader className="space-y-2">
                <div className="h-4 w-28 animate-pulse rounded bg-muted" />
                <div className="h-6 w-48 animate-pulse rounded bg-muted" />
                <div className="h-10 w-full animate-pulse rounded bg-muted" />
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="h-4 w-full animate-pulse rounded bg-muted" />
                <div className="h-9 w-full animate-pulse rounded bg-muted" />
              </CardContent>
            </Card>
          ))}
        </section>
      ) : error ? (
        <section aria-live="polite">
          <Card className="border-destructive/40 bg-destructive/5">
            <CardHeader>
              <CardTitle className="text-base text-destructive">Gagal Memuat Modul Sistem Pakar</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-wrap items-center justify-between gap-4 text-sm">
              <p className="text-muted-foreground">{error}</p>
              <Button type="button" variant="outline" onClick={() => void loadDomains()}>
                Coba Lagi
              </Button>
            </CardContent>
          </Card>
        </section>
      ) : domains.length === 0 ? (
        <section aria-live="polite">
          <Card>
            <CardContent className="grid gap-3 p-8 text-center">
              <h2 className="text-base font-semibold">Belum Ada Domain Sistem Pakar</h2>
              <p className="mx-auto max-w-md text-sm text-muted-foreground">
                Akun Anda belum memiliki akses domain aktif atau sinkronisasi basis aturan belum dijalankan.
              </p>
              <div className="flex justify-center">
                <Button type="button" variant="outline" onClick={() => void loadDomains()}>
                  Sinkronkan Ulang
                </Button>
              </div>
            </CardContent>
          </Card>
        </section>
      ) : (
        <section aria-label="Daftar domain sistem pakar" className="grid gap-5 md:grid-cols-2">
          {domains.map((domain, index) => {
            const isPrimaryHighlight = index === 0
            return (
              <Card
                key={domain.kode}
                className={
                  isPrimaryHighlight
                    ? "border-foreground/25 bg-card shadow-xs md:col-span-2"
                    : "border-border bg-card"
                }
              >
                <CardHeader className="gap-2">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="font-mono text-xs font-medium text-muted-foreground">
                      {domain.kode}
                    </span>
                    <div className="flex flex-wrap gap-1.5">
                      <Badge variant="secondary">
                        {roleLabels[domain.target_role] ?? domain.target_role}
                      </Badge>
                      <Badge variant="outline">
                        {entityLabels[domain.entity_type] ?? domain.entity_type}
                      </Badge>
                    </div>
                  </div>
                  <CardTitle className={isPrimaryHighlight ? "text-xl" : "text-lg"}>
                    {domain.nama}
                  </CardTitle>
                  <p className="text-sm leading-relaxed text-muted-foreground">
                    {domain.deskripsi ?? "Domain evaluasi pakar terstruktur untuk operasional Dewa Jam."}
                  </p>
                </CardHeader>
                <CardContent className="grid gap-4">
                  <dl className="grid grid-cols-2 gap-3 rounded-md border bg-muted/30 p-3 text-sm">
                    <div>
                      <dt className="text-xs text-muted-foreground">Pertanyaan Fakta Input</dt>
                      <dd className="mt-0.5 font-mono text-base font-semibold">
                        {domain.user_facts_count} fakta
                      </dd>
                    </div>
                    <div>
                      <dt className="text-xs text-muted-foreground">Aturan Pakar Aktif</dt>
                      <dd className="mt-0.5 font-mono text-base font-semibold">
                        {domain.active_rules_count} rule
                      </dd>
                    </div>
                  </dl>
                  <div className="flex flex-wrap items-center gap-2">
                    <Link to={`/internal/es/${domain.kode}`} className="flex-1">
                      <Button type="button" className="min-h-10 w-full">
                        Mulai Diagnosis Pakar
                      </Button>
                    </Link>
                    {canManageRules && (
                      <Link to={`/internal/es/${domain.kode}/rules`}>
                        <Button type="button" variant="outline" className="min-h-10">
                          Kelola Rule Base
                        </Button>
                      </Link>
                    )}
                  </div>
                </CardContent>
              </Card>
            )
          })}
        </section>
      )}
    </main>
  )
}
