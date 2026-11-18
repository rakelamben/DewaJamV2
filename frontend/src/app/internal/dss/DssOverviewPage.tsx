import { useEffect, useState } from "react"
import { Link } from "react-router"
import { BrainCircuit, RefreshCw } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { useAuth } from "../../../auth/AuthContext"
import { getDssScenarios } from "../../../../lib/dss-api"
import type { DssScenario } from "../../../../lib/dss-types"
import { toast } from "sonner"

export default function DssOverviewPage() {
  const { session } = useAuth(); const [items, setItems] = useState<DssScenario[]>([]); const [loading, setLoading] = useState(false)
  async function load() { if (!session) return; setLoading(true); try { setItems(await getDssScenarios(session.access_token)) } catch (error) { toast.error(error instanceof Error ? error.message : "DSS gagal dimuat.") } finally { setLoading(false) } }
  useEffect(() => { void load() }, [session])
  return <main className="grid gap-6 p-6"><div className="flex items-start justify-between gap-4"><div><h1 className="text-2xl font-semibold">Decision Support System</h1><p className="text-sm text-muted-foreground">Analisis AHP dan TOPSIS untuk keputusan operasional.</p></div><Button variant="outline" onClick={() => void load()} disabled={loading}><RefreshCw className={loading ? "animate-spin" : ""} /> Refresh</Button></div><div className="grid gap-4 md:grid-cols-3">{items.map((item) => <Card key={item.kode}><CardHeader><CardTitle className="flex items-center gap-2"><BrainCircuit className="size-4" />{item.nama}</CardTitle><p className="text-sm text-muted-foreground">{item.deskripsi}</p></CardHeader><CardContent className="grid gap-3"><div className="flex justify-between text-sm"><span>Alternatif</span><Badge variant="outline">{item.alternative_type}</Badge></div><div className="flex justify-between text-sm"><span>Kriteria</span><span>{item.criteria.length}</span></div><div className="flex justify-between text-sm"><span>CR aktif</span><span>{item.active_weight_set ? Number(item.active_weight_set.cr).toFixed(4) : "Belum ada"}</span></div><Link to={`/internal/dss/${item.kode}`}><Button className="w-full">Buka Skenario</Button></Link></CardContent></Card>)}</div>{!loading && !items.length && <p className="rounded-lg border p-8 text-center text-sm text-muted-foreground">Belum ada konfigurasi DSS. Jalankan sinkronisasi registry.</p>}</main>
}
