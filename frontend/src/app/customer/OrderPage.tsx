import { useEffect, useState } from "react"
import { Link, useNavigate } from "react-router"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { MarketplaceFooter, MarketplaceHeader } from "@/components/marketplace-header"
import { confirmCustomerPayment, getCustomerOrders, type MarketplaceOrder } from "../../../lib/api"
import { getSupabaseClient } from "../../../lib/supabase"

const currency = new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 })

export default function OrderPage() {
  const navigate = useNavigate(); const [orders, setOrders] = useState<MarketplaceOrder[]>([]); const [loading, setLoading] = useState(true); const [confirmingId, setConfirmingId] = useState<string | null>(null)
  useEffect(() => { void getSupabaseClient().auth.getSession().then(async ({ data }) => { if (!data.session) { navigate("/login", { replace: true }); return } try { setOrders(await getCustomerOrders(data.session.access_token)) } finally { setLoading(false) } }) }, [navigate])
  async function confirmPayment(order: MarketplaceOrder) { const { data } = await getSupabaseClient().auth.getSession(); if (!data.session) return; setConfirmingId(order.transaction_id); try { const updated = await confirmCustomerPayment(data.session.access_token, order.transaction_id); setOrders((current) => current.map((item) => item.transaction_id === updated.transaction_id ? { ...item, ...updated } : item)) } finally { setConfirmingId(null) } }
  return <><MarketplaceHeader /><main className="mx-auto max-w-5xl px-4 py-8"><Link to="/" className="text-sm text-muted-foreground hover:underline">← Kembali ke toko</Link><h1 className="mt-6 text-3xl font-semibold">Pesanan Saya</h1><div className="mt-8 grid gap-4">{loading ? [1,2].map((item) => <Card className="h-32 animate-pulse bg-muted" key={item} />) : orders.length === 0 ? <Card><CardContent className="grid gap-4 p-10 text-center"><p className="text-muted-foreground">Belum ada pesanan.</p><Button onClick={() => navigate("/")}>Mulai Belanja</Button></CardContent></Card> : orders.map((order) => <Card key={order.transaction_id}><CardContent className="flex flex-wrap items-center justify-between gap-4 p-5"><div><p className="font-semibold">{order.no_invoice}</p><p className="text-sm text-muted-foreground">{new Date(order.tanggal_transaksi).toLocaleString("id-ID")}</p><p className="mt-2 text-sm">{order.payment_status} · {order.order_status}</p></div><div className="text-right"><p className="font-semibold">{currency.format(Number(order.total_harga))}</p><div className="mt-2 flex justify-end gap-2"><Button variant="outline" size="sm" onClick={() => navigate(`/orders/${order.transaction_id}`)}>Lihat Detail</Button>{order.payment_status !== "paid" && order.payment_method !== "store_payment" && <Button size="sm" disabled={confirmingId === order.transaction_id} onClick={() => void confirmPayment(order)}>{confirmingId === order.transaction_id ? "Mengonfirmasi..." : "Konfirmasi Pembayaran"}</Button>}</div></div></CardContent></Card>)}</div></main><MarketplaceFooter /></>
}
