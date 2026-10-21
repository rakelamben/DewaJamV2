import { useEffect, useState } from "react"
import { Link, useParams } from "react-router"
import { ArrowLeft, ShoppingCart } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { MarketplaceFooter, MarketplaceHeader } from "@/components/marketplace-header"
import { CustomerLoginDialog } from "@/components/customer-login-dialog"
import { getMarketplaceProduct, type PosProduct } from "../../../lib/api"
import { useMarketplaceCart } from "../../lib/marketplace"
import { useCustomerAuth } from "../../auth/CustomerAuthContext"

const currency = new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 })

export default function ProductPage() {
  const { productId = "" } = useParams()
  const [product, setProduct] = useState<PosProduct | null>(null)
  const [loading, setLoading] = useState(true)
  const { add } = useMarketplaceCart(); const { profile } = useCustomerAuth(); const [loginDialog, setLoginDialog] = useState(false)
  useEffect(() => { void getMarketplaceProduct(productId).then(setProduct).finally(() => setLoading(false)) }, [productId])
  return <><MarketplaceHeader /><main className="mx-auto max-w-6xl px-4 py-8"><Link to="/" className="mb-8 inline-flex items-center gap-2 text-sm text-muted-foreground"><ArrowLeft /> Kembali ke katalog</Link>{loading ? <Card className="h-96 animate-pulse bg-muted" /> : !product ? <p>Produk tidak ditemukan.</p> : <div className="grid gap-8 md:grid-cols-2"><div className="flex min-h-96 items-center justify-center rounded-xl bg-muted">{product.gambar_url ? <img src={product.gambar_url} alt={product.nama_barang} className="h-full max-h-[520px] w-full object-cover" /> : <ShoppingCart className="size-20 text-muted-foreground" />}</div><div className="flex flex-col justify-center"><p className="text-sm text-primary">{product.brand || product.kategori}</p><h1 className="mt-2 text-3xl font-semibold">{product.nama_barang}</h1><p className="mt-4 text-2xl font-bold">{currency.format(Number(product.harga))}</p><p className="mt-4 text-sm text-muted-foreground">Stok tersedia: {product.stok}</p><p className="mt-6 leading-7 text-muted-foreground">{product.deskripsi || "Produk pilihan dari Dewa Jam."}</p><Button className="mt-8 w-full sm:w-fit" disabled={product.stok < 1} onClick={() => profile ? add(product) : setLoginDialog(true)}>{product.stok < 1 ? "Stok Habis" : "Tambah ke Cart"}</Button></div></div>}</main><MarketplaceFooter /><CustomerLoginDialog open={loginDialog} from={`/product/${productId}`} onClose={() => setLoginDialog(false)} /></>
}
