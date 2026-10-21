import { useState } from "react"
import { Link, useNavigate } from "react-router"
import { ArrowLeft, Minus, Plus, Trash2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { MarketplaceFooter, MarketplaceHeader } from "@/components/marketplace-header"
import { CustomerLoginDialog } from "@/components/customer-login-dialog"
import { useMarketplaceCart } from "../../lib/marketplace"
import { useCustomerAuth } from "../../auth/CustomerAuthContext"

const currency = new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 })

export default function CartPage() {
  const navigate = useNavigate()
  const { items, count, change, remove, clear } = useMarketplaceCart()
  const { profile, loading } = useCustomerAuth()
  const [loginDialog, setLoginDialog] = useState(true)
  const total = items.reduce((sum, item) => sum + Number(item.product.harga) * item.qty, 0)
  if (!loading && !profile) return <><MarketplaceHeader /><main className="mx-auto max-w-3xl p-8"><Card><CardContent className="grid gap-4 p-10 text-center"><p>Login diperlukan untuk membuka cart.</p><Button onClick={() => setLoginDialog(true)}>Login</Button></CardContent></Card></main><MarketplaceFooter /><CustomerLoginDialog open={loginDialog} from="/cart" onClose={() => setLoginDialog(false)} /></>
  return <><MarketplaceHeader /><main className="mx-auto max-w-6xl px-4 py-8"><Link to="/" className="inline-flex items-center gap-2 text-sm text-muted-foreground"><ArrowLeft /> Lanjut belanja</Link><h1 className="mt-6 text-3xl font-semibold">Keranjang Anda</h1>{items.length === 0 ? <Card className="mt-8"><CardContent className="grid place-items-center gap-4 p-12 text-center"><p className="text-muted-foreground">Keranjang Anda masih kosong.</p><Button onClick={() => navigate("/")}>Mulai Belanja</Button></CardContent></Card> : <div className="mt-8 grid gap-6 lg:grid-cols-[1fr_340px]"><Card><CardHeader><CardTitle>{count} item</CardTitle></CardHeader><CardContent className="grid gap-4">{items.map((item) => <div className="flex gap-4 border-b pb-4 last:border-0" key={item.product.product_id}><div className="flex size-20 items-center justify-center rounded-lg bg-muted">{item.product.gambar_url && <img src={item.product.gambar_url} alt="" className="h-full w-full rounded-lg object-cover" />}</div><div className="min-w-0 flex-1"><p className="font-medium">{item.product.nama_barang}</p><p className="text-sm text-muted-foreground">{currency.format(Number(item.product.harga))}</p><div className="mt-2 flex items-center gap-2"><Button variant="outline" size="icon-xs" onClick={() => change(item.product.product_id, item.qty - 1)}><Minus /></Button><span>{item.qty}</span><Button variant="outline" size="icon-xs" onClick={() => change(item.product.product_id, Math.min(item.qty + 1, item.product.stok))}><Plus /></Button></div></div><div className="text-right"><p className="font-semibold">{currency.format(Number(item.product.harga) * item.qty)}</p><button className="mt-2 text-destructive" onClick={() => remove(item.product.product_id)} aria-label="Hapus produk"><Trash2 className="size-4" /></button></div></div>)}<Button variant="ghost" className="w-fit text-destructive" onClick={clear}>Kosongkan cart</Button></CardContent></Card><Card className="h-fit lg:sticky lg:top-24"><CardHeader><CardTitle>Ringkasan</CardTitle></CardHeader><CardContent className="grid gap-4"><div className="flex justify-between"><span>Subtotal</span><strong>{currency.format(total)}</strong></div><p className="text-xs text-muted-foreground">Ongkir dan metode pembayaran dipilih saat checkout.</p><Button onClick={() => navigate("/checkout")}>Checkout</Button></CardContent></Card></div>}</main><MarketplaceFooter /></>
}
