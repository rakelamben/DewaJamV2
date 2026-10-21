/* eslint-disable react-hooks/set-state-in-effect */
import { useCallback, useEffect, useState } from "react"
import { Check, RefreshCw, X } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { toast } from "sonner"
import { approveWorkflow, getWorkflows, rejectWorkflow, type StockWorkflow } from "../../../lib/api"
import { useAuth } from "../../auth/AuthContext"

export default function WorkflowsPage() {
  const { session, profile } = useAuth()
  const [items, setItems] = useState<StockWorkflow[]>([])
  const [loading, setLoading] = useState(true)
  const canApprove = profile?.role === "admin" || profile?.role === "manager"

  const load = useCallback(async () => {
    if (!session) return
    setLoading(true)
    try { setItems(await getWorkflows(session.access_token)) } catch (error) { toast.error(error instanceof Error ? error.message : "Workflow gagal dimuat.") } finally { setLoading(false) }
  }, [session])

  useEffect(() => { void load() }, [load])

  async function decide(item: StockWorkflow, decision: "approve" | "reject") {
    if (!session) return
    const note = decision === "reject" ? window.prompt("Alasan penolakan wajib diisi:") : window.prompt("Catatan approval (opsional):")
    if (decision === "reject" && !note?.trim()) return
    try {
      if (decision === "approve") await approveWorkflow(session.access_token, item.request_id, note || undefined)
      else await rejectWorkflow(session.access_token, item.request_id, note!.trim())
      await load()
      toast.success(decision === "approve" ? "Workflow disetujui dan diproses." : "Workflow ditolak.")
    } catch (error) { toast.error(error instanceof Error ? error.message : "Workflow gagal diproses.") }
  }

  return <main className="grid gap-6 p-6"><div className="flex flex-wrap items-center justify-between gap-3"><div><h1 className="text-2xl font-semibold">Workflow Approval</h1><p className="text-sm text-muted-foreground">Kontrol adjustment, barang rusak, dan retur stok.</p></div><Button variant="outline" onClick={() => void load()} disabled={loading}><RefreshCw className={loading ? "animate-spin" : ""} /> Refresh</Button></div><Card><CardHeader><CardTitle>Request workflow</CardTitle></CardHeader><CardContent>{loading ? <p>Memuat workflow...</p> : items.length === 0 ? <p className="py-8 text-center text-sm text-muted-foreground">Belum ada workflow.</p> : <div className="grid gap-3">{items.map((item) => { const metadata = item.metadata || {}; return <div className="rounded-lg border p-4" key={item.request_id}><div className="flex flex-wrap items-start justify-between gap-3"><div><p className="font-medium">{item.tipe_request}</p><p className="text-sm text-muted-foreground">{String(metadata.product_name || item.reference_id)}</p><p className="mt-2 text-sm">{item.deskripsi}</p></div><span className="rounded-full bg-muted px-2 py-1 text-xs uppercase">{item.current_status}</span></div><div className="mt-3 grid gap-1 text-xs text-muted-foreground sm:grid-cols-3"><span>Perubahan: {String(metadata.qty_change ?? "-")}</span><span>Stok: {String(metadata.stok_sebelum ?? "-")} → {String(metadata.stok_diharapkan ?? "-")}</span><span>Dibuat: {new Date(item.created_at).toLocaleString("id-ID")}</span></div>{canApprove && item.current_status === "pending" && <div className="mt-4 flex justify-end gap-2"><Button variant="destructive" size="sm" onClick={() => void decide(item, "reject")}><X /> Tolak</Button><Button size="sm" onClick={() => void decide(item, "approve")}><Check /> Setujui</Button></div>}</div>})}</div>}</CardContent></Card></main>
}
