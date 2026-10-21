/* eslint-disable react-refresh/only-export-components */
import {
  createContext,
  useContext,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react"
import type { Session } from "@supabase/supabase-js"
import { useLocation } from "react-router"
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
  const location = useLocation()
  const isInternalRoute = location.pathname === "/internal" || location.pathname.startsWith("/internal/")
  const [session, setSession] = useState<Session | null>(null)
  const [profile, setProfile] = useState<InternalUser | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [errorStatus, setErrorStatus] = useState<number | null>(null)
  const sessionRef = useRef<Session | null>(null)
  const profileRef = useRef<InternalUser | null>(null)

  useEffect(() => {
    let mounted = true
    let latestRequest = 0

    const syncSession = async (nextSession: Session | null, blocking = true) => {
      if (!mounted) return
      const requestId = ++latestRequest
      sessionRef.current = nextSession
      setSession(nextSession)
      setError(null)
      setErrorStatus(null)

       const canKeepVerifiedProfile = Boolean(
         nextSession &&
         profileRef.current &&
         profileRef.current.auth_user_id === nextSession.user.id
       )

       if (blocking && !canKeepVerifiedProfile) {
         profileRef.current = null
         setProfile(null)
       }
       if (blocking) setLoading(true)

      if (!nextSession) {
        profileRef.current = null
        setProfile(null)
        setLoading(false)
        return
      }

      if (!isInternalRoute) {
        profileRef.current = null
        setProfile(null)
        setLoading(false)
        return
      }

      try {
        const nextProfile = await getCurrentInternalUser(nextSession.access_token)
        if (mounted && requestId === latestRequest) {
          profileRef.current = nextProfile
          setProfile(nextProfile)
          setLoading(false)
        }
      } catch (profileError) {
        if (mounted && requestId === latestRequest) {
          setError(
            profileError instanceof Error
              ? profileError.message
              : "Profil internal tidak dapat dimuat."
          )
          setErrorStatus(profileError instanceof ApiError ? profileError.status : null)
          if (!canKeepVerifiedProfile || profileError instanceof ApiError && (profileError.status === 401 || profileError.status === 403)) {
            profileRef.current = null
            setProfile(null)
          }
          setLoading(false)
        }
      } finally {
        if (mounted && requestId === latestRequest && blocking) setLoading(false)
      }
    }

    let unsubscribe = () => {}
    try {
      const supabase = getSupabaseClient()
      let initialized = false
      const initialize = (nextSession: Session | null) => {
        if (initialized) return
        initialized = true
        void syncSession(nextSession)
      }

      void supabase.auth.getSession().then(({ data }) => initialize(data.session))
      const { data: authListener } = supabase.auth.onAuthStateChange(
        (event, nextSession) => {
          if (event === "INITIAL_SESSION") {
            initialize(nextSession)
            return
          }

          // Token refresh can happen when a tab becomes active again. Keep the
          // current profile and UI while only replacing the access token.
          if (event === "TOKEN_REFRESHED" && nextSession) {
            sessionRef.current = nextSession
            setSession(nextSession)
            if (!profileRef.current) void syncSession(nextSession, false)
            return
          }

          if (event === "USER_UPDATED") {
            void syncSession(nextSession, false)
            return
          }

          void syncSession(nextSession, event === "SIGNED_IN" || event === "SIGNED_OUT")
        }
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
  }, [isInternalRoute])

  const signOut = useCallback(async () => {
    const { error: signOutError } = await getSupabaseClient().auth.signOut({
      scope: "local",
    })
    if (signOutError) throw signOutError

    setSession(null)
    setProfile(null)
    setError(null)
    setErrorStatus(null)
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
