import { useEffect, useState } from "react"
import { Search } from "lucide-react"
import { toast } from "sonner"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { getInternalPersonnel, type InternalPersonnel } from "../../../lib/api"
import { useAuth } from "../../auth/AuthContext"

export default function PersonnelPage() {
  const { session } = useAuth()
  const [items, setItems] = useState<InternalPersonnel[]>([])
  const [search, setSearch] = useState("")
  useEffect(() => { if (!session) return; void getInternalPersonnel(session.access_token, search ? { search } : undefined).then(setItems).catch((error) => toast.error(error instanceof Error ? error.message : "Direktori gagal dimuat.")) }, [session, search])
  return <main className="grid gap-6 p-6"><div><h1 className="text-2xl font-semibold">Direktori Personnel</h1><p className="text-sm text-muted-foreground">Daftar personel internal Dewa Jam.</p></div><Card><CardHeader><CardTitle>Personnel</CardTitle><div className="relative max-w-sm"><Search className="absolute left-3 top-2.5 size-4 text-muted-foreground" /><Input className="pl-9" placeholder="Cari nama..." value={search} onChange={(event) => setSearch(event.target.value)} /></div></CardHeader><CardContent><div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">{items.map((person) => <div className="rounded-lg border p-4" key={person.personnel_id}><p className="font-medium">{person.nama}</p><p className="mt-1 text-sm text-muted-foreground">{person.role || person.personnel_type}</p><p className="mt-2 text-xs text-muted-foreground">Status: {person.status}</p></div>)}{items.length === 0 && <p className="py-8 text-sm text-muted-foreground">Personnel tidak ditemukan.</p>}</div></CardContent></Card></main>
}
