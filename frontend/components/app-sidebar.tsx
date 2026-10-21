import * as React from "react"

import { NavMain } from "@/components/nav-main"
import { NavUser } from "@/components/nav-user"
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar"
import { LayoutDashboardIcon, StoreIcon, WatchIcon, BoxIcon, NotebookTabsIcon, PackageIcon, BellIcon, ClipboardListIcon, UsersIcon, MessageSquareIcon, FileTextIcon, GitPullRequestIcon, MailIcon, BookOpenIcon, BarChart3Icon, ChartNoAxesCombinedIcon, WarehouseIcon } from "lucide-react"
import { useAuth } from "../src/auth/AuthContext"

const data = {
  navGroups: [
    {
      isGroup: false,
      items: [{ title: "Dashboard MIS", path: "/internal", icon: <LayoutDashboardIcon /> }],
    },
    {
      label: "Laporan MIS",
      items: [
        { title: "Sales Report", path: "/internal/mis/sales", icon: <BarChart3Icon /> },
        { title: "Profitability Report", path: "/internal/mis/profitability", icon: <ChartNoAxesCombinedIcon /> },
        { title: "Inventory Report", path: "/internal/mis/inventory", icon: <WarehouseIcon /> },
        { title: "KPI Management", path: "/internal/mis/kpi", icon: <ChartNoAxesCombinedIcon /> },
      ],
    },
    {
      label: "POS",
      items: [
        { title: "Input Transaksi", path: "/internal/pos/transaction", icon: <NotebookTabsIcon /> },
        { title: "Sales Harian", path: "/internal/pos/sales", icon: <NotebookTabsIcon /> },
      ],
    },
    {
      label: "Warehouse",
      items: [{ title: "Warehouse", path: "/internal/warehouse", icon: <BoxIcon /> }],
    },
    {
      label: "Master Data",
      items: [
        { title: "Master Data Produk", path: "/internal/masterdata/products", icon: <PackageIcon /> },
        { title: "Master Data Store", path: "/internal/masterdata/stores", icon: <StoreIcon /> },
        { title: "Master Data Knowledge", path: "/internal/masterdata/knowledge", icon: <BookOpenIcon /> },
      ],
    },
    {
      label: "OAS",
      items: [
        { title: "Notifikasi", path: "/internal/notifications", icon: <BellIcon /> },
        { title: "Activity Log", path: "/internal/activity-logs", icon: <ClipboardListIcon /> },
        { title: "Pesan Internal", path: "/internal/messages", icon: <MessageSquareIcon /> },
        { title: "Direktori Personnel", path: "/internal/personnel", icon: <UsersIcon /> },
        { title: "Dokumen Internal", path: "/internal/documents", icon: <FileTextIcon /> },
        { title: "Workflow Approval", path: "/internal/workflows", icon: <GitPullRequestIcon /> },
        { title: "Persuratan", path: "/internal/correspondence", icon: <MailIcon /> },
      ],
    },
    {
      label: "Knowledge",
      items: [{ title: "Knowledge Management", path: "/internal/knowledge", icon: <BookOpenIcon /> }],
    },
  ],
}
export function AppSidebar({ ...props }: React.ComponentProps<typeof Sidebar>) {
  const { profile } = useAuth()
  const canManageKnowledge = profile?.role === "admin" || profile?.role === "manager"
  const visibleGroups = data.navGroups.map((group) => ({ ...group, items: group.items.filter((item) => item.path !== "/internal/masterdata/knowledge" || canManageKnowledge) })).filter((group) => group.items.length > 0)
  const user = {
    name: profile?.name ?? "User internal",
    email: profile?.email ?? "",
    avatar: "",
  }

  return (
    <Sidebar collapsible="offcanvas" {...props}>
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton
              className="data-[slot=sidebar-menu-button]:p-1.5!"
              render={<a href="#" />}
            >
              <WatchIcon className="size-5!" />
              <span className="text-base font-semibold">Dewa Jam</span>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>
      <SidebarContent>
        <NavMain groups={visibleGroups} />
      </SidebarContent>
      <SidebarFooter>
        <NavUser user={user} />
      </SidebarFooter>
    </Sidebar>
  )
}
