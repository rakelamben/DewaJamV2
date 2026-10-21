import { useEffect, useState } from "react"
import { Bell } from "lucide-react"
import { Link, useLocation } from "react-router"
import { getInternalUnreadCount } from "../lib/api"
import { useAuth } from "../src/auth/AuthContext"
import { Button } from "@/components/ui/button"
import { SidebarTrigger } from "@/components/ui/sidebar"
import { Separator } from "@/components/ui/separator"

export function SiteHeader() {
  const { pathname } = useLocation()
  const { session } = useAuth()
  const [unreadCount, setUnreadCount] = useState(0)

  const pageTitles: Record<string, string> = {
    "/internal": "Dashboard MIS",
    "/internal/mis": "Dashboard MIS",
    "/internal/pos": "POS",
    "/internal/warehouse": "Warehouse",
    "/internal/masterdata": "Master Data",
    "/internal/notifications": "Notifikasi",
    "/internal/activity-logs": "Activity Log",
    "/internal/messages": "Pesan Internal",
    "/internal/personnel": "Direktori Personnel",
    "/internal/documents": "Dokumen Internal",
    "/internal/workflows": "Workflow Approval",
    "/internal/correspondence": "Persuratan",
    "/internal/knowledge": "Knowledge Management",
    "/internal/masterdata/knowledge": "Master Data Knowledge",
  }

  useEffect(() => {
    if (!session) return
    void getInternalUnreadCount(session.access_token).then((result) => setUnreadCount(result.unread_count)).catch(() => setUnreadCount(0))
  }, [session, pathname])

  return (
    <header className="flex h-(--header-height) shrink-0 items-center gap-2 border-b transition-[width,height] ease-linear group-has-data-[collapsible=icon]/sidebar-wrapper:h-(--header-height)">
      <div className="flex w-full items-center gap-1 px-4 lg:gap-2 lg:px-6">
        <SidebarTrigger className="-ml-1" />
        <Separator
          orientation="vertical"
          className="mx-2 h-4 data-vertical:self-auto"
        />
        <h1 className="text-base font-medium">{pageTitles[pathname] ?? "Internal"}</h1>
        <Button variant="ghost" size="icon" className="relative ml-auto" aria-label="Notifikasi" render={<Link to="/internal/notifications" />}>
          <Bell /><span className="sr-only">Notifikasi</span>{unreadCount > 0 && <span className="absolute right-0 top-0 min-w-4 rounded-full bg-destructive px-1 text-[10px] leading-4 text-white">{unreadCount > 99 ? "99+" : unreadCount}</span>}
        </Button>
      </div>
    </header>
  )
}
