import logging
from typing import Any

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from config import SUPABASE_PUBLISHABLE_KEY, SUPABASE_SECRET_KEY, SUPABASE_URL

bearer_scheme = HTTPBearer(auto_error=False)
logger = logging.getLogger(__name__)


class InternalUser(BaseModel):
    auth_user_id: str
    email: str | None = None
    entity_type: str
    entity_id: str
    role: str
    name: str


async def _get_json(
    client: httpx.AsyncClient,
    path: str,
    *,
    headers: dict[str, str],
    params: dict[str, str] | None = None,
) -> Any:
    response = await client.get(f"{SUPABASE_URL}{path}", headers=headers, params=params)
    if response.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Layanan Supabase tidak dapat diakses.",
        )
    return response.json()


async def get_current_internal_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> InternalUser:
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token diperlukan.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not SUPABASE_URL or not SUPABASE_PUBLISHABLE_KEY or not SUPABASE_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Konfigurasi Supabase backend belum lengkap.",
        )

    token = credentials.credentials
    auth_headers = {
        "apikey": SUPABASE_PUBLISHABLE_KEY,
        "Authorization": f"Bearer {token}",
    }
    db_headers = {
        "apikey": SUPABASE_SECRET_KEY,
        "Authorization": f"Bearer {SUPABASE_SECRET_KEY}",
        "Accept-Profile": "toko_jam",
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            auth_response = await client.get(
                f"{SUPABASE_URL}/auth/v1/user", headers=auth_headers
            )
            if auth_response.status_code in (401, 403):
                logger.info(
                    "Supabase menolak session dengan status %s: %s",
                    auth_response.status_code,
                    auth_response.text,
                )
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token Supabase tidak valid atau sudah kedaluwarsa.",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            if auth_response.status_code >= 400:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Layanan Supabase Auth tidak dapat diakses.",
                )

            auth_user = auth_response.json()
            auth_user_id = auth_user.get("id")
            if not auth_user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token Supabase tidak valid.",
                )

            profiles = await _get_json(
                client,
                "/rest/v1/user_profiles",
                headers=db_headers,
                params={
                    "auth_user_id": f"eq.{auth_user_id}",
                    "select": "auth_user_id,entity_type,entity_id",
                },
            )
            if not profiles:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Akun tidak memiliki profil internal.",
                )

            profile = profiles[0]
            profile_type = str(profile.get("entity_type", "")).strip().lower()
            profile_entity_id = profile.get("entity_id")

            if profile_type != "personnel" or not profile_entity_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Akun bukan personnel internal.",
                )

            personnel_rows = await _get_json(
                client,
                "/rest/v1/personnel",
                headers=db_headers,
                params={
                    "personnel_id": f"eq.{profile_entity_id}",
                    "select": "personnel_id,personnel_type",
                },
            )
            if not personnel_rows:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Data personnel tidak ditemukan.",
                )

            personnel = personnel_rows[0]
            personnel_type = str(personnel.get("personnel_type", "")).strip().lower()
            detail_config = {
                "admin": ("admins", "admin", "nama"),
                "manager": ("managers", "manager", "nama"),
                "staff": ("staff", None, "nama,role"),
            }.get(personnel_type)
            if not detail_config:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Tipe personnel tidak memiliki akses internal.",
                )

            table, fixed_role, select = detail_config
            entity_rows = await _get_json(
                client,
                f"/rest/v1/{table}",
                headers=db_headers,
                params={
                    "personnel_id": f"eq.{profile_entity_id}",
                    "select": select,
                },
            )
            if not entity_rows:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Detail akun personnel tidak ditemukan.",
                )

            entity = entity_rows[0]
            role = fixed_role or str(entity.get("role", "")).strip().lower()
            allowed_roles = {
                "admin",
                "manager",
                "staf_gudang",
                "staf_operasional",
            }
            if role not in allowed_roles:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Role akun tidak diizinkan untuk sistem internal.",
                )

            return InternalUser(
                auth_user_id=auth_user_id,
                email=auth_user.get("email"),
                entity_type="personnel",
                entity_id=profile_entity_id,
                role=role,
                name=entity.get("nama", ""),
            )
    except HTTPException:
        raise
    except httpx.HTTPError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Tidak dapat menghubungi Supabase.",
        ) from error
