import { useCallback, useEffect, useMemo, useState } from "react"
import { ArrowLeft, Ban, FileText, RefreshCw } from "lucide-react"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { useAuth } from "../../auth/AuthContext"
import { cancelPosTransaction, getPosTransaction, getTodayPosTransactions, type PosTransaction } from "../../../lib/api"

const currency = new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 })
const formatCurrency = (value: number | string) => currency.format(Number(value))

export default function SalesDailyPage() {
  const { session } = useAuth()
  const [transactions, setTransactions] = useState<PosTransaction[]>([])
  const [selected, setSelected] = useState<PosTransaction | null>(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)

  const loadTransactions = useCallback(async () => {
    if (!session?.access_token) return
    setRefreshing(true)
    try {
      setTransactions(await getTodayPosTransactions(session.access_token))
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Sales harian gagal dimuat.")
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [session])

  useEffect(() => {
    queueMicrotask(() => void loadTransactions())
  }, [loadTransactions])

  const completed = transactions.filter((transaction) => transaction.payment_status === "paid")
  const canceled = transactions.filter((transaction) => transaction.status === "canceled")
  const totalSales = useMemo(() => completed.reduce((sum, transaction) => sum + Number(transaction.total_harga), 0), [completed])
  const totalItems = useMemo(() => completed.reduce((sum, transaction) => sum + (transaction.items?.reduce((itemSum, item) => itemSum + item.qty, 0) ?? 0), 0), [completed])

  async function openDetail(transactionId: string) {
    if (!session?.access_token) return
    try {
      setSelected(await getPosTransaction(session.access_token, transactionId))
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Detail transaksi gagal dimuat.")
    }
  }

  async function cancelTransaction(transactionId: string) {
    if (!session?.access_token || !window.confirm("Batalkan transaksi ini? Stok akan dikembalikan.")) return
    try {
      await cancelPosTransaction(session.access_token, transactionId)
      toast.success("Transaksi dibatalkan dan stok dikembalikan.")
      setSelected(null)
      await loadTransactions()
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Transaksi gagal dibatalkan.")
    }
  }

  if (!session) return null

  if (selected) {
    return <TransactionDetail transaction={selected} onBack={() => setSelected(null)} onCancel={() => void cancelTransaction(selected.transaction_id)} />
  }

  return <div className="grid gap-6 p-4"><div className="flex flex-wrap items-center justify-between gap-3"><div><h1 className="text-2xl font-semibold">Sales Harian</h1><p className="text-sm text-muted-foreground">Ringkasan transaksi POS hari ini</p></div><Button variant="outline" onClick={() => void loadTransactions()} disabled={refreshing}><RefreshCw className={refreshing ? "animate-spin" : ""} /> Refresh</Button></div><div className="grid gap-4 sm:grid-cols-3"><SummaryCard title="Total Penjualan" value={formatCurrency(totalSales)} /><SummaryCard title="Transaksi Berhasil" value={String(completed.length)} /><SummaryCard title="Item Terjual" value={String(totalItems)} /><SummaryCard title="Transaksi Batal" value={String(canceled.length)} /></div><Card><CardHeader><CardTitle>Riwayat Transaksi Hari Ini</CardTitle></CardHeader><CardContent>{loading ? <p>Memuat transaksi...</p> : transactions.length === 0 ? <p className="text-sm text-muted-foreground">Belum ada transaksi hari ini.</p> : <div className="overflow-x-auto"><table className="w-full text-left text-sm"><thead><tr className="border-b text-muted-foreground"><th className="p-3">Invoice</th><th className="p-3">Pembeli</th><th className="p-3">Waktu</th><th className="p-3">Metode</th><th className="p-3 text-right">Total</th><th className="p-3">Status</th><th className="p-3">Aksi</th></tr></thead><tbody>{transactions.map((transaction) => <tr className="border-b last:border-0" key={transaction.transaction_id}><td className="p-3 font-medium">{transaction.no_invoice}</td><td className="p-3">{transaction.buyer_name_snapshot}<br /><span className="text-xs text-muted-foreground">{transaction.buyer_phone_snapshot}</span></td><td className="p-3">{new Date(transaction.tanggal_transaksi).toLocaleTimeString("id-ID", { hour: "2-digit", minute: "2-digit" })}</td><td className="p-3 uppercase">{transaction.payment_method}</td><td className="p-3 text-right">{formatCurrency(transaction.total_harga)}</td><td className="p-3"><span className={transaction.status === "canceled" ? "text-destructive" : "text-green-600"}>{transaction.status}</span></td><td className="p-3"><Button variant="outline" size="sm" onClick={() => void openDetail(transaction.transaction_id)}><FileText /> Detail</Button></td></tr>)}</tbody></table></div>}</CardContent></Card></div>
}

function SummaryCard({ title, value }: { title: string; value: string }) { return <Card><CardContent className="p-4"><p className="text-sm text-muted-foreground">{title}</p><p className="mt-2 text-xl font-semibold">{value}</p></CardContent></Card> }

function TransactionDetail({ transaction, onBack, onCancel }: { transaction: PosTransaction; onBack: () => void; onCancel: () => void }) {
  return <div className="mx-auto grid max-w-3xl gap-4 p-4"><Button className="w-fit" variant="ghost" onClick={onBack}><ArrowLeft /> Kembali ke Sales Harian</Button><Card><CardHeader><div className="flex flex-wrap items-center justify-between gap-2"><CardTitle>{transaction.no_invoice}</CardTitle><span className={transaction.status === "canceled" ? "text-destructive" : "text-green-600"}>{transaction.status}</span></div></CardHeader><CardContent className="grid gap-5"><div className="grid gap-1 text-sm sm:grid-cols-2"><p>Pembeli: <strong>{transaction.buyer_name_snapshot}</strong></p><p>No. HP: <strong>{transaction.buyer_phone_snapshot}</strong></p><p>Metode: <strong>{transaction.payment_method}</strong></p><p>Waktu: <strong>{new Date(transaction.tanggal_transaksi).toLocaleString("id-ID")}</strong></p></div><div className="grid gap-2 border-y py-4">{transaction.items?.map((item) => <div className="flex justify-between text-sm" key={item.item_id}><span>{item.nama_barang_snapshot} × {item.qty}</span><span>{formatCurrency(item.subtotal)}</span></div>)}</div><div className="flex justify-between font-semibold"><span>Total penjualan</span><span>{formatCurrency(transaction.total_harga)}</span></div>{transaction.status !== "canceled" && <Button variant="destructive" className="w-fit" onClick={onCancel}><Ban /> Batalkan Transaksi</Button>}</CardContent></Card></div>
}
