import {
  SidebarGroup,
  SidebarGroupLabel,
  SidebarGroupContent,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar"
import { NavLink, useLocation } from "react-router";


export function NavMain({
  groups,
}: {
  groups: {
    isGroup?: boolean
    label?: string
    items: {
      title: string
      path: string
      icon?: React.ReactNode
    }[]
  }[]
}) {
  const location = useLocation()
  const pathname = location.pathname.replace(/\/$/, "") || "/"

  return (
    <>
      {groups.map((group) =>
        group.isGroup !== false ? (
          <SidebarGroup key={group.label}>
            <SidebarGroupLabel>{group.label}</SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>
                {group.items.map((item) => (
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
        ) : (
          <SidebarMenu>
            {group.items.map((item) => (
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
        )
      )}
    </>
  )
}
