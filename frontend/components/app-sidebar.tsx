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
import { LayoutDashboardIcon, FolderIcon, WatchIcon, BoxIcon, NotebookTabsIcon } from "lucide-react"

const data = {
  user: {
    name: "shadcn",
    email: "m@example.com",
    avatar: "/avatars/shadcn.jpg",
  },
  navMain: [
    {
      title: "Dashboard",
      path: "/internal",
      icon: (
        <LayoutDashboardIcon
        />
      ),
    },
    {
      title: "POS",
      path: "/internal/pos",
      icon: (
        <NotebookTabsIcon
        />
      ),
    },
    {
      title: "Warehouse",
      path: "/internal/warehouse",
      icon: (
        <BoxIcon
        />
      ),
    },
    {
      title: "Master Data",
      path: "/internal/masterdata",
      icon: (
        <FolderIcon
        />
      ),
    },

  ],
  
  
  
}
export function AppSidebar({ ...props }: React.ComponentProps<typeof Sidebar>) {
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
        <NavMain items={data.navMain} />
      </SidebarContent>
      <SidebarFooter>
        <NavUser user={data.user} />
      </SidebarFooter>
    </Sidebar>
  )
}
