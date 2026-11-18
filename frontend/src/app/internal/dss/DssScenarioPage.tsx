import { useEffect, useMemo, useState } from "react"
import { Link, useNavigate, useParams } from "react-router"
import { ArrowLeft, Play, Save, SlidersHorizontal } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { useAuth } from "../../../auth/AuthContext"
import { getDssScenarios, runDss } from "../../../../lib/dss-api"
import type { DssResult, DssScenario, DssScenarioCode, DssRun } from "../../../../lib/dss-types"
import { toast } from "sonner"

const codes = new Set<DssScenarioCode>(["RESTOCK", "PROMO", "SUPPLIER"])
const labels: Record<string, string> = { RESTOCK: "Restock", PROMO: "Promo", SUPPLIER: "Supplier" }
const productCategories = [
  "Jam Tangan Pria",
  "Jam Tangan Wanita",
  "Jam Tangan Anak-anak",
  "Smartwatch",
  "Jam Tangan Luxury",
  "Strap & Aksesoris",
]

const parameterInfo: Record<DssScenarioCode, Record<string, { label: string; description: string; suffix?: string }>> = {
  RESTOCK: {
    window_days: { label: "Periode analisis penjualan", description: "Jumlah hari histori penjualan yang digunakan untuk menghitung kecepatan jual dan tren.", suffix: "hari" },
    target_cover_days: { label: "Target days of cover", description: "Target jumlah hari stok harus dapat mencukupi penjualan.", suffix: "hari" },
    safety_days: { label: "Hari stok pengaman", description: "Tambahan cadangan hari untuk mengantisipasi keterlambatan atau kenaikan permintaan.", suffix: "hari" },
    default_lead_time_days: { label: "Lead time default supplier", description: "Estimasi waktu tunggu jika supplier produk belum memiliki histori lead time.", suffix: "hari" },
    days_of_cover_cap: { label: "Batas maksimum days of cover", description: "Nilai maksimum days of cover saat kecepatan jual produk bernilai nol.", suffix: "hari" },
    prefilter_max_stok_rop_ratio: { label: "Batas rasio stok terhadap ROP", description: "Produk di atas rasio ini dianggap stoknya masih aman dan dikeluarkan dari analisis.", suffix: "kali ROP" },
    threshold_high: { label: "Ambang restock segera", description: "Skor minimal agar rekomendasi dikategorikan sebagai Restock Segera." },
    threshold_mid: { label: "Ambang restock terjadwal", description: "Skor minimal agar rekomendasi dikategorikan sebagai Restock Terjadwal." },
  },
  PROMO: {
    window_days: { label: "Periode analisis penjualan", description: "Jumlah hari histori penjualan yang digunakan untuk menghitung days of cover dan tren.", suffix: "hari" },
    margin_min_pct: { label: "Margin minimum setelah diskon", description: "Batas margin minimum yang harus tetap tersisa setelah diskon diterapkan.", suffix: "%" },
    discount_cap_high: { label: "Batas diskon promo agresif", description: "Diskon maksimum untuk produk dengan status Promo Agresif.", suffix: "%" },
    discount_cap_mid: { label: "Batas diskon promo ringan", description: "Diskon maksimum untuk produk dengan status Promo Ringan.", suffix: "%" },
    days_of_cover_cap: { label: "Batas maksimum days of cover", description: "Nilai maksimum days of cover saat kecepatan jual produk bernilai nol.", suffix: "hari" },
    threshold_high: { label: "Ambang promo agresif", description: "Skor minimal agar produk dikategorikan sebagai Promo Agresif." },
    threshold_mid: { label: "Ambang promo ringan", description: "Skor minimal agar produk dikategorikan sebagai Promo Ringan." },
  },
  SUPPLIER: {
    window_days: { label: "Periode histori pembelian", description: "Jumlah hari histori PO dan penerimaan yang digunakan untuk menilai supplier.", suffix: "hari" },
    min_purchases: { label: "Minimum jumlah PO", description: "Jumlah minimum PO selesai yang harus dimiliki supplier agar dapat dibandingkan.", suffix: "PO" },
    threshold_high: { label: "Ambang supplier direkomendasikan", description: "Skor minimal agar supplier dikategorikan sebagai Direkomendasikan." },
    threshold_mid: { label: "Ambang supplier cadangan", description: "Skor minimal agar supplier dikategorikan sebagai Cadangan." },
  },
}

function displayValue(value: unknown) {
  if (value === null || value === undefined || value === "") return "-"
  if (typeof value === "number") return Number.isInteger(value) ? String(value) : value.toFixed(2)
  return String(value)
}

export default function DssScenarioPage() {
  const { scenarioCode } = useParams(); const code = scenarioCode?.toUpperCase() as DssScenarioCode
  const { session, profile } = useAuth(); const navigate = useNavigate(); const [scenario, setScenario] = useState<DssScenario | null>(null); const [values, setValues] = useState<Record<string, string>>({}); const [category, setCategory] = useState(""); const [loading, setLoading] = useState(false); const [run, setRun] = useState<DssRun | null>(null)
  const canRun = profile?.role === "admin" || profile?.role === "manager" || (profile?.role === "staf_gudang" && code !== "SUPPLIER")
  useEffect(() => { if (!session || !codes.has(code)) return; void getDssScenarios(session.access_token).then((items) => setScenario(items.find((item) => item.kode === code) ?? null)).catch((error) => toast.error(error instanceof Error ? error.message : "Skenario gagal dimuat.")) }, [session, code])
  useEffect(() => { if (scenario) setValues(Object.fromEntries(Object.entries(scenario.default_params).map(([key, value]) => [key, String(value)]))) }, [scenario])
  const resultGroups = useMemo(() => { const groups = new Map<string, DssResult[]>(); for (const result of run?.results ?? []) { const key = result.group_key ?? "Semua"; groups.set(key, [...(groups.get(key) ?? []), result]) } return groups }, [run])
  const recommendationKeys = useMemo(() => Array.from(new Set((run?.results ?? []).flatMap((item) => Object.keys(item.recommendation)))).sort(), [run])
  async function execute(persist: boolean) { if (!session || !scenario || !canRun) return; setLoading(true); try { const params = Object.fromEntries(Object.entries(values).map(([key, value]) => [key, Number(value)])); const response = await runDss(session.access_token, code, { scope: category ? { kategori: category } : {}, params, persist }); setRun(response); toast.success(persist ? "Run DSS tersimpan." : "Simulasi DSS selesai."); if (persist && response.run_id) navigate(`/internal/dss/runs/${response.run_id}`) } catch (error) { toast.error(error instanceof Error ? error.message : "Run DSS gagal.") } finally { setLoading(false) } }
  if (!codes.has(code)) return <main className="p-6"><p>Skenario DSS tidak ditemukan.</p></main>
  const info = parameterInfo[code]
  return <main className="grid gap-6 p-6"><div className="flex flex-wrap items-start justify-between gap-4"><div><Link className="mb-2 inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground" to="/internal/dss"><ArrowLeft className="size-4" /> Semua DSS</Link><h1 className="text-2xl font-semibold">{labels[code]} DSS</h1><p className="text-sm text-muted-foreground">{scenario?.deskripsi ?? "Memuat konfigurasi skenario..."}</p></div><Link to={`/internal/dss/${code}/weights`}><Button variant="outline"><SlidersHorizontal /> Kelola Bobot</Button></Link></div><Card><CardHeader><CardTitle>Parameter analisis</CardTitle><p className="text-sm text-muted-foreground">Sesuaikan nilai berikut jika ingin menggunakan asumsi analisis yang berbeda dari nilai default.</p></CardHeader><CardContent className="grid gap-4">{scenario?.alternative_type === "product" && <div className="grid gap-2"><label className="text-sm font-medium">Kategori produk (opsional)</label><Select value={category || "__all__"} onValueChange={(value) => setCategory(value === "__all__" ? "" : value ?? "")}><SelectTrigger className="w-full"><SelectValue placeholder="Semua kategori" /></SelectTrigger><SelectContent><SelectItem value="__all__">Semua kategori</SelectItem>{productCategories.map((item) => <SelectItem value={item} key={item}>{item}</SelectItem>)}</SelectContent></Select></div>}<div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">{Object.entries(values).map(([key, value]) => { const item = info[key] ?? { label: key, description: "Parameter analisis DSS.", suffix: undefined }; return <label className="grid gap-1 text-sm" key={key}><span className="font-medium">{item.label}{item.suffix ? ` (${item.suffix})` : ""}</span><span className="min-h-10 text-xs leading-relaxed text-muted-foreground">{item.description}</span><Input type="number" value={value} aria-label={item.label} onChange={(event) => setValues((current) => ({ ...current, [key]: event.target.value }))} /></label> })}</div><div className="flex flex-wrap gap-2"><Button onClick={() => void execute(false)} disabled={loading || !scenario?.active_weight_set || !canRun}><Play /> Simulasi</Button><Button variant="outline" onClick={() => void execute(true)} disabled={loading || !scenario?.active_weight_set || !canRun}><Save /> Jalankan & Simpan</Button>{!canRun && <p className="self-center text-sm text-muted-foreground">Role Anda tidak dapat menjalankan skenario ini.</p>}</div></CardContent></Card>{run && <><div className="flex flex-wrap gap-2"><Badge variant="outline">CR {Number(run.weight_set.cr).toFixed(4)}</Badge><Badge variant={run.persisted ? "default" : "secondary"}>{run.persisted ? "Tersimpan" : "Simulasi"}</Badge>{run.workflow_request_id && <Badge variant="destructive">Workflow dibuat</Badge>}</div>{run.warnings.map((warning, index) => <div className="rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm" key={index}>{String(warning.pesan ?? "Peringatan analisis")}</div>)}{Array.from(resultGroups.entries()).map(([group, results]) => <Card key={group}><CardHeader><CardTitle>{group}</CardTitle></CardHeader><CardContent className="overflow-x-auto"><table className="w-full text-sm"><thead><tr className="border-b text-left"><th className="p-2">Rank</th><th className="p-2">Alternatif</th><th className="p-2">Skor</th><th className="p-2">Status</th>{recommendationKeys.map((key) => <th className="p-2" key={key}>{key}</th>)}</tr></thead><tbody>{results.map((item) => <tr className="border-b" key={item.id}><td className="p-2">{item.ranking}</td><td className="p-2 font-medium">{item.label}</td><td className="p-2">{Number(item.skor).toFixed(4)}</td><td className="p-2"><Badge variant={item.status.includes("Segera") || item.status.includes("Agresif") ? "destructive" : "outline"}>{item.status}</Badge></td>{recommendationKeys.map((key) => <td className="p-2 text-xs" key={key}>{displayValue(item.recommendation[key])}</td>)}</tr>)}</tbody></table></CardContent></Card>)}</>}</main>
}
