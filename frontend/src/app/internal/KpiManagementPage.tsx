/* eslint-disable react-hooks/set-state-in-effect */
import { useCallback, useEffect, useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { createKpiTarget, getKpiTargets, getKpis, type KpiTarget } from "../../../lib/api"
import { useAuth } from "../../auth/AuthContext"
import { toast } from "sonner"

type KpiDefinition = { kpi_id: string; kode_kpi: string; nama_kpi: string; satuan: string }

export default function KpiManagementPage() {
  const { session, profile } = useAuth()
  const [kpis, setKpis] = useState<KpiDefinition[]>([])
  const [targets, setTargets] = useState<KpiTarget[]>([])
  const [kpiId, setKpiId] = useState("")
  const [dateFrom, setDateFrom] = useState(new Date().toISOString().slice(0, 8) + "01")
  const [dateTo, setDateTo] = useState(new Date(new Date().getFullYear(), new Date().getMonth() + 1, 0).toISOString().slice(0, 10))
  const [target, setTarget] = useState("")
  const [warning, setWarning] = useState("")
  const [loading, setLoading] = useState(false)
  const canManage = profile?.role === "admin" || profile?.role === "manager"
  const load = useCallback(async () => { if (!session) return; try { const [kpiResponse, targetResponse] = await Promise.all([getKpis(session.access_token), getKpiTargets(session.access_token)]); setKpis(kpiResponse.items as KpiDefinition[]); setTargets(targetResponse.items); if (!kpiId && kpiResponse.items[0]) setKpiId(String(kpiResponse.items[0].kpi_id)) } catch (error) { toast.error(error instanceof Error ? error.message : "Data KPI gagal dimuat.") } }, [session, kpiId])
  useEffect(() => { void load() }, [load])
  async function submit() { if (!session || !kpiId) return; setLoading(true); try { await createKpiTarget(session.access_token, { kpi_id: kpiId, personnel_id: null, periode_tipe: "monthly", periode_mulai: dateFrom, periode_selesai: dateTo, nilai_target: Number(target), nilai_peringatan: warning ? Number(warning) : null, catatan: null }); toast.success("Target KPI berhasil dibuat."); setTarget(""); setWarning(""); await load() } catch (error) { toast.error(error instanceof Error ? error.message : "Target KPI gagal dibuat.") } finally { setLoading(false) } }
  return <main className="grid gap-6 p-6"><div><h1 className="text-2xl font-semibold">KPI Management</h1><p className="text-sm text-muted-foreground">Kelola target KPI per periode.</p></div>{canManage && <div className="grid gap-3 rounded-lg border p-4 md:grid-cols-5"><select className="h-9 rounded-lg border bg-background px-3 text-sm" value={kpiId} onChange={(event) => setKpiId(event.target.value)}>{kpis.map((kpi) => <option key={kpi.kpi_id} value={kpi.kpi_id}>{kpi.nama_kpi}</option>)}</select><Input type="date" value={dateFrom} onChange={(event) => setDateFrom(event.target.value)} /><Input type="date" value={dateTo} onChange={(event) => setDateTo(event.target.value)} /><Input type="number" min="0" placeholder="Nilai target" value={target} onChange={(event) => setTarget(event.target.value)} /><div className="flex gap-2"><Input type="number" min="0" placeholder="Peringatan" value={warning} onChange={(event) => setWarning(event.target.value)} /><Button onClick={() => void submit()} disabled={loading || !target}>Simpan</Button></div></div>}<div className="overflow-x-auto rounded-lg border"><table className="w-full text-sm"><thead className="bg-muted/50"><tr><th className="px-4 py-3 text-left">KPI</th><th className="px-4 py-3 text-left">Periode</th><th className="px-4 py-3 text-left">Target</th><th className="px-4 py-3 text-left">Peringatan</th></tr></thead><tbody>{targets.map((item) => <tr className="border-t" key={item.target_id}><td className="px-4 py-3">{item.mis_kpi_definitions?.nama_kpi ?? item.kpi_id}</td><td className="px-4 py-3">{item.periode_mulai} — {item.periode_selesai}</td><td className="px-4 py-3">{item.nilai_target}</td><td className="px-4 py-3">{item.nilai_peringatan ?? "-"}</td></tr>)}</tbody></table>{!targets.length && <p className="p-8 text-center text-sm text-muted-foreground">Belum ada target KPI.</p>}</div></main>
}
