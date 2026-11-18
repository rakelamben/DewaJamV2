import { useEffect, useMemo, useState } from "react"
import { Link } from "react-router"
import { Search, ShoppingCart } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { MarketplaceFooter, MarketplaceHeader } from "@/components/marketplace-header"
import { CustomerLoginDialog } from "@/components/customer-login-dialog"
import { getMarketplaceProducts, type PosProduct } from "../../../lib/api"
import { useMarketplaceCart } from "../../lib/marketplace"
import { useCustomerAuth } from "../../auth/CustomerAuthContext"

const currency = new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 })

export default function ShopPage() {
  const [products, setProducts] = useState<PosProduct[]>([])
  const [search, setSearch] = useState("")
  const [category, setCategory] = useState("")
  const [brand, setBrand] = useState("")
  const [stockOnly, setStockOnly] = useState(false)
  const [sort, setSort] = useState("newest")
  const [loginDialog, setLoginDialog] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const { add } = useMarketplaceCart()
  const { profile } = useCustomerAuth()
  useEffect(() => { void getMarketplaceProducts().then(setProducts).catch((err) => setError(err instanceof Error ? err.message : "Katalog gagal dimuat.")).finally(() => setLoading(false)) }, [])
  const categories = useMemo(() => [...new Set(products.map((product) => product.kategori).filter(Boolean))] as string[], [products])
  const brands = useMemo(() => [...new Set(products.map((product) => product.brand).filter(Boolean))] as string[], [products])
  const visible = useMemo(() => products.filter((product) => {
    const textMatch = [product.nama_barang, product.brand, product.kategori, ...(product.tags ?? [])].some((value) => value?.toLowerCase().includes(search.toLowerCase()))
    return textMatch && (!category || product.kategori === category) && (!brand || product.brand === brand) && (!stockOnly || product.stok > 0)
  }).sort((a, b) => sort === "price-asc" ? Number(a.harga) - Number(b.harga) : sort === "price-desc" ? Number(b.harga) - Number(a.harga) : sort === "newest" ? String(b.updated_at ?? "").localeCompare(String(a.updated_at ?? "")) : 0), [products, search, category, brand, stockOnly, sort])
  return <><MarketplaceHeader /><main><section className="mx-auto max-w-7xl px-4 pb-10 pt-16"><div className="max-w-2xl"><p className="text-sm font-medium text-primary">Koleksi pilihan Dewa Jam</p><h1 className="mt-3 text-4xl font-semibold tracking-tight md:text-6xl">Temukan waktu terbaikmu.</h1><p className="mt-4 text-lg text-muted-foreground">Jam tangan pilihan untuk menemani setiap momen.</p><div className="mt-6 flex flex-wrap gap-3"><Link to="/advisor"><Button type="button" variant="outline">Konsultasi Spesifikasi Horologi (Sistem Pakar)</Button></Link></div></div></section><section className="mx-auto max-w-7xl px-4"><div className="mb-6 flex flex-wrap items-center justify-between gap-4"><div><h2 className="text-2xl font-semibold">Katalog Produk</h2><p className="text-sm text-muted-foreground">{visible.length} produk</p></div><div className="relative w-full max-w-sm"><Search className="absolute left-3 top-2.5 size-4 text-muted-foreground" /><Input className="pl-9" placeholder="Cari produk..." value={search} onChange={(event) => setSearch(event.target.value)} /></div></div><div className="mb-6 flex flex-wrap gap-2"><select className="h-9 rounded-lg border bg-background px-3 text-sm" value={category} onChange={(event) => setCategory(event.target.value)}><option value="">Semua kategori</option>{categories.map((item) => <option key={item} value={item}>{item}</option>)}</select><select className="h-9 rounded-lg border bg-background px-3 text-sm" value={brand} onChange={(event) => setBrand(event.target.value)}><option value="">Semua brand</option>{brands.map((item) => <option key={item} value={item}>{item}</option>)}</select><select className="h-9 rounded-lg border bg-background px-3 text-sm" value={sort} onChange={(event) => setSort(event.target.value)}><option value="newest">Terbaru</option><option value="price-asc">Harga terendah</option><option value="price-desc">Harga tertinggi</option></select><label className="flex items-center gap-2 px-2 text-sm"><input type="checkbox" checked={stockOnly} onChange={(event) => setStockOnly(event.target.checked)} /> Tersedia saja</label></div>{loading ? <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">{[1,2,3,4].map((item) => <Card className="h-80 animate-pulse bg-muted" key={item} />)}</div> : error ? <Card><CardContent className="p-8 text-center">{error}</CardContent></Card> : visible.length === 0 ? <Card><CardContent className="p-8 text-center text-muted-foreground">Produk tidak ditemukan.</CardContent></Card> : <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">{visible.map((product) => <Card key={product.product_id} className="overflow-hidden"><Link to={`/product/${product.product_id}`}><div className="flex h-56 items-center justify-center bg-muted">{product.gambar_url ? <img src={product.gambar_url} alt={product.nama_barang} className="h-full w-full object-cover" /> : <ShoppingCart className="size-12 text-muted-foreground" />}</div></Link><CardContent className="grid gap-2 p-4"><div><p className="font-medium">{product.nama_barang}</p><p className="text-xs text-muted-foreground">{product.brand || product.kategori || "Dewa Jam"}</p></div><p className="font-semibold">{currency.format(Number(product.harga))}</p><Button size="sm" disabled={product.stok < 1} onClick={() => profile ? add(product) : setLoginDialog(true)}>{product.stok < 1 ? "Stok Habis" : "Tambah ke Cart"}</Button></CardContent></Card>)}</div>}</section></main><MarketplaceFooter /><CustomerLoginDialog open={loginDialog} from="/" onClose={() => setLoginDialog(false)} /></>
}
