/* eslint-disable react-hooks/set-state-in-effect */
import { useCallback, useEffect, useState } from "react"
import { CheckCheck, RefreshCw } from "lucide-react"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  getInternalNotifications,
  markAllInternalNotificationsRead,
  markInternalNotificationRead,
  type InternalNotification,
} from "../../../lib/api"
import { useAuth } from "../../auth/AuthContext"

const severityClass: Record<InternalNotification["severity"], string> = {
  info: "border-blue-200 bg-blue-50 dark:border-blue-900 dark:bg-blue-950/30",
  success: "border-emerald-200 bg-emerald-50 dark:border-emerald-900 dark:bg-emerald-950/30",
  warning: "border-amber-200 bg-amber-50 dark:border-amber-900 dark:bg-amber-950/30",
  critical: "border-red-200 bg-red-50 dark:border-red-900 dark:bg-red-950/30",
}

export default function NotificationsPage() {
  const { session } = useAuth()
  const [items, setItems] = useState<InternalNotification[]>([])
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    if (!session) return
    setLoading(true)
    try {
      setItems(await getInternalNotifications(session.access_token))
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Notifikasi gagal dimuat.")
    } finally {
      setLoading(false)
    }
  }, [session])

  useEffect(() => { void load() }, [load])

  async function markRead(item: InternalNotification) {
    if (!session || item.is_read) return
    try {
      await markInternalNotificationRead(session.access_token, item.notification_id)
      setItems((current) => current.map((entry) => entry.notification_id === item.notification_id ? { ...entry, is_read: true, read_at: new Date().toISOString() } : entry))
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Notifikasi gagal diperbarui.")
    }
  }

  async function markAllRead() {
    if (!session) return
    try {
      await markAllInternalNotificationsRead(session.access_token)
      setItems((current) => current.map((item) => ({ ...item, is_read: true, read_at: new Date().toISOString() })))
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Notifikasi gagal diperbarui.")
    }
  }

  return <main className="grid gap-6 p-6">
    <div className="flex flex-wrap items-center justify-between gap-3">
      <div><h1 className="text-2xl font-semibold">Notifikasi Internal</h1><p className="text-sm text-muted-foreground">Pemberitahuan operasional dari marketplace, POS, dan warehouse.</p></div>
      <div className="flex gap-2"><Button variant="outline" onClick={() => void load()} disabled={loading}><RefreshCw className={loading ? "animate-spin" : ""} /> Refresh</Button><Button variant="outline" onClick={() => void markAllRead()}><CheckCheck /> Tandai semua dibaca</Button></div>
    </div>
    <Card><CardHeader><CardTitle>{items.filter((item) => !item.is_read).length} belum dibaca</CardTitle></CardHeader><CardContent className="grid gap-3">
      {loading ? <p className="text-sm text-muted-foreground">Memuat notifikasi...</p> : items.length === 0 ? <p className="py-8 text-center text-sm text-muted-foreground">Belum ada notifikasi.</p> : items.map((item) => <button type="button" key={item.notification_id} onClick={() => void markRead(item)} className={`rounded-lg border p-4 text-left transition-opacity ${severityClass[item.severity]} ${item.is_read ? "opacity-60" : ""}`}><div className="flex items-start justify-between gap-3"><div><p className="font-medium">{item.title}</p><p className="mt-1 text-sm">{item.message}</p></div><span className="shrink-0 text-xs uppercase text-muted-foreground">{item.severity}</span></div><p className="mt-2 text-xs text-muted-foreground">{new Date(item.created_at).toLocaleString("id-ID")}{!item.is_read && " · Belum dibaca"}</p></button>)}
    </CardContent></Card>
  </main>
}
