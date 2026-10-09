import { Separator } from "@/components/ui/separator"
import { SidebarTrigger } from "@/components/ui/sidebar"
import { useLocation } from "react-router"

export function SiteHeader() {
  const { pathname } = useLocation()

  const pageTitles: Record<string, string> = {
    "/internal": "Dashboard",
    "/internal/pos": "POS",
    "/internal/warehouse": "Warehouse",
    "/internal/masterdata": "Master Data",
  }

  return (
    <header className="flex h-(--header-height) shrink-0 items-center gap-2 border-b transition-[width,height] ease-linear group-has-data-[collapsible=icon]/sidebar-wrapper:h-(--header-height)">
      <div className="flex w-full items-center gap-1 px-4 lg:gap-2 lg:px-6">
        <SidebarTrigger className="-ml-1" />
        <Separator
          orientation="vertical"
          className="mx-2 h-4 data-vertical:self-auto"
        />
        <h1 className="text-base font-medium">{pageTitles[pathname] ?? "Internal"}</h1>
      </div>
    </header>
  )
}
