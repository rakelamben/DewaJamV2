/* eslint-disable react-hooks/set-state-in-effect */
import { useCallback, useEffect, useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { getMisReport, exportMisReport, type MisReport } from "../../../lib/api"
import { useAuth } from "../../auth/AuthContext"
import { toast } from "sonner"

type ReportType = "sales" | "profitability" | "inventory"
const labels: Record<ReportType, string> = { sales: "Sales Report", profitability: "Profitability Report", inventory: "Inventory Report" }
const money = (value: number) => `Rp ${Math.round(value).toLocaleString("id-ID")}`
const initialToday = new Date().toISOString().slice(0, 10)
const initialMonthAgo = new Date(new Date().setDate(new Date().getDate() - 29)).toISOString().slice(0, 10)

export default function MisReportPage({ report }: { report: ReportType }) {
  const { session } = useAuth()
  const [dateFrom, setDateFrom] = useState(initialMonthAgo)
  const [dateTo, setDateTo] = useState(initialToday)
  const [status, setStatus] = useState("all")
  const [data, setData] = useState<MisReport | null>(null)
  const [loading, setLoading] = useState(false)
  const load = useCallback(async () => { if (!session) return; setLoading(true); try { setData(await getMisReport(session.access_token, report, { date_from: dateFrom, date_to: dateTo, stock_status: report === "inventory" ? status : undefined })) } catch (error) { toast.error(error instanceof Error ? error.message : "Laporan gagal dimuat.") } finally { setLoading(false) } }, [session, report, dateFrom, dateTo, status])
  useEffect(() => { void load() }, [load])
  async function download() { if (!session) return; try { const blob = await exportMisReport(session.access_token, report, { date_from: dateFrom, date_to: dateTo, stock_status: report === "inventory" ? status : undefined }); const url = URL.createObjectURL(blob); const link = document.createElement("a"); link.href = url; link.download = `${report}-report-${dateFrom}-${dateTo}.csv`; link.click(); URL.revokeObjectURL(url) } catch (error) { toast.error(error instanceof Error ? error.message : "Export gagal.") } }
  const columns = data?.items[0] ? Object.keys(data.items[0]) : []
  return <main className="grid gap-6 p-6"><div className="flex flex-wrap items-end justify-between gap-4"><div><h1 className="text-2xl font-semibold">{labels[report]}</h1><p className="text-sm text-muted-foreground">Laporan periode {dateFrom} sampai {dateTo}.</p></div><div className="flex flex-wrap items-end gap-2"><div><label className="mb-1 block text-xs text-muted-foreground">Mulai</label><Input type="date" value={dateFrom} onChange={(event) => setDateFrom(event.target.value)} /></div><div><label className="mb-1 block text-xs text-muted-foreground">Sampai</label><Input type="date" value={dateTo} onChange={(event) => setDateTo(event.target.value)} /></div>{report === "inventory" && <select className="h-9 rounded-lg border bg-background px-3 text-sm" value={status} onChange={(event) => setStatus(event.target.value)}><option value="all">Semua stok</option><option value="in_stock">Tersedia</option><option value="low_stock">Stok rendah</option><option value="out_of_stock">Habis</option></select>}<Button onClick={() => void load()} disabled={loading}>Terapkan</Button><Button variant="outline" onClick={() => void download()}>Export CSV</Button></div></div>{data && <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">{Object.entries(data.summary).map(([key, value]) => <div className="rounded-lg border p-4" key={key}><p className="text-xs text-muted-foreground">{key.replaceAll("_", " ")}</p><p className="mt-1 font-semibold">{typeof value === "number" && key.includes("revenue") || key.includes("profit") || key === "hpp" ? money(value) : typeof value === "number" ? value.toLocaleString("id-ID") : value}</p></div>)}</div>}<div className="overflow-x-auto rounded-lg border">{loading && !data ? <div className="p-10 text-center text-sm text-muted-foreground">Memuat laporan...</div> : <table className="w-full text-sm"><thead className="bg-muted/50"><tr>{columns.map((column) => <th className="whitespace-nowrap px-4 py-3 text-left font-medium" key={column}>{column.replaceAll("_", " ")}</th>)}</tr></thead><tbody>{data?.items.map((row, index) => <tr className="border-t" key={index}>{columns.map((column) => <td className="whitespace-nowrap px-4 py-3" key={column}>{String(row[column] ?? "-")}</td>)}</tr>)}</tbody></table>}</div></main>
}
