import { useState, type FormEvent } from "react"
import { Link, useLocation, useNavigate } from "react-router"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { getSupabaseClient } from "../../../lib/supabase"

export default function LoginPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(null); setLoading(true)
    try {
      const { error: authError } = await getSupabaseClient().auth.signInWithPassword({ email: email.trim(), password })
      if (authError) throw authError
      const { data: sessionData } = await getSupabaseClient().auth.getSession()
      if (!sessionData.session) throw new Error("Sesi login tidak ditemukan.")
      const profileResponse = await fetch(`${import.meta.env.VITE_API_URL ?? "http://localhost:8000"}/api/customer/me`, { headers: { Authorization: `Bearer ${sessionData.session.access_token}` } })
      if (!profileResponse.ok) {
        await getSupabaseClient().auth.signOut({ scope: "local" })
        throw new Error("Akun ini belum terdaftar sebagai customer.")
      }
      const from = (location.state as { from?: string } | null)?.from ?? "/"
      navigate(from, { replace: true })
    } catch (err) { setError(err instanceof Error ? err.message : "Login gagal.") } finally { setLoading(false) }
  }
  return <div className="grid min-h-[calc(100dvh-4rem)] place-items-center px-4 py-8"><Card className="w-full max-w-md"><CardHeader className="text-center"><CardTitle>Masuk sebagai Customer</CardTitle><CardDescription>Masuk untuk melanjutkan belanja dan melihat pesanan.</CardDescription></CardHeader><CardContent><form className="grid gap-4" onSubmit={submit}><div className="grid gap-2"><Label htmlFor="customer-email">Email</Label><Input id="customer-email" type="email" value={email} onChange={(event) => setEmail(event.target.value)} required autoComplete="email" /></div><div className="grid gap-2"><Label htmlFor="customer-password">Password</Label><Input id="customer-password" type="password" value={password} onChange={(event) => setPassword(event.target.value)} required autoComplete="current-password" /></div>{error && <p className="text-sm text-destructive">{error}</p>}<Button type="submit" disabled={loading}>{loading ? "Memproses..." : "Masuk"}</Button></form></CardContent><CardFooter className="justify-center text-sm text-muted-foreground">Belum punya akun? <Link className="ml-1 text-primary hover:underline" to="/signup">Daftar</Link></CardFooter></Card></div>
}
