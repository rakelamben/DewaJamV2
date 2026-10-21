import { useEffect, useState } from "react"
import { Link } from "react-router"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { MarketplaceFooter, MarketplaceHeader } from "@/components/marketplace-header"
import { createCustomerAddress, deleteCustomerAddress, getCustomerAddresses, updateCustomerAddress, type CustomerAddress } from "../../../lib/api"
import { getSupabaseClient } from "../../../lib/supabase"

const blank = { label: "Rumah", recipient_name: "", recipient_phone: "", address: "", is_default: false }
export default function AddressPage() {
  const [token, setToken] = useState<string | null>(null); const [addresses, setAddresses] = useState<CustomerAddress[]>([]); const [form, setForm] = useState(blank); const [editing, setEditing] = useState<string | null>(null)
  useEffect(() => { void getSupabaseClient().auth.getSession().then(({ data }) => { if (data.session) { setToken(data.session.access_token); void getCustomerAddresses(data.session.access_token).then(setAddresses) } }) }, [])
  async function save() { if (!token) return; try { const address = editing ? await updateCustomerAddress(token, editing, form) : await createCustomerAddress(token, form); setAddresses((current) => editing ? current.map((item) => item.address_id === editing ? address : item) : [address, ...current]); setEditing(null); setForm(blank); toast.success("Alamat tersimpan.") } catch (error) { toast.error(error instanceof Error ? error.message : "Alamat gagal disimpan.") } }
  async function remove(id: string) { if (!token) return; try { await deleteCustomerAddress(token, id); setAddresses((current) => current.filter((item) => item.address_id !== id)) } catch (error) { toast.error(error instanceof Error ? error.message : "Alamat gagal dihapus.") } }
  return <><MarketplaceHeader /><main className="mx-auto max-w-3xl px-4 py-8"><Link to="/profile" className="text-sm text-muted-foreground">← Kembali ke profil</Link><h1 className="mt-6 text-3xl font-semibold">Alamat Saya</h1><div className="mt-6 grid gap-4">{addresses.map((item) => <Card key={item.address_id}><CardContent className="flex flex-wrap justify-between gap-4 p-5"><div><strong>{item.label}</strong>{item.is_default && <span className="ml-2 rounded bg-primary/10 px-2 py-1 text-xs">Default</span>}<p>{item.recipient_name} · {item.recipient_phone}</p><p className="text-sm text-muted-foreground">{item.address}</p></div><div className="flex gap-2"><Button variant="outline" size="sm" onClick={() => { setEditing(item.address_id); setForm(item) }}>Edit</Button><Button variant="destructive" size="sm" onClick={() => void remove(item.address_id)}>Hapus</Button></div></CardContent></Card>)}<Card><CardContent className="grid gap-3 p-5"><h2 className="font-semibold">{editing ? "Edit alamat" : "Tambah alamat"}</h2>{["label", "recipient_name", "recipient_phone", "address"].map((field) => <Input key={field} placeholder={field} value={form[field as keyof typeof form] as string} onChange={(event) => setForm({ ...form, [field]: event.target.value })} />)}<label className="flex gap-2 text-sm"><input type="checkbox" checked={form.is_default} onChange={(event) => setForm({ ...form, is_default: event.target.checked })} /> Jadikan alamat default</label><Button onClick={() => void save()}>Simpan</Button></CardContent></Card></div></main><MarketplaceFooter /></>
}
