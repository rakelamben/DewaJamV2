/* eslint-disable react-refresh/only-export-components */
import {
  createContext,
  useContext,
  useCallback,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react"
import type { Session } from "@supabase/supabase-js"
import { getSupabaseClient } from "../../lib/supabase"
import { ApiError, getCurrentInternalUser, type InternalUser } from "../../lib/api"

type AuthContextValue = {
  session: Session | null
  profile: InternalUser | null
  loading: boolean
  error: string | null
  errorStatus: number | null
  signOut: () => Promise<void>
  clearLocalSession: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(null)
  const [profile, setProfile] = useState<InternalUser | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [errorStatus, setErrorStatus] = useState<number | null>(null)

  useEffect(() => {
    let mounted = true
    let latestRequest = 0

    const syncSession = async (nextSession: Session | null) => {
      if (!mounted) return
      const requestId = ++latestRequest
      setSession(nextSession)
      setProfile(null)
      setError(null)
      setErrorStatus(null)
      setLoading(true)

      if (!nextSession) {
        setLoading(false)
        return
      }

      try {
        const nextProfile = await getCurrentInternalUser(nextSession.access_token)
        if (mounted && requestId === latestRequest) setProfile(nextProfile)
      } catch (profileError) {
        if (mounted && requestId === latestRequest) {
          setError(
            profileError instanceof Error
              ? profileError.message
              : "Profil internal tidak dapat dimuat."
          )
          setErrorStatus(profileError instanceof ApiError ? profileError.status : null)
        }
      } finally {
        if (mounted && requestId === latestRequest) setLoading(false)
      }
    }

    let unsubscribe = () => {}
    try {
      const supabase = getSupabaseClient()
      void supabase.auth.getSession().then(({ data }) => syncSession(data.session))
      const { data: authListener } = supabase.auth.onAuthStateChange(
        (_event, nextSession) => void syncSession(nextSession)
      )
      unsubscribe = () => authListener.subscription.unsubscribe()
    } catch (authError) {
      queueMicrotask(() => {
        if (!mounted) return
        setError(authError instanceof Error ? authError.message : "Auth belum siap.")
        setErrorStatus(null)
        setLoading(false)
      })
    }

    return () => {
      mounted = false
      unsubscribe()
    }
  }, [])

  const signOut = useCallback(async () => {
    await getSupabaseClient().auth.signOut({ scope: "local" })
  }, [])

  const clearLocalSession = useCallback(async () => {
    await getSupabaseClient().auth.signOut({ scope: "local" })
  }, [])

  const value = useMemo<AuthContextValue>(
    () => ({
      session,
      profile,
      loading,
      error,
      errorStatus,
      signOut,
      clearLocalSession,
    }),
    [session, profile, loading, error, errorStatus, signOut, clearLocalSession]
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) throw new Error("useAuth harus digunakan di dalam AuthProvider.")
  return context
}
