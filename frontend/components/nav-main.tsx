import {
  SidebarGroup,
  SidebarGroupContent,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar"
import { Separator } from "@/components/ui/separator"
import { NavLink, useLocation } from "react-router";


export function NavMain({
  items,
}: {
  items: {
    title: string
    path: string
    icon?: React.ReactNode
  }[]
}) {
  const location = useLocation()
  const pathname = location.pathname.replace(/\/$/, "") || "/"

  return (
    <SidebarGroup>
      <SidebarGroupContent className="flex flex-col gap-2">
        <Separator />
        <SidebarMenu>
          {items.map((item) => (
            <SidebarMenuItem key={item.title}>
              <SidebarMenuButton
                isActive={
                  item.path === "/internal"
                    ? pathname === item.path
                    : pathname === item.path || pathname.startsWith(`${item.path}/`)
                }
                tooltip={item.title}
                render={
                  <NavLink
                    to={item.path}
                    end={item.path === "/internal"}
                  />
                }
              >
                {item.icon}
                <span>{item.title}</span>
              </SidebarMenuButton>
            </SidebarMenuItem>
          ))}
        </SidebarMenu>
      </SidebarGroupContent>
    </SidebarGroup>
  )
}
