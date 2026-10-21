/* eslint-disable react-hooks/set-state-in-effect */
import { useCallback, useEffect, useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { toast } from "sonner"
import { createCorrespondence, getCorrespondences, type Correspondence } from "../../../lib/api"
import { useAuth } from "../../auth/AuthContext"

export default function CorrespondencePage() {
  const { session } = useAuth()
  const [items, setItems] = useState<Correspondence[]>([])
  const [type, setType] = useState<"masuk" | "keluar">("masuk")
  const [subject, setSubject] = useState("")
  const [origin, setOrigin] = useState("")
  const [saving, setSaving] = useState(false)
  const load = useCallback(async () => { if (!session) return; try { setItems(await getCorrespondences(session.access_token)) } catch (error) { toast.error(error instanceof Error ? error.message : "Surat gagal dimuat.") } }, [session])
  useEffect(() => { void load() }, [load])
  async function submit(event: React.FormEvent) { event.preventDefault(); if (!session) return; setSaving(true); try { await createCorrespondence(session.access_token, { tipe: type, perihal: subject, asal_tujuan: origin, sifat_surat: "biasa", status: type === "masuk" ? "dicatat" : "draft" }); setSubject(""); setOrigin(""); await load(); toast.success("Surat berhasil dicatat.") } catch (error) { toast.error(error instanceof Error ? error.message : "Surat gagal disimpan.") } finally { setSaving(false) } }
  return <main className="grid gap-6 p-6"><div><h1 className="text-2xl font-semibold">Persuratan</h1><p className="text-sm text-muted-foreground">Kelola surat masuk, surat keluar, dan disposisi.</p></div><div className="grid gap-6 lg:grid-cols-[1fr_360px]"><Card><CardHeader><CardTitle>Daftar surat</CardTitle></CardHeader><CardContent className="grid gap-3">{items.length === 0 ? <p className="text-sm text-muted-foreground">Belum ada surat.</p> : items.map((item) => <div className="rounded-lg border p-4" key={item.correspondence_id}><div className="flex justify-between gap-3"><div><p className="font-medium">{item.nomor_agenda} · {item.perihal}</p><p className="text-sm text-muted-foreground">{item.tipe} · {item.asal_tujuan}</p></div><span className="text-xs uppercase text-muted-foreground">{item.status}</span></div></div>)}</CardContent></Card><Card><CardHeader><CardTitle>Catat surat</CardTitle></CardHeader><CardContent><form className="grid gap-4" onSubmit={submit}><div className="grid gap-2"><Label>Tipe</Label><select className="h-9 rounded-lg border bg-background px-3 text-sm" value={type} onChange={(event) => setType(event.target.value as "masuk" | "keluar")}><option value="masuk">Surat masuk</option><option value="keluar">Surat keluar</option></select></div><div className="grid gap-2"><Label>Perihal</Label><Input value={subject} onChange={(event) => setSubject(event.target.value)} required /></div><div className="grid gap-2"><Label>Asal/Tujuan</Label><Input value={origin} onChange={(event) => setOrigin(event.target.value)} required /></div><Button disabled={saving}>{saving ? "Menyimpan..." : "Simpan Surat"}</Button></form></CardContent></Card></div></main>
}
