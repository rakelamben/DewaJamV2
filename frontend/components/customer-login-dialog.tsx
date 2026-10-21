import { useNavigate } from "react-router"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"

type CustomerLoginDialogProps = {
  open: boolean
  from: string
  onClose: () => void
}

export function CustomerLoginDialog({ open, from, onClose }: CustomerLoginDialogProps) {
  const navigate = useNavigate()
  if (!open) return null
  return <div className="fixed inset-0 z-50 grid place-items-center bg-black/50 p-4" role="dialog" aria-modal="true" aria-labelledby="customer-login-title"><Card className="w-full max-w-md"><CardHeader><CardTitle id="customer-login-title">Login diperlukan</CardTitle></CardHeader><CardContent><p className="text-sm text-muted-foreground">Silakan login terlebih dahulu untuk menggunakan cart.</p></CardContent><CardFooter className="justify-end gap-2"><Button variant="ghost" onClick={onClose}>Batal</Button><Button variant="outline" onClick={() => navigate("/signup", { state: { from } })}>Daftar</Button><Button onClick={() => navigate("/login", { state: { from } })}>Login</Button></CardFooter></Card></div>
}
