import { useEffect, useState } from "react"
import { Link, useParams } from "react-router"
import { ArrowLeft } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { useAuth } from "../../../auth/AuthContext"
import { decideDssResult, getDssRun } from "../../../../lib/dss-api"
import type { DssRun } from "../../../../lib/dss-types"
import { toast } from "sonner"

function displayValue(value: unknown) {
  if (value === null || value === undefined || value === "") return "-"
  if (typeof value === "number") return Number.isInteger(value) ? String(value) : value.toFixed(2)
  return String(value)
}

export default function DssRunDetailPage() {
  const { runId } = useParams(); const { session, profile } = useAuth(); const [run, setRun] = useState<DssRun | null>(null)
  const canDecide = profile?.role === "admin" || profile?.role === "manager"
  async function load() { if (!session || !runId) return; try { setRun(await getDssRun(session.access_token, runId)) } catch (error) { toast.error(error instanceof Error ? error.message : "Run DSS gagal dimuat.") } }
  useEffect(() => { void load() }, [session, runId])
  async function decide(id: string, decision: "accepted" | "rejected") { if (!session) return; const note = window.prompt(decision === "rejected" ? "Alasan penolakan wajib diisi:" : "Catatan keputusan (opsional):", "") ?? ""; if (decision === "rejected" && !note.trim()) return; try { await decideDssResult(session.access_token, id, decision, note || null); toast.success("Keputusan tersimpan."); await load() } catch (error) { toast.error(error instanceof Error ? error.message : "Keputusan gagal disimpan.") } }
  const recommendationKeys = Array.from(new Set((run?.results ?? []).flatMap((item) => Object.keys(item.recommendation)))).sort()
  return <main className="grid gap-6 p-6"><div><Link className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground" to={`/internal/dss/${run?.scenario ?? "RESTOCK"}`}><ArrowLeft className="size-4" /> Kembali</Link><h1 className="mt-2 text-2xl font-semibold">Detail Run DSS</h1><p className="text-sm text-muted-foreground">{run?.scenario} · {run?.persisted ? "Tersimpan" : "Simulasi"}</p></div>{run && <><div className="flex gap-2"><Badge variant="outline">CR {Number(run.weight_set.cr).toFixed(4)}</Badge><Badge variant="secondary">{run.results.length} hasil</Badge></div>{run.warnings.map((warning, index) => <div className="rounded border border-amber-300 bg-amber-50 p-3 text-sm" key={index}>{String(warning.pesan ?? "Peringatan")}</div>)}<Card><CardHeader><CardTitle>Hasil rekomendasi</CardTitle></CardHeader><CardContent className="overflow-x-auto"><table className="w-full text-sm"><thead><tr className="border-b text-left"><th className="p-2">Rank</th><th className="p-2">Alternatif</th><th className="p-2">Skor</th><th className="p-2">Status</th>{recommendationKeys.map((key) => <th className="p-2" key={key}>{key}</th>)}<th className="p-2">Keputusan</th><th className="p-2">Aksi</th></tr></thead><tbody>{run.results.map((item) => <tr className="border-b" key={item.result_id ?? item.id}><td className="p-2">{item.ranking}</td><td className="p-2">{item.label}</td><td className="p-2">{Number(item.skor).toFixed(4)}</td><td className="p-2"><Badge variant="outline">{item.status}</Badge></td>{recommendationKeys.map((key) => <td className="p-2 text-xs" key={key}>{displayValue(item.recommendation[key])}</td>)}<td className="p-2">{item.decision ?? "pending"}</td><td className="flex gap-2 p-2">{canDecide && item.result_id && item.decision === "pending" && <><button className="text-green-700 hover:underline" onClick={() => void decide(item.result_id!, "accepted")}>Terima</button><button className="text-red-700 hover:underline" onClick={() => void decide(item.result_id!, "rejected")}>Tolak</button></>}</td></tr>)}</tbody></table></CardContent></Card></>}</main>
}
