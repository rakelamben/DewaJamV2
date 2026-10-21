import { Link, useParams } from "react-router"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { MarketplaceFooter, MarketplaceHeader } from "@/components/marketplace-header"

export default function PaymentPage() {
  const { state = "pending", transactionId = "" } = useParams()
  const success = state === "success"
  return <><MarketplaceHeader /><main className="mx-auto max-w-xl px-4 py-16"><Card><CardHeader><CardTitle>{success ? "Pembayaran berhasil" : state === "failed" ? "Pembayaran gagal" : "Menunggu pembayaran"}</CardTitle></CardHeader><CardContent className="grid gap-4"><p className="text-muted-foreground">{success ? "Pesanan Anda sedang diproses." : state === "failed" ? "Silakan lihat detail pesanan atau hubungi toko." : "Untuk simulasi, konfirmasi pembayaran tersedia pada detail pesanan untuk Virtual Account dan E-wallet."}</p>{transactionId && <Link className="inline-flex h-9 items-center justify-center rounded-lg bg-primary px-4 text-sm text-primary-foreground" to={`/orders/${transactionId}`}>{success ? "Lihat Pesanan" : "Buka Detail Pesanan"}</Link>}<Link className="inline-flex h-9 items-center justify-center rounded-lg border px-4 text-sm" to="/orders">Riwayat Pesanan</Link></CardContent></Card></main><MarketplaceFooter /></>
}
