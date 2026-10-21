import { useState, type FormEvent } from "react"
import { Link, useNavigate } from "react-router"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { getSupabaseClient } from "../../../lib/supabase"

export default function SignupPage() {
  const navigate = useNavigate()
  const [name, setName] = useState(""); const [phone, setPhone] = useState(""); const [email, setEmail] = useState(""); const [password, setPassword] = useState(""); const [confirm, setConfirm] = useState(""); const [error, setError] = useState<string | null>(null); const [success, setSuccess] = useState(false); const [loading, setLoading] = useState(false)
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(null)
    if (password.length < 8) return setError("Password minimal 8 karakter.")
    if (password !== confirm) return setError("Konfirmasi password tidak cocok.")
    setLoading(true)
    try {
      const { data, error: authError } = await getSupabaseClient().auth.signUp({ email: email.trim(), password })
      if (authError) throw authError
      if (data.session && data.user) {
        const response = await fetch(`${import.meta.env.VITE_API_URL ?? "http://localhost:8000"}/api/customer/register`, { method: "POST", headers: { Authorization: `Bearer ${data.session.access_token}`, "Content-Type": "application/json" }, body: JSON.stringify({ nama: name.trim(), no_hp: phone.trim(), auth_user_id: data.user.id }) })
        if (!response.ok) throw new Error("Profil customer gagal dibuat.")
        navigate("/", { replace: true })
      } else setSuccess(true)
    } catch (err) { setError(err instanceof Error ? err.message : "Pendaftaran gagal.") } finally { setLoading(false) }
  }
  return <div className="grid min-h-[calc(100dvh-4rem)] place-items-center px-4 py-8"><Card className="w-full max-w-md"><CardHeader className="text-center"><CardTitle>Buat Akun Customer</CardTitle><CardDescription>Daftar untuk berbelanja dan melacak pesanan.</CardDescription></CardHeader><CardContent><form className="grid gap-4" onSubmit={submit}><div className="grid gap-2"><Label htmlFor="signup-name">Nama lengkap</Label><Input id="signup-name" value={name} onChange={(event) => setName(event.target.value)} required /></div><div className="grid gap-2"><Label htmlFor="signup-phone">Nomor HP</Label><Input id="signup-phone" type="tel" value={phone} onChange={(event) => setPhone(event.target.value)} required /></div><div className="grid gap-2"><Label htmlFor="signup-email">Email</Label><Input id="signup-email" type="email" value={email} onChange={(event) => setEmail(event.target.value)} required /></div><div className="grid gap-2"><Label htmlFor="signup-password">Password</Label><Input id="signup-password" type="password" value={password} onChange={(event) => setPassword(event.target.value)} required /></div><div className="grid gap-2"><Label htmlFor="signup-confirm">Konfirmasi password</Label><Input id="signup-confirm" type="password" value={confirm} onChange={(event) => setConfirm(event.target.value)} required /></div>{error && <p className="text-sm text-destructive">{error}</p>}{success && <p className="text-sm text-green-600">Akun dibuat. Periksa email untuk konfirmasi, lalu login.</p>}<Button type="submit" disabled={loading}>{loading ? "Mendaftar..." : "Daftar"}</Button></form></CardContent><CardFooter className="justify-center text-sm text-muted-foreground">Sudah punya akun? <Link className="ml-1 text-primary hover:underline" to="/login">Masuk</Link></CardFooter></Card></div>
}
