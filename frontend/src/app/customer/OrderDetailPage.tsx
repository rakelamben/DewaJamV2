import { useEffect, useState } from "react"
import { Link, useNavigate, useParams } from "react-router"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { MarketplaceFooter, MarketplaceHeader } from "@/components/marketplace-header"
import { confirmCustomerPayment, getCustomerOrder, type MarketplaceOrder } from "../../../lib/api"
import { getSupabaseClient } from "../../../lib/supabase"

const currency = new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 })

export default function OrderDetailPage() {
  const { transactionId = "" } = useParams(); const navigate = useNavigate(); const [order, setOrder] = useState<MarketplaceOrder | null>(null); const [loading, setLoading] = useState(true); const [confirming, setConfirming] = useState(false)
  useEffect(() => { void getSupabaseClient().auth.getSession().then(async ({ data }) => { if (!data.session) { navigate("/login", { replace: true }); return } try { setOrder(await getCustomerOrder(data.session.access_token, transactionId)) } finally { setLoading(false) } }) }, [navigate, transactionId])
  async function confirmPayment() { const { data } = await getSupabaseClient().auth.getSession(); if (!data.session || !order) return; setConfirming(true); try { setOrder(await confirmCustomerPayment(data.session.access_token, order.transaction_id)) } finally { setConfirming(false) } }
  return <><MarketplaceHeader /><main className="mx-auto max-w-3xl px-4 py-8"><Link to="/orders" className="text-sm text-muted-foreground hover:underline">← Kembali ke pesanan</Link>{loading ? <Card className="mt-6 h-96 animate-pulse bg-muted" /> : !order ? <p className="mt-6">Pesanan tidak ditemukan.</p> : <Card className="mt-6"><CardHeader><CardTitle>{order.no_invoice}</CardTitle><p className="text-sm text-muted-foreground">{new Date(order.tanggal_transaksi).toLocaleString("id-ID")}</p></CardHeader><CardContent className="grid gap-5"><div className="grid gap-2 sm:grid-cols-3"><div><p className="text-xs text-muted-foreground">Order</p><p>{order.order_status}</p></div><div><p className="text-xs text-muted-foreground">Pembayaran</p><p>{order.payment_status}</p></div><div><p className="text-xs text-muted-foreground">Fulfillment</p><p>{order.fulfillment?.status ?? order.fulfillment_method}</p></div></div><div className="grid gap-3 border-y py-4">{order.items?.map((item) => <div className="flex justify-between gap-4 text-sm" key={item.item_id}><span>{item.nama_barang_snapshot} × {item.qty}</span><span>{currency.format(Number(item.subtotal))}</span></div>)}</div><div className="flex justify-between text-lg font-semibold"><span>Total</span><span>{currency.format(Number(order.total_harga))}</span></div>{order.payment_status !== "paid" && order.payment_method !== "store_payment" && <Button disabled={confirming} onClick={() => void confirmPayment()}>{confirming ? "Mengonfirmasi..." : "Konfirmasi Pembayaran"}</Button>}</CardContent></Card>}</main><MarketplaceFooter /></>
}
