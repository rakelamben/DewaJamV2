/* eslint-disable react-hooks/set-state-in-effect */
import { useCallback, useEffect, useState } from "react"
import { Card, CardContent } from "@/components/ui/card"
import { getKpiPerformance, type KpiPerformance } from "../../lib/api"
import { useAuth } from "../../src/auth/AuthContext"
import { toast } from "sonner"

const money = (value: number) => `Rp ${Math.round(value).toLocaleString("id-ID")}`

function displayValue(item: KpiPerformance) {
  if (item.satuan === "IDR") return money(item.actual)
  if (item.satuan === "percent") return `${item.actual.toFixed(1)}%`
  return item.actual.toLocaleString("id-ID")
}

export function KpiGrid({ dateFrom, dateTo }: { dateFrom: string; dateTo: string }) {
  const { session } = useAuth()
  const [items, setItems] = useState<KpiPerformance[]>([])
  const [loading, setLoading] = useState(true)
  const load = useCallback(async () => {
    if (!session) return
    setLoading(true)
    try { setItems((await getKpiPerformance(session.access_token, { date_from: dateFrom, date_to: dateTo })).items) }
    catch (error) { toast.error(error instanceof Error ? error.message : "KPI gagal dimuat.") }
    finally { setLoading(false) }
  }, [session, dateFrom, dateTo])
  useEffect(() => { void load() }, [load])
  return <section><h2 className="mb-3 text-lg font-semibold">KPI Performance</h2><div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">{loading ? <div className="text-sm text-muted-foreground">Memuat KPI...</div> : items.map((item) => <Card key={item.kpi_id}><CardContent className="pt-5"><p className="text-sm text-muted-foreground">{item.nama_kpi}</p><p className="mt-2 text-xl font-semibold">{displayValue(item)}</p><p className="mt-1 text-xs text-muted-foreground">Target: {item.target === null ? "Belum ditetapkan" : item.satuan === "IDR" ? money(item.target) : `${item.target.toLocaleString("id-ID")}${item.satuan === "percent" ? "%" : ""}`}</p><span className={`mt-3 inline-block rounded-full px-2 py-1 text-xs ${item.status === "achieved" ? "bg-green-100 text-green-700" : item.status === "warning" ? "bg-yellow-100 text-yellow-700" : item.status === "failed" ? "bg-red-100 text-red-700" : "bg-muted text-muted-foreground"}`}>{item.status === "no_target" ? "Belum ada target" : item.status}</span></CardContent></Card>)}</div></section>
}
