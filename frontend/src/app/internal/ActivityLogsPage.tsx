import { useEffect, useState } from "react"
import { toast } from "sonner"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { getActivityLogs, type ActivityLog } from "../../../lib/api"
import { useAuth } from "../../auth/AuthContext"

export default function ActivityLogsPage() {
  const { session, profile } = useAuth()
  const [logs, setLogs] = useState<ActivityLog[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!session || !["admin", "manager"].includes(profile?.role ?? "")) return
    void getActivityLogs(session.access_token, { limit: 200 }).then(setLogs).catch((error) => toast.error(error instanceof Error ? error.message : "Activity log gagal dimuat.")).finally(() => setLoading(false))
  }, [session, profile?.role])

  if (!profile || !["admin", "manager"].includes(profile.role)) return <main className="grid min-h-96 place-items-center p-6"><p className="text-sm text-muted-foreground">Anda tidak memiliki akses ke activity log.</p></main>

  return <main className="grid gap-6 p-6"><div><h1 className="text-2xl font-semibold">Activity Log</h1><p className="text-sm text-muted-foreground">Riwayat aktivitas penting sistem internal.</p></div><Card><CardHeader><CardTitle>Aktivitas terbaru</CardTitle></CardHeader><CardContent>{loading ? <p>Memuat activity log...</p> : logs.length === 0 ? <p className="py-8 text-center text-sm text-muted-foreground">Belum ada aktivitas.</p> : <div className="overflow-x-auto"><table className="w-full text-left text-sm"><thead><tr className="border-b text-muted-foreground"><th className="p-3">Waktu</th><th className="p-3">Modul</th><th className="p-3">Aksi</th><th className="p-3">Status</th><th className="p-3">Deskripsi</th></tr></thead><tbody>{logs.map((log) => <tr className="border-b last:border-0" key={log.activity_id}><td className="whitespace-nowrap p-3">{new Date(log.created_at).toLocaleString("id-ID")}</td><td className="p-3">{log.module}</td><td className="p-3">{log.action}</td><td className="p-3">{log.status}</td><td className="p-3">{log.description}</td></tr>)}</tbody></table></div>}</CardContent></Card></main>
}
