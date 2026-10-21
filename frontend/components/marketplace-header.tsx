import { useState } from "react"
import { Link, useNavigate } from "react-router"
import { LogIn, ShoppingBag, UserRound } from "lucide-react"
import { Button } from "@/components/ui/button"
import { useMarketplaceCart } from "../src/lib/marketplace"
import { useCustomerAuth } from "../src/auth/CustomerAuthContext"
import { CustomerLoginDialog } from "./customer-login-dialog"

export function MarketplaceHeader() {
  const navigate = useNavigate()
  const { count } = useMarketplaceCart()
  const { profile, signOut } = useCustomerAuth()
  const [loginDialog, setLoginDialog] = useState(false)

  return <><header className="sticky top-0 z-40 border-b bg-background/95 backdrop-blur print:hidden"><div className="mx-auto flex h-16 max-w-7xl items-center gap-4 px-4"><Link to="/" className="text-lg font-semibold tracking-tight">Dewa Jam</Link><div className="hidden flex-1 md:block" /><nav className="flex items-center gap-2">{profile ? <><Button variant="ghost" size="sm" onClick={() => navigate("/profile")}><UserRound /> {profile.nama}</Button><Button variant="ghost" size="sm" onClick={() => navigate("/orders")}>Pesanan</Button><Button variant="ghost" size="sm" onClick={() => void signOut().then(() => navigate("/"))}>Logout</Button></> : <><Button variant="ghost" size="sm" onClick={() => navigate("/login")}><LogIn /> Masuk</Button><Button variant="outline" size="sm" onClick={() => navigate("/signup")}><UserRound /> Daftar</Button></>}<Button variant="ghost" size="icon-sm" aria-label="Keranjang" onClick={() => profile ? navigate("/cart") : setLoginDialog(true)}><ShoppingBag /><span className="sr-only">Keranjang</span>{profile && count > 0 && <span className="absolute ml-6 -mt-5 rounded-full bg-primary px-1.5 text-[10px] text-primary-foreground">{count}</span>}</Button></nav></div></header><CustomerLoginDialog open={loginDialog} from="/cart" onClose={() => setLoginDialog(false)} /></>
}

export function MarketplaceFooter() {
  return <footer className="mt-16 border-t bg-muted/30"><div className="mx-auto max-w-7xl px-4 py-8 text-sm text-muted-foreground"><p className="font-semibold text-foreground">Dewa Jam</p><p className="mt-2">Koleksi jam tangan pilihan untuk setiap momen.</p><p className="mt-6">© {new Date().getFullYear()} Dewa Jam</p></div></footer>
}
