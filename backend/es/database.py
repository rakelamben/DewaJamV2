from typing import Any

import httpx

from config import SUPABASE_DB_SCHEMA, SUPABASE_SECRET_KEY, SUPABASE_URL


def headers(prefer: str | None = None) -> dict[str, str]:
    value = {
        "apikey": SUPABASE_SECRET_KEY,
        "Authorization": f"Bearer {SUPABASE_SECRET_KEY}",
        "Accept-Profile": SUPABASE_DB_SCHEMA,
        "Content-Profile": SUPABASE_DB_SCHEMA,
        "Content-Type": "application/json",
    }
    if prefer:
        value["Prefer"] = prefer
    return value


async def request(
    client: httpx.AsyncClient,
    method: str,
    table: str,
    *,
    params: dict[str, str] | None = None,
    body: Any = None,
    prefer: str | None = None,
) -> list[dict[str, Any]]:
    response = await client.request(
        method,
        f"{SUPABASE_URL}/rest/v1/{table}",
        headers=headers(prefer),
        params=params,
        json=body,
    )
    if response.status_code >= 400:
        raise RuntimeError(f"Supabase {method} {table} gagal ({response.status_code}): {response.text}")
    if not response.content:
        return []
    return response.json()
