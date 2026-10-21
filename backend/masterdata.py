from uuid import uuid4

import httpx
from fastapi import HTTPException
from pydantic import BaseModel, Field, HttpUrl

from pos import _request


class ProductInput(BaseModel):
    nama_barang: str = Field(min_length=1, max_length=255)
    kategori: str = Field(min_length=1, max_length=100)
    harga: float = Field(ge=0)
    stok: int = Field(ge=0)
    deskripsi: str | None = None
    gambar_url: HttpUrl | None = None
    brand: str | None = Field(default=None, max_length=100)
    tags: list[str] = Field(default_factory=list)


class StoreInput(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    address: str = Field(min_length=1)
    google_maps_url: HttpUrl | None = None
    opening_hours: str | None = Field(default=None, max_length=255)
    is_active: bool = True


async def list_master_products():
    async with httpx.AsyncClient(timeout=10) as client:
        return await _request(client, "GET", "products", params={"select": "*", "order": "nama_barang.asc"})


async def create_master_product(payload: ProductInput):
    async with httpx.AsyncClient(timeout=10) as client:
        rows = await _request(client, "POST", "products", body={"product_id": str(uuid4()), **payload.model_dump(mode="json")}, prefer="return=representation")
        return rows[0] if rows else payload.model_dump(mode="json")


async def update_master_product(product_id: str, payload: ProductInput):
    async with httpx.AsyncClient(timeout=10) as client:
        rows = await _request(client, "PATCH", "products", params={"product_id": f"eq.{product_id}"}, body=payload.model_dump(mode="json"), prefer="return=representation")
        if not rows:
            raise HTTPException(status_code=404, detail="Produk tidak ditemukan.")
        return rows[0]


async def delete_master_product(product_id: str):
    async with httpx.AsyncClient(timeout=10) as client:
        rows = await _request(client, "DELETE", "products", params={"product_id": f"eq.{product_id}"}, prefer="return=representation")
        if not rows:
            raise HTTPException(status_code=404, detail="Produk tidak ditemukan.")
        return {"deleted": True}


async def list_master_stores():
    async with httpx.AsyncClient(timeout=10) as client:
        return await _request(client, "GET", "stores", params={"select": "*", "order": "name.asc"})


async def create_master_store(payload: StoreInput):
    async with httpx.AsyncClient(timeout=10) as client:
        rows = await _request(client, "POST", "stores", body={"store_id": str(uuid4()), **payload.model_dump(mode="json")}, prefer="return=representation")
        return rows[0] if rows else payload.model_dump(mode="json")


async def update_master_store(store_id: str, payload: StoreInput):
    async with httpx.AsyncClient(timeout=10) as client:
        rows = await _request(client, "PATCH", "stores", params={"store_id": f"eq.{store_id}"}, body=payload.model_dump(mode="json"), prefer="return=representation")
        if not rows:
            raise HTTPException(status_code=404, detail="Store tidak ditemukan.")
        return rows[0]


async def delete_master_store(store_id: str):
    async with httpx.AsyncClient(timeout=10) as client:
        rows = await _request(client, "DELETE", "stores", params={"store_id": f"eq.{store_id}"}, prefer="return=representation")
        if not rows:
            raise HTTPException(status_code=404, detail="Store tidak ditemukan.")
        return {"deleted": True}
