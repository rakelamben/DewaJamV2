/* eslint-disable react-hooks/set-state-in-effect */
import { useCallback, useEffect, useMemo, useState } from "react"
import { BarChart } from "../../components/charts/bar-chart"
import { Bar } from "../../components/charts/bar"
import { BarYAxis } from "../../components/charts/bar-y-axis"
import { BarXAxis } from "../../components/charts/bar-x-axis"
import { ChartTooltip } from "../../components/charts/tooltip/chart-tooltip"
import { Grid } from "../../components/charts/grid"
import { LineChart, Line } from "../../components/charts/line-chart"
import { XAxis } from "../../components/charts/x-axis"
import { PieChart } from "../../components/charts/pie-chart"
import { PieSlice } from "../../components/charts/pie-slice"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { getMisDashboard, type MisDashboard } from "../../../lib/api"
import { useAuth } from "../../auth/AuthContext"
import { toast } from "sonner"
import { KpiGrid } from "../../../components/mis/KpiGrid"

const isoDate = (value: Date) => value.toISOString().slice(0, 10)
const money = (value: number) => `Rp ${Math.round(value).toLocaleString("id-ID")}`
const initialTo = new Date()
const initialFrom = new Date(initialTo.getTime() - 29 * 24 * 60 * 60 * 1000)

function Metric({ label, value, detail }: { label: string; value: string; detail?: string }) {
  return <Card><CardContent className="pt-6"><p className="text-sm text-muted-foreground">{label}</p><p className="mt-2 text-2xl font-semibold tracking-tight">{value}</p>{detail && <p className="mt-1 text-xs text-muted-foreground">{detail}</p>}</CardContent></Card>
}

export default function DashboardPage() {
  const { session } = useAuth()
  const [dashboard, setDashboard] = useState<MisDashboard | null>(null)
  const [dateFrom, setDateFrom] = useState(isoDate(initialFrom))
  const [dateTo, setDateTo] = useState(isoDate(initialTo))
  const [channel, setChannel] = useState("")
  const [loading, setLoading] = useState(true)
  const load = useCallback(async () => { if (!session) return; setLoading(true); try { setDashboard(await getMisDashboard(session.access_token, { date_from: dateFrom, date_to: dateTo, channel: channel || undefined })) } catch (error) { toast.error(error instanceof Error ? error.message : "Dashboard MIS gagal dimuat.") } finally { setLoading(false) } }, [session, dateFrom, dateTo, channel])
  useEffect(() => { void load() }, [load])
  const daily = useMemo(() => (dashboard?.daily || []).map((row) => ({ ...row, date: new Date(`${row.date}T00:00:00`) })), [dashboard])
  const channelData = dashboard?.channels || []
  const statusData = (dashboard?.statuses || []).map((row, index) => ({ label: row.status, value: row.count, color: `var(--chart-${(index % 5) + 1})` }))
  const topProducts = dashboard?.top_products || []
  const kpis = dashboard?.kpis
  return <main className="grid gap-6 p-6"><div className="flex flex-wrap items-start justify-between gap-4"><div><h1 className="text-2xl font-semibold">MIS Dashboard</h1><p className="text-sm text-muted-foreground">Ringkasan penjualan, profit, channel, dan persediaan.</p></div><div className="flex flex-wrap items-end gap-2"><div><label className="mb-1 block text-xs text-muted-foreground">Mulai</label><Input type="date" value={dateFrom} onChange={(event) => setDateFrom(event.target.value)} /></div><div><label className="mb-1 block text-xs text-muted-foreground">Sampai</label><Input type="date" value={dateTo} onChange={(event) => setDateTo(event.target.value)} /></div><select className="h-9 rounded-lg border bg-background px-3 text-sm" value={channel} onChange={(event) => setChannel(event.target.value)}><option value="">Semua channel</option><option value="pos">POS</option><option value="marketplace">Marketplace</option></select><Button onClick={() => void load()} disabled={loading}>Terapkan</Button></div></div><KpiGrid dateFrom={dateFrom} dateTo={dateTo} />
    {loading && !dashboard ? <div className="grid place-items-center rounded-lg border py-20 text-sm text-muted-foreground">Memuat dashboard MIS...</div> : <><div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4"><Metric label="Total Pendapatan" value={money(kpis?.revenue || 0)} detail={`${dashboard?.period.date_from} sampai ${dashboard?.period.date_to}`} /><Metric label="Gross Profit" value={money(kpis?.profit || 0)} detail={`Margin ${(kpis?.margin || 0).toFixed(1)}%`} /><Metric label="Transaksi" value={String(kpis?.transactions || 0)} detail={`${kpis?.items || 0} item terjual`} /><Metric label="Rata-rata Transaksi" value={money(kpis?.average_transaction || 0)} detail={`${kpis?.unique_customers || 0} pelanggan unik`} /></div><div className="grid gap-6 xl:grid-cols-[2fr_1fr]"><Card><CardHeader><CardTitle>Tren Pendapatan dan Profit</CardTitle></CardHeader><CardContent><LineChart data={daily} xDataKey="date" status={loading ? "loading" : "ready"} className="min-h-72"><Grid horizontal /><Line dataKey="revenue" stroke="var(--chart-1)" /><Line dataKey="profit" stroke="var(--chart-2)" /><XAxis /><ChartTooltip /></LineChart></CardContent></Card><Card><CardHeader><CardTitle>Status Transaksi</CardTitle></CardHeader><CardContent className="grid place-items-center"><PieChart data={statusData} innerRadius={72} size={260}>{statusData.map((_, index) => <PieSlice key={index} index={index} />)}</PieChart><div className="flex flex-wrap justify-center gap-3 text-xs text-muted-foreground">{statusData.map((row) => <span key={row.label}><i className="mr-1 inline-block size-2 rounded-full" style={{ background: row.color }} />{row.label}: {row.value}</span>)}</div></CardContent></Card></div><div className="grid gap-6 xl:grid-cols-2"><Card><CardHeader><CardTitle>Pendapatan per Channel</CardTitle></CardHeader><CardContent><BarChart data={channelData} xDataKey="channel" className="min-h-72"><Grid horizontal /><Bar dataKey="revenue" fill="var(--chart-1)" lineCap="round" /><BarXAxis /><ChartTooltip /></BarChart></CardContent></Card><Card><CardHeader><CardTitle>Top 10 Produk berdasarkan Pendapatan</CardTitle></CardHeader><CardContent><BarChart data={topProducts} xDataKey="name" orientation="horizontal" className="min-h-72"><Grid horizontal /><Bar dataKey="revenue" fill="var(--chart-3)" lineCap="round" /><BarYAxis /><ChartTooltip /></BarChart></CardContent></Card></div><Card><CardHeader><CardTitle>Stok Kritis</CardTitle></CardHeader><CardContent>{(dashboard?.low_stock || []).length === 0 ? <p className="py-6 text-center text-sm text-muted-foreground">Tidak ada produk dengan stok kritis.</p> : <div className="overflow-x-auto"><table className="w-full text-sm"><thead><tr className="border-b text-left text-muted-foreground"><th className="px-3 py-2">Produk</th><th className="px-3 py-2">Kategori</th><th className="px-3 py-2 text-right">Stok</th><th className="px-3 py-2 text-right">Batas</th></tr></thead><tbody>{dashboard?.low_stock.map((row) => <tr className="border-b last:border-0" key={row.product_id}><td className="px-3 py-2 font-medium">{row.nama_barang}</td><td className="px-3 py-2 text-muted-foreground">{row.kategori || "-"}</td><td className="px-3 py-2 text-right font-semibold text-destructive">{row.stok}</td><td className="px-3 py-2 text-right text-muted-foreground">{row.stock_threshold}</td></tr>)}</tbody></table></div>}</CardContent></Card><p className="text-right text-xs text-muted-foreground">Data dibuat: {dashboard?.generated_at ? new Date(dashboard.generated_at).toLocaleString("id-ID") : "-"}</p></>}
  </main>
}
