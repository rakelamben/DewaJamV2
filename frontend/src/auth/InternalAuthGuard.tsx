import { useEffect, useRef, type ReactNode } from "react"
import { Navigate, useLocation } from "react-router"
import { useAuth } from "./AuthContext"

export function InternalAuthGuard({ children }: { children: ReactNode }) {
  const { session, profile, loading, error, errorStatus, clearLocalSession } = useAuth()
  const location = useLocation()
  const hasClearedInvalidSession = useRef(false)

  useEffect(() => {
    const invalidSession = errorStatus === 401 || errorStatus === 403
    if (!loading && session && !profile && invalidSession && !hasClearedInvalidSession.current) {
      hasClearedInvalidSession.current = true
      void clearLocalSession()
    }
  }, [loading, session, profile, errorStatus, clearLocalSession])

  if (loading) {
    return <div className="grid min-h-svh place-items-center">Memeriksa sesi...</div>
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
