/* eslint-disable react-hooks/set-state-in-effect */
import { useEffect, useState, type FormEvent } from "react"
import { Link, useNavigate } from "react-router"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { MarketplaceFooter, MarketplaceHeader } from "@/components/marketplace-header"
import { updateCustomerProfile } from "../../../lib/api"
import { useCustomerAuth } from "../../auth/CustomerAuthContext"

export default function ProfilePage() {
  const navigate = useNavigate(); const { profile, session, loading, refresh, signOut } = useCustomerAuth(); const [form, setForm] = useState({ nama: "", no_hp: "" }); const [saving, setSaving] = useState(false)
  useEffect(() => { if (!loading && !profile) navigate("/login", { replace: true }); if (profile) setForm({ nama: profile.nama, no_hp: profile.no_hp }) }, [loading, navigate, profile])
  async function submit(event: FormEvent) { event.preventDefault(); if (!session) return; setSaving(true); try { await updateCustomerProfile(session.access_token, form); await refresh(); toast.success("Profil diperbarui.") } catch (error) { toast.error(error instanceof Error ? error.message : "Profil gagal diperbarui.") } finally { setSaving(false) } }
  if (!profile) return null
  return <><MarketplaceHeader /><main className="mx-auto max-w-2xl px-4 py-8"><h1 className="text-3xl font-semibold">Profil Saya</h1><Card className="mt-6"><CardHeader><CardTitle>Data customer</CardTitle></CardHeader><CardContent><form className="grid gap-4" onSubmit={submit}><div className="grid gap-2"><Label>Email</Label><Input value={profile.email ?? "-"} disabled /></div><div className="grid gap-2"><Label htmlFor="nama">Nama</Label><Input id="nama" value={form.nama} onChange={(event) => setForm({ ...form, nama: event.target.value })} required /></div><div className="grid gap-2"><Label htmlFor="no_hp">Nomor HP</Label><Input id="no_hp" value={form.no_hp} onChange={(event) => setForm({ ...form, no_hp: event.target.value })} required /></div><div className="flex flex-wrap gap-2"><Button disabled={saving}>{saving ? "Menyimpan..." : "Simpan Perubahan"}</Button><Button type="button" variant="outline" onClick={() => navigate("/profile/addresses")}>Kelola Alamat</Button><Button type="button" variant="ghost" onClick={() => void signOut().then(() => navigate("/"))}>Logout</Button></div></form></CardContent></Card><Link className="mt-4 inline-block text-sm text-muted-foreground hover:underline" to="/orders">Lihat pesanan saya</Link></main><MarketplaceFooter /></>
}
