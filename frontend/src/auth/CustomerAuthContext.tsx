/* eslint-disable react-refresh/only-export-components */
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react"
import type { Session } from "@supabase/supabase-js"
import { useLocation } from "react-router"
import { getSupabaseClient } from "../../lib/supabase"

export type CustomerProfile = { auth_user_id: string; email: string | null; entity_type: "customer"; customer_id: string; nama: string; no_hp: string }
type CustomerAuthValue = { profile: CustomerProfile | null; session: Session | null; loading: boolean; signOut: () => Promise<void>; refresh: () => Promise<void> }
const CustomerAuthContext = createContext<CustomerAuthValue | null>(null)

async function fetchProfile(token: string) {
  const response = await fetch(`${import.meta.env.VITE_API_URL ?? "http://localhost:8000"}/api/customer/me`, { headers: { Authorization: `Bearer ${token}` } })
  if (!response.ok) throw new Error("Akun customer belum terdaftar.")
  return (await response.json()) as CustomerProfile
}

export function CustomerAuthProvider({ children }: { children: ReactNode }) {
  const location = useLocation()
  const isCustomerRoute = !location.pathname.startsWith("/internal")
  const [session, setSession] = useState<CustomerAuthValue["session"]>(null)
  const [profile, setProfile] = useState<CustomerProfile | null>(null)
  const [loading, setLoading] = useState(true)
  const refresh = useCallback(async () => {
    const { data } = await getSupabaseClient().auth.getSession()
    setSession(data.session)
    if (!isCustomerRoute) {
      setProfile(null)
      setLoading(false)
      return
    }
    if (data.session) {
      try {
        setProfile(await fetchProfile(data.session.access_token))
      } catch {
        setProfile(null)
      }
    } else {
      setProfile(null)
    }
    setLoading(false)
  }, [isCustomerRoute])

  useEffect(() => {
    queueMicrotask(() => void refresh())
    const { data } = getSupabaseClient().auth.onAuthStateChange((_event, nextSession) => {
      setSession(nextSession)
      if (!isCustomerRoute || !nextSession) {
        setProfile(null)
        setLoading(false)
      } else {
        setLoading(true)
        void fetchProfile(nextSession.access_token)
          .then(setProfile)
          .catch(() => setProfile(null))
          .finally(() => setLoading(false))
      }
    })
    return () => data.subscription.unsubscribe()
  }, [isCustomerRoute, refresh])
  const signOut = useCallback(async () => { await getSupabaseClient().auth.signOut({ scope: "local" }); setSession(null); setProfile(null) }, [])
  const value = useMemo(() => ({ profile, session, loading, signOut, refresh }), [profile, session, loading, signOut, refresh])
  return <CustomerAuthContext.Provider value={value}>{children}</CustomerAuthContext.Provider>
}

export function useCustomerAuth() { const context = useContext(CustomerAuthContext); if (!context) throw new Error("useCustomerAuth harus digunakan di dalam CustomerAuthProvider."); return context }
