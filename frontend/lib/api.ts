export type InternalRole =
  | "admin"
  | "manager"
  | "staf_gudang"
  | "staf_operasional"

export type InternalUser = {
  auth_user_id: string
  email: string | null
  entity_type: "admin" | "manager" | "staff"
  entity_id: string
  role: InternalRole
  name: string
}

const apiUrl = import.meta.env.VITE_API_URL ?? "http://localhost:8000"

export class ApiError extends Error {
  readonly status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = "ApiError"
    this.status = status
  }
}

export async function getCurrentInternalUser(accessToken: string) {
  const response = await fetch(`${apiUrl}/api/auth/me`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  })
  if (!response.ok) {
    let detail = "Profil internal tidak dapat dimuat."
    try {
      const body = (await response.json()) as { detail?: string }
      if (body.detail) detail = body.detail
    } catch {
      // Gunakan pesan default jika backend tidak mengembalikan JSON.
    }
    throw new ApiError(detail, response.status)
  }

  return (await response.json()) as InternalUser
}
