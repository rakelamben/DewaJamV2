import { useEffect, useMemo, useState, type FormEvent } from "react"
import { ArrowLeft } from "lucide-react"
import { Link, useNavigate } from "react-router"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { MarketplaceFooter, MarketplaceHeader } from "@/components/marketplace-header"
import { createCustomerAddress, createMarketplaceOrder, getCustomerAddresses, getMarketplaceStores, type CustomerAddress } from "../../../lib/api"
import { getSupabaseClient } from "../../../lib/supabase"
import { useMarketplaceCart } from "../../lib/marketplace"

const currency = new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 })
type Fulfillment = "pickup" | "delivery"
type Payment = "virtual_account" | "e_wallet" | "store_payment"
type Store = { store_id: string; name: string; address: string; opening_hours: string | null }

export default function CheckoutPage() {
  const navigate = useNavigate()
  const { items, count, clear } = useMarketplaceCart()
  const [token, setToken] = useState<string | null>(null)
  const [addresses, setAddresses] = useState<CustomerAddress[]>([])
  const [stores, setStores] = useState<Store[]>([])
  const [addressId, setAddressId] = useState("")
  const [storeId, setStoreId] = useState("")
  const [fulfillment, setFulfillment] = useState<Fulfillment>("pickup")
  const [payment, setPayment] = useState<Payment>("e_wallet")
  const [loading, setLoading] = useState(false)
  const [successOrder, setSuccessOrder] = useState<{ transaction_id: string; no_invoice: string; total_harga: string } | null>(null)
  const [newAddress, setNewAddress] = useState(false)
  const [addressForm, setAddressForm] = useState({ label: "Rumah", recipient_name: "", recipient_phone: "", address: "" })
  const total = useMemo(() => items.reduce((sum, item) => sum + Number(item.product.harga) * item.qty, 0), [items])

  useEffect(() => {
    void getSupabaseClient().auth.getSession().then(({ data }) => {
      if (!data.session) {
        navigate("/login", { state: { from: "/checkout" }, replace: true })
        return
      }
      setToken(data.session.access_token)
      void getCustomerAddresses(data.session.access_token).then((rows) => {
        setAddresses(rows)
        setAddressId(rows.find((row) => row.is_default)?.address_id ?? rows[0]?.address_id ?? "")
      })
      void getMarketplaceStores().then((rows) => {
        setStores(rows)
        setStoreId(rows[0]?.store_id ?? "")
      })
    })
  }, [navigate])

  function selectFulfillment(next: Fulfillment) {
    setFulfillment(next)
    if (next === "pickup") {
      setAddressId("")
      if (payment === "store_payment" || payment === "e_wallet" || payment === "virtual_account") return
      setPayment("e_wallet")
    } else {
      setStoreId("")
      if (payment === "store_payment") setPayment("e_wallet")
    }
  }

  async function saveAddress() {
    if (!token) return
    try {
      const address = await createCustomerAddress(token, addressForm)
      setAddresses((current) => [address, ...current])
      setAddressId(address.address_id)
      setNewAddress(false)
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Alamat gagal disimpan.")
    }
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!token || !items.length) return
    if (fulfillment === "pickup" && !storeId) {
      toast.error("Pilih store pickup terlebih dahulu.")
      return
    }
    if (fulfillment === "delivery" && !addressId) {
      toast.error("Pilih alamat delivery terlebih dahulu.")
      return
    }
    if (fulfillment === "delivery" && payment === "store_payment") {
      toast.error("Store payment hanya tersedia untuk pickup.")
      return
    }
    setLoading(true)
    try {
      const order = await createMarketplaceOrder(token, {
        items: items.map((item) => ({ product_id: item.product.product_id, qty: item.qty })),
        address_id: fulfillment === "delivery" ? addressId : undefined,
        store_id: fulfillment === "pickup" ? storeId : undefined,
        fulfillment_method: fulfillment,
        payment_method: payment,
        shipping_fee: 0,
      })
      clear()
      if (payment === "store_payment") {
        setSuccessOrder(order)
      } else {
        navigate(`/payment/pending/${order.transaction_id}`, { replace: true })
      }
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Checkout gagal.")
    } finally {
      setLoading(false)
    }
  }

  if (successOrder) return <><MarketplaceHeader /><main className="mx-auto max-w-xl px-4 py-16"><Card><CardHeader><CardTitle>Berhasil memesan</CardTitle></CardHeader><CardContent className="grid gap-4"><p className="text-muted-foreground">Pesanan berhasil dibuat dan pembayaran dilakukan di toko.</p><div className="rounded-lg bg-muted p-4 text-sm"><p>Invoice: <strong>{successOrder.no_invoice}</strong></p><p className="mt-1">Total: <strong>{currency.format(Number(successOrder.total_harga))}</strong></p></div><div className="flex flex-wrap gap-2"><Button onClick={() => navigate(`/orders/${successOrder.transaction_id}`, { replace: true })}>Lihat Pesanan</Button><Button variant="outline" onClick={() => navigate("/", { replace: true })}>Kembali Belanja</Button></div></CardContent></Card></main><MarketplaceFooter /></>

  if (!items.length) return <><MarketplaceHeader /><main className="mx-auto max-w-3xl p-8"><Card><CardContent className="grid gap-4 p-10 text-center"><p>Cart masih kosong.</p><Button onClick={() => navigate("/")}>Kembali Belanja</Button></CardContent></Card></main><MarketplaceFooter /></>

  return <><MarketplaceHeader /><main className="mx-auto max-w-6xl px-4 py-8"><Link to="/cart" className="inline-flex items-center gap-2 text-sm text-muted-foreground"><ArrowLeft /> Kembali ke cart</Link><h1 className="mt-6 text-3xl font-semibold">Checkout</h1><div className="mt-8 grid gap-6 lg:grid-cols-[1fr_340px]"><form id="checkout-form" className="grid gap-6" onSubmit={submit}>
    <Card><CardHeader><CardTitle>1. Fulfillment</CardTitle></CardHeader><CardContent className="grid gap-3"><label className="flex cursor-pointer gap-3 rounded-lg border p-4"><input type="radio" checked={fulfillment === "pickup"} onChange={() => selectFulfillment("pickup")} /><span><strong>Pickup di toko</strong><br /><small className="text-muted-foreground">Ambil pesanan di store pilihan Anda.</small></span></label>{fulfillment === "pickup" && <div className="grid gap-2"><Label htmlFor="store">Store pickup</Label><select id="store" className="h-9 rounded-lg border bg-background px-3 text-sm" value={storeId} onChange={(event) => setStoreId(event.target.value)} required>{stores.length === 0 && <option value="">Tidak ada store aktif</option>}{stores.map((store) => <option key={store.store_id} value={store.store_id}>{store.name} — {store.address}{store.opening_hours ? ` (${store.opening_hours})` : ""}</option>)}</select></div>}<label className="flex cursor-pointer gap-3 rounded-lg border p-4"><input type="radio" checked={fulfillment === "delivery"} onChange={() => selectFulfillment("delivery")} /><span><strong>Delivery</strong><br /><small className="text-muted-foreground">Pesanan dikirim ke alamat Anda.</small></span></label></CardContent></Card>
    {fulfillment === "delivery" && <Card><CardHeader><CardTitle>2. Alamat delivery</CardTitle></CardHeader><CardContent className="grid gap-3">{addresses.map((address) => <label className="flex cursor-pointer gap-3 rounded-lg border p-4" key={address.address_id}><input type="radio" checked={addressId === address.address_id} onChange={() => setAddressId(address.address_id)} /><span><strong>{address.label}</strong><br />{address.recipient_name} · {address.recipient_phone}<br /><small className="text-muted-foreground">{address.address}</small></span></label>)}<Button type="button" variant="outline" className="w-fit" onClick={() => setNewAddress((current) => !current)}>+ Tambah alamat</Button>{newAddress && <div className="grid gap-3 rounded-lg bg-muted/50 p-4"><Input placeholder="Label alamat" value={addressForm.label} onChange={(event) => setAddressForm({ ...addressForm, label: event.target.value })} required /><Input placeholder="Nama penerima" value={addressForm.recipient_name} onChange={(event) => setAddressForm({ ...addressForm, recipient_name: event.target.value })} required /><Input placeholder="Nomor HP" value={addressForm.recipient_phone} onChange={(event) => setAddressForm({ ...addressForm, recipient_phone: event.target.value })} required /><textarea className="min-h-20 rounded-lg border bg-background p-3 text-sm" placeholder="Alamat lengkap" value={addressForm.address} onChange={(event) => setAddressForm({ ...addressForm, address: event.target.value })} required /><Button type="button" onClick={() => void saveAddress()}>Simpan Alamat</Button></div>}</CardContent></Card>}
    <Card><CardHeader><CardTitle>{fulfillment === "pickup" ? "2" : "3"}. Pembayaran</CardTitle></CardHeader><CardContent className="grid gap-3"><Label htmlFor="payment">Metode pembayaran</Label><select id="payment" className="h-9 rounded-lg border bg-background px-3 text-sm" value={payment} onChange={(event) => setPayment(event.target.value as Payment)}><option value="virtual_account">Virtual Account</option><option value="e_wallet">E-wallet</option>{fulfillment === "pickup" && <option value="store_payment">Bayar di toko</option>}</select></CardContent></Card>
  </form><Card className="h-fit lg:sticky lg:top-24"><CardHeader><CardTitle>Ringkasan Pesanan</CardTitle></CardHeader><CardContent className="grid gap-4"><p className="text-sm text-muted-foreground">{count} item · {fulfillment === "pickup" ? "Pickup" : "Delivery"}</p>{items.map((item) => <div className="flex justify-between gap-3 text-sm" key={item.product.product_id}><span>{item.product.nama_barang} × {item.qty}</span><span>{currency.format(Number(item.product.harga) * item.qty)}</span></div>)}<div className="flex justify-between border-t pt-4 font-semibold"><span>Total</span><span>{currency.format(total)}</span></div><Button type="submit" form="checkout-form" disabled={loading}>{loading ? "Membuat pesanan..." : "Buat Pesanan"}</Button></CardContent></Card></div></main><MarketplaceFooter /></>
}
