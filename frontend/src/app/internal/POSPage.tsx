import { useEffect, useMemo, useState } from "react"
import { ArrowLeft, CheckCircle2, Minus, Plus, Printer, Search, ShoppingCart, Trash2 } from "lucide-react"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { useAuth } from "../../auth/AuthContext"
import {
  createPosTransaction,
  getPosProducts,
  type PosCartItem,
  type PosProduct,
  type PosTransaction,
} from "../../../lib/api"

const currency = new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 })
const formatCurrency = (value: number | string) => currency.format(Number(value))

export default function POSPage() {
  const { session } = useAuth()
  const [started, setStarted] = useState(false)
  const [buyerName, setBuyerName] = useState("")
  const [buyerPhone, setBuyerPhone] = useState("")
  const [products, setProducts] = useState<PosProduct[]>([])
  const [cart, setCart] = useState<PosCartItem[]>([])
  const [search, setSearch] = useState("")
  const [paymentMethod, setPaymentMethod] = useState("tunai")
  const [paidAmount, setPaidAmount] = useState("")
  const [checkout, setCheckout] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [completed, setCompleted] = useState<PosTransaction | null>(null)
  const [loadingProducts, setLoadingProducts] = useState(false)

  const total = useMemo(
    () => cart.reduce((sum, item) => sum + Number(item.product.harga) * item.qty, 0),
    [cart]
  )
  const totalItems = useMemo(() => cart.reduce((sum, item) => sum + item.qty, 0), [cart])
  const change = Math.max(0, Number(paidAmount || 0) - total)
  const filteredProducts = products.filter((product) => {
    const query = search.toLowerCase().trim()
    return !query || [product.nama_barang, product.kategori, product.brand].some((value) => value?.toLowerCase().includes(query))
  })

  useEffect(() => {
    if (!started || !session?.access_token) return
    void getPosProducts(session.access_token)
      .then(setProducts)
      .catch((error) => toast.error(error instanceof Error ? error.message : "Katalog produk gagal dimuat."))
      .finally(() => setLoadingProducts(false))
  }, [started, session?.access_token])

  function beginTransaction(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!buyerName.trim()) return
    setBuyerPhone(buyerPhone.trim() || "9999")
    setLoadingProducts(true)
    setStarted(true)
  }

  function addProduct(product: PosProduct) {
    if (product.stok < 1) return
    setCart((current) => {
      const existing = current.find((item) => item.product.product_id === product.product_id)
      if (!existing) return [...current, { product, qty: 1 }]
      if (existing.qty >= product.stok) {
        toast.error("Jumlah melebihi stok yang tersedia.")
        return current
      }
      return current.map((item) => item.product.product_id === product.product_id ? { ...item, qty: item.qty + 1 } : item)
    })
  }

  function changeQuantity(productId: string, delta: number) {
    setCart((current) => current.flatMap((item) => {
      if (item.product.product_id !== productId) return [item]
      const qty = Math.min(item.product.stok, item.qty + delta)
      return qty > 0 ? [{ ...item, qty }] : []
    }))
  }

  async function submitPayment(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!session?.access_token || !cart.length) return
    const paid = paymentMethod === "tunai" ? Number(paidAmount) : total
    if (!Number.isFinite(paid) || paid < total) {
      toast.error("Nominal pembayaran kurang dari total transaksi.")
      return
    }
    setSubmitting(true)
    try {
      const result = await createPosTransaction(session.access_token, {
        buyer_name: buyerName.trim(),
        buyer_phone: buyerPhone.trim() || "9999",
        items: cart.map((item) => ({ product_id: item.product.product_id, qty: item.qty })),
        payment_method: paymentMethod,
        paid_amount: paid,
      })
      setCompleted(result)
      setCart([])
      setCheckout(false)
      toast.success("Pembayaran berhasil dikonfirmasi.")
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Transaksi gagal diproses.")
    } finally {
      setSubmitting(false)
    }
  }

  function newTransaction() {
    setStarted(false)
    setCompleted(null)
    setBuyerName("")
    setBuyerPhone("")
    setPaymentMethod("tunai")
    setPaidAmount("")
  }

  if (!session) return null

  if (completed) {
    return <Receipt transaction={completed} onPrint={() => window.print()} onNew={newTransaction} />
  }

  if (!started) {
    return (
      <div className="mx-auto flex min-h-[calc(100dvh-var(--header-height)-3rem)] max-w-3xl items-center p-6 min-w-xl">
        <Card className="w-full">
          <CardHeader><CardTitle>Mulai Transaksi Customer</CardTitle></CardHeader>
          <CardContent>
            <form className="grid gap-4" onSubmit={beginTransaction}>
              <div className="grid gap-2"><Label htmlFor="buyer-name">Nama pembeli</Label><Input id="buyer-name" value={buyerName} onChange={(event) => setBuyerName(event.target.value)} required placeholder="Nama pembeli" /></div>
              <div className="grid gap-2"><Label htmlFor="buyer-phone">Nomor HP pembeli</Label><Input id="buyer-phone" value={buyerPhone} onChange={(event) => setBuyerPhone(event.target.value)} placeholder="Isi 9999 jika tidak bersedia" /></div>
              <Button type="submit">Mulai Input Transaksi</Button>
            </form>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="grid gap-4 p-4 xl:grid-cols-[minmax(0,1fr)_380px]">
      <section className="min-w-0">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-start gap-2"><Button variant="ghost" size="icon-sm" aria-label="Kembali ke input identitas" onClick={() => { setCheckout(false); setStarted(false) }}><ArrowLeft /></Button><div><h1 className="text-2xl font-semibold">Katalog Produk</h1><p className="text-sm text-muted-foreground">Pembeli: {buyerName} · {buyerPhone || "9999"}</p></div></div>
          <div className="relative w-full max-w-sm"><Search className="absolute left-3 top-2.5 size-4 text-muted-foreground" /><Input className="pl-9" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Cari produk..." /></div>
        </div>
        {loadingProducts ? <p>Memuat katalog produk...</p> : filteredProducts.length === 0 ? <Card><CardContent className="p-6 text-center text-muted-foreground">Produk tidak ditemukan.</CardContent></Card> : <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">{filteredProducts.map((product) => <ProductCard key={product.product_id} product={product} onAdd={() => addProduct(product)} />)}</div>}
      </section>
      <CartPanel cart={cart} total={total} totalItems={totalItems} onChange={changeQuantity} onRemove={(id) => setCart((current) => current.filter((item) => item.product.product_id !== id))} onCheckout={() => { setPaidAmount(paymentMethod === "tunai" ? String(total) : ""); setCheckout(true) }} />
      {checkout && <PaymentDialog total={total} method={paymentMethod} paidAmount={paidAmount} submitting={submitting} onMethodChange={(method) => { setPaymentMethod(method); if (method !== "tunai") setPaidAmount(String(total)) }} onPaidChange={setPaidAmount} onSubmit={submitPayment} onClose={() => setCheckout(false)} change={change} />}
    </div>
  )
}

function ProductCard({ product, onAdd }: { product: PosProduct; onAdd: () => void }) {
  return <Card className="overflow-hidden"><div className="flex h-32 items-center justify-center bg-muted">{product.gambar_url ? <img className="h-full w-full object-cover" src={product.gambar_url} alt={product.nama_barang} /> : <ShoppingCart className="size-10 text-muted-foreground" />}</div><CardContent className="grid gap-2 p-4"><div><p className="font-medium">{product.nama_barang}</p><p className="text-xs text-muted-foreground">{product.brand || product.kategori || "Produk"}</p></div><p className="font-semibold">{formatCurrency(product.harga)}</p><p className="text-xs text-muted-foreground">Stok: {product.stok}</p><Button size="sm" disabled={product.stok < 1} onClick={onAdd}>{product.stok < 1 ? "Habis" : "Tambah"}</Button></CardContent></Card>
}

function CartPanel({ cart, total, totalItems, onChange, onRemove, onCheckout }: { cart: PosCartItem[]; total: number; totalItems: number; onChange: (id: string, delta: number) => void; onRemove: (id: string) => void; onCheckout: () => void }) {
  return <Card className="h-fit xl:sticky xl:top-4"><CardHeader><CardTitle className="flex items-center justify-between"><span>Cart Checkout</span><span className="text-sm text-muted-foreground">{totalItems} item</span></CardTitle></CardHeader><CardContent className="grid gap-4">{cart.length === 0 ? <p className="text-sm text-muted-foreground">Belum ada produk.</p> : cart.map((item) => <div className="grid gap-2 border-b pb-3" key={item.product.product_id}><div className="flex justify-between gap-2"><span className="font-medium">{item.product.nama_barang}</span><button aria-label={`Hapus ${item.product.nama_barang}`} onClick={() => onRemove(item.product.product_id)}><Trash2 className="size-4 text-destructive" /></button></div><div className="flex items-center justify-between"><span className="text-sm">{formatCurrency(Number(item.product.harga) * item.qty)}</span><div className="flex items-center gap-2"><Button variant="outline" size="icon-xs" onClick={() => onChange(item.product.product_id, -1)}><Minus /></Button><span>{item.qty}</span><Button variant="outline" size="icon-xs" onClick={() => onChange(item.product.product_id, 1)}><Plus /></Button></div></div></div>)}<div className="flex justify-between border-t pt-3 font-semibold"><span>Total</span><span>{formatCurrency(total)}</span></div><Button disabled={!cart.length} onClick={onCheckout}>Checkout</Button></CardContent></Card>
}

function PaymentDialog({ total, method, paidAmount, submitting, onMethodChange, onPaidChange, onSubmit, onClose, change }: { total: number; method: string; paidAmount: string; submitting: boolean; onMethodChange: (method: string) => void; onPaidChange: (value: string) => void; onSubmit: (event: React.FormEvent<HTMLFormElement>) => void; onClose: () => void; change: number }) {
  return <div className="fixed inset-0 z-50 grid place-items-center bg-black/50 p-4"><Card className="w-full max-w-md"><CardHeader><CardTitle>Konfirmasi Pembayaran</CardTitle></CardHeader><CardContent><form className="grid gap-4" onSubmit={onSubmit}><div className="grid gap-2"><Label>Total belanja</Label><p className="text-2xl font-bold">{formatCurrency(total)}</p></div><div className="grid gap-2"><Label htmlFor="payment-method">Metode pembayaran</Label><select id="payment-method" className="h-9 rounded-lg border bg-background px-3 text-sm" value={method} onChange={(event) => onMethodChange(event.target.value)}><option value="tunai">Tunai</option><option value="QRIS">QRIS</option><option value="debit">Debit</option></select></div><div className="grid gap-2"><Label htmlFor="paid-amount">Nominal dibayar</Label><Input id="paid-amount" type="number" min={total} value={paidAmount} onChange={(event) => onPaidChange(event.target.value)} disabled={method !== "tunai"} required /></div>{method === "tunai" && <p className="flex justify-between text-sm"><span>Kembalian</span><strong>{formatCurrency(change)}</strong></p>}<div className="flex justify-end gap-2"><Button type="button" variant="outline" onClick={onClose}>Kembali</Button><Button type="submit" disabled={submitting}>{submitting ? "Memproses..." : "Konfirmasi Pembayaran"}</Button></div></form></CardContent></Card></div>
}

function Receipt({ transaction, onPrint, onNew }: { transaction: PosTransaction; onPrint: () => void; onNew: () => void }) {
  return <div className="mx-auto max-w-xl p-6"><Card className="print:border-0 print:shadow-none"><CardHeader className="text-center"><CheckCircle2 className="mx-auto size-12 text-green-600" /><CardTitle>Pembayaran Berhasil</CardTitle><p className="text-sm text-muted-foreground">{transaction.no_invoice}</p></CardHeader><CardContent className="grid gap-3"><div className="text-sm"><p>Pembeli: {transaction.buyer_name_snapshot}</p><p>No. HP: {transaction.buyer_phone_snapshot}</p><p>Metode: {transaction.payment_method}</p></div><div className="grid gap-2 border-y py-3">{transaction.items?.map((item) => <div className="flex justify-between text-sm" key={item.item_id}><span>{item.nama_barang_snapshot} × {item.qty}</span><span>{formatCurrency(item.subtotal)}</span></div>)}</div><div className="flex justify-between font-bold"><span>Total</span><span>{formatCurrency(transaction.total_harga)}</span></div><div className="flex justify-end gap-2 print:hidden"><Button variant="outline" onClick={onPrint}><Printer /> Cetak / Simpan PDF</Button><Button onClick={onNew}>Transaksi Baru</Button></div></CardContent></Card></div>
}
