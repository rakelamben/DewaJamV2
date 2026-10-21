from uuid import uuid4

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from config import SUPABASE_DB_SCHEMA, SUPABASE_PUBLISHABLE_KEY, SUPABASE_SECRET_KEY, SUPABASE_URL

customer_bearer = HTTPBearer(auto_error=False)


class CustomerRegisterInput(BaseModel):
    auth_user_id: str
    nama: str = Field(min_length=1, max_length=255)
    no_hp: str = Field(min_length=1, max_length=50)


class CustomerProfileUpdate(BaseModel):
    nama: str = Field(min_length=1, max_length=255)
    no_hp: str = Field(min_length=1, max_length=50)


async def get_customer_profile(
    credentials: HTTPAuthorizationCredentials | None = Depends(customer_bearer),
) -> dict[str, str | None]:
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bearer token diperlukan.")

    async with httpx.AsyncClient(timeout=10) as client:
        auth_response = await client.get(
            f"{SUPABASE_URL}/auth/v1/user",
            headers={"apikey": SUPABASE_PUBLISHABLE_KEY, "Authorization": f"Bearer {credentials.credentials}"},
        )
        if auth_response.status_code >= 400:
            raise HTTPException(status_code=401, detail="Session customer tidak valid.")
        auth_user = auth_response.json()
        profiles = await client.get(
            f"{SUPABASE_URL}/rest/v1/user_profiles",
            headers=_db_headers(),
            params={"auth_user_id": f"eq.{auth_user.get('id')}", "entity_type": "eq.customer", "select": "entity_id"},
        )
        if profiles.status_code >= 400 or not profiles.json():
            raise HTTPException(status_code=403, detail="Akun bukan customer terdaftar.")
        customer_id = profiles.json()[0]["entity_id"]
        customers = await client.get(
            f"{SUPABASE_URL}/rest/v1/customers",
            headers=_db_headers(),
            params={"customer_id": f"eq.{customer_id}", "select": "customer_id,nama,no_hp"},
        )
        if customers.status_code >= 400 or not customers.json():
            raise HTTPException(status_code=403, detail="Profil customer tidak ditemukan.")
        customer = customers.json()[0]
        return {
            "auth_user_id": auth_user.get("id"),
            "email": auth_user.get("email"),
            "entity_type": "customer",
            "customer_id": customer["customer_id"],
            "nama": customer["nama"],
            "no_hp": customer["no_hp"],
        }


def _db_headers(prefer: str | None = None) -> dict[str, str]:
    headers = {
        "apikey": SUPABASE_SECRET_KEY,
        "Authorization": f"Bearer {SUPABASE_SECRET_KEY}",
        "Accept-Profile": SUPABASE_DB_SCHEMA,
        "Content-Profile": SUPABASE_DB_SCHEMA,
        "Content-Type": "application/json",
    }
    if prefer:
        headers["Prefer"] = prefer
    return headers


async def register_customer(
    payload: CustomerRegisterInput,
    credentials: HTTPAuthorizationCredentials | None = Depends(customer_bearer),
) -> dict[str, str]:
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bearer token diperlukan.")

    async with httpx.AsyncClient(timeout=10) as client:
        auth_response = await client.get(
            f"{SUPABASE_URL}/auth/v1/user",
            headers={"apikey": SUPABASE_PUBLISHABLE_KEY, "Authorization": f"Bearer {credentials.credentials}"},
        )
        if auth_response.status_code >= 400:
            raise HTTPException(status_code=401, detail="Session customer tidak valid.")
        auth_user_id = auth_response.json().get("id")
        if auth_user_id != payload.auth_user_id:
            raise HTTPException(status_code=403, detail="Auth user tidak sesuai.")

        existing = await client.get(
            f"{SUPABASE_URL}/rest/v1/customers",
            headers=_db_headers(),
            params={"no_hp": f"eq.{payload.no_hp.strip()}", "select": "customer_id"},
        )
        if existing.status_code >= 400:
            raise HTTPException(status_code=502, detail="Data customer tidak dapat diakses.")
        if existing.json():
            raise HTTPException(status_code=409, detail="Nomor HP sudah terdaftar.")

        customer_id = str(uuid4())
        customer = {"customer_id": customer_id, "nama": payload.nama.strip(), "no_hp": payload.no_hp.strip()}
        response = await client.post(
            f"{SUPABASE_URL}/rest/v1/customers",
            headers=_db_headers("return=minimal"),
            json=customer,
        )
        if response.status_code >= 400:
            raise HTTPException(status_code=502, detail="Profil customer gagal dibuat.")

        profile = {"auth_user_id": auth_user_id, "entity_type": "customer", "entity_id": customer_id}
        response = await client.post(
            f"{SUPABASE_URL}/rest/v1/user_profiles",
            headers=_db_headers("return=minimal"),
            json=profile,
        )
        if response.status_code >= 400:
            raise HTTPException(status_code=502, detail="Mapping akun customer gagal dibuat.")

        return {"customer_id": customer_id, "auth_user_id": auth_user_id}


async def update_customer_profile(
    payload: CustomerProfileUpdate,
    credentials: HTTPAuthorizationCredentials | None = Depends(customer_bearer),
):
    profile = await get_customer_profile(credentials)
    async with httpx.AsyncClient(timeout=10) as client:
        duplicate = await client.get(
            f"{SUPABASE_URL}/rest/v1/customers",
            headers=_db_headers(),
            params={"no_hp": f"eq.{payload.no_hp.strip()}", "customer_id": f"neq.{profile['customer_id']}", "select": "customer_id"},
        )
        if duplicate.status_code >= 400:
            raise HTTPException(status_code=502, detail="Data customer tidak dapat diakses.")
        if duplicate.json():
            raise HTTPException(status_code=409, detail="Nomor HP sudah terdaftar.")
        response = await client.patch(
            f"{SUPABASE_URL}/rest/v1/customers",
            headers=_db_headers("return=representation"),
            params={"customer_id": f"eq.{profile['customer_id']}"},
            json={"nama": payload.nama.strip(), "no_hp": payload.no_hp.strip()},
        )
        if response.status_code >= 400 or not response.json():
            raise HTTPException(status_code=502, detail="Profil customer gagal diperbarui.")
    return await get_customer_profile(credentials)
