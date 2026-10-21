import { useEffect, useRef, type ReactNode } from "react"
import { Navigate, useLocation } from "react-router"
import { useAuth } from "./AuthContext"

export function InternalAuthGuard({ children }: { children: ReactNode }) {
  const { session, profile, loading, error, errorStatus, clearLocalSession } = useAuth()
  const location = useLocation()
  const hasClearedInvalidSession = useRef(false)

  useEffect(() => {
    const invalidSession = errorStatus === 401
    if (!loading && session && !profile && invalidSession && !hasClearedInvalidSession.current) {
      hasClearedInvalidSession.current = true
      void clearLocalSession()
    }
  }, [loading, session, profile, errorStatus, clearLocalSession])

  // Keep the internal layout mounted while the profile is checked in the
  // background. Only wait when there is no session at all yet.
  // Keep the verified internal layout mounted while auth is checked in the
  // background. No loading feedback is shown to avoid unmounting the sidebar.
  if (session && profile) {
    return children
  }

  // Initial auth validation also runs silently. The route is not rendered
  // until the internal profile has been verified.
  if (loading) {
    return null
  }

  // A valid customer session is not an invalid Supabase session. Keep it
  // alive and leave the internal area without logging the customer out.
  if (!loading && session && !profile && errorStatus === 403) {
    return <Navigate to="/" replace />
  }

  if (session && !profile && error && errorStatus !== 401 && errorStatus !== 403) {
    return (
      <div className="grid min-h-svh place-items-center p-6 text-center">
        <div>
          <p className="font-medium">Sistem auth tidak dapat dihubungi.</p>
          <p className="mt-2 text-sm text-muted-foreground">{error}</p>
        </div>
      </div>
    )
  }

  if (!session || !profile) {
    return <Navigate to="/internal/login" replace state={{ from: location }} />
  }

  return children
}
