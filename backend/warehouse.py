from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import httpx
from fastapi import HTTPException
from pydantic import BaseModel, Field

from auth import InternalUser
from oas import create_internal_notification, record_activity
from pos import _request

VALID_MOVEMENT_TYPES = {"purchase_in", "sale_out", "return_in", "return_out", "adjustment", "damaged"}
IN_TYPES = {"purchase_in", "return_in"}


class StockMovementInput(BaseModel):
    product_id: str
    tipe_mutasi: str
    qty_change: int
    alasan: str = Field(min_length=1, max_length=500)


async def get_stock():
    async with httpx.AsyncClient(timeout=10) as client:
        return await _request(client, "GET", "products", params={"select": "product_id,nama_barang,kategori,brand,stok,harga", "order": "nama_barang.asc"})


async def get_movements(product_id: str | None = None, movement_type: str | None = None):
    async with httpx.AsyncClient(timeout=10) as client:
        params: dict[str, str] = {"select": "*", "order": "created_at.desc", "limit": "500"}
        if product_id:
            params["product_id"] = f"eq.{product_id}"
        if movement_type:
            params["tipe_mutasi"] = f"eq.{movement_type}"
        movements = await _request(client, "GET", "mis_stock_movements", params=params)
        product_ids = {str(item["product_id"]) for item in movements}
        products: dict[str, dict[str, Any]] = {}
        if product_ids:
            rows = await _request(client, "GET", "products", params={"product_id": f"in.({','.join(product_ids)})", "select": "product_id,nama_barang,kategori,brand"})
            products = {str(row["product_id"]): row for row in rows}
        return [{**movement, "product": products.get(str(movement["product_id"]))} for movement in movements]


async def create_movement(payload: StockMovementInput, current_user: InternalUser):
    if payload.tipe_mutasi not in VALID_MOVEMENT_TYPES:
        raise HTTPException(status_code=422, detail="Tipe mutasi stok tidak valid.")
    if payload.qty_change == 0:
        raise HTTPException(status_code=422, detail="Perubahan stok tidak boleh nol.")
    if payload.tipe_mutasi != "adjustment" and payload.qty_change < 0:
        raise HTTPException(status_code=422, detail="Quantity mutasi harus positif untuk tipe ini.")

    async with httpx.AsyncClient(timeout=15) as client:
        products = await _request(client, "GET", "products", params={"product_id": f"eq.{payload.product_id}", "select": "product_id,stok"})
        if not products:
            raise HTTPException(status_code=404, detail="Produk tidak ditemukan.")
        old_stock = int(products[0]["stok"])
        delta = payload.qty_change if payload.tipe_mutasi == "adjustment" else payload.qty_change * (1 if payload.tipe_mutasi in IN_TYPES else -1)
        new_stock = old_stock + delta
        if new_stock < 0:
            raise HTTPException(status_code=409, detail="Stok akhir tidak boleh negatif.")
        changed = await _request(client, "PATCH", "products", params={"product_id": f"eq.{payload.product_id}", "stok": f"eq.{old_stock}"}, body={"stok": new_stock}, prefer="return=representation")
        if not changed:
            raise HTTPException(status_code=409, detail="Stok berubah oleh proses lain. Silakan refresh.")
        movement = {"movement_id": str(uuid4()), "product_id": payload.product_id, "tipe_mutasi": payload.tipe_mutasi, "qty_change": delta, "stok_sebelum": old_stock, "stok_sesudah": new_stock, "alasan": payload.alasan.strip(), "created_by": current_user.entity_id, "created_at": datetime.now(timezone.utc).isoformat()}
        try:
            rows = await _request(client, "POST", "mis_stock_movements", body=movement, prefer="return=representation")
        except Exception:
            await _request(client, "PATCH", "products", params={"product_id": f"eq.{payload.product_id}", "stok": f"eq.{new_stock}"}, body={"stok": old_stock}, prefer="return=minimal")
            raise
        result = rows[0] if rows else movement
        metadata = {
            "product_id": payload.product_id,
            "tipe_mutasi": payload.tipe_mutasi,
            "qty_change": delta,
            "stok_sebelum": old_stock,
            "stok_sesudah": new_stock,
            "transaction_id": None,
        }
        await record_activity(
            current_user,
            action="create",
            resource_type="stock_movement",
            resource_id=str(result.get("movement_id", movement["movement_id"])),
            module="warehouse",
            status="success",
            description=f"Membuat mutasi stok {payload.tipe_mutasi}.",
            metadata=metadata,
        )
        await create_internal_notification(
            "stock_movement_created",
            title="Mutasi stok baru",
            message=f"Mutasi {payload.tipe_mutasi} untuk produk berhasil dibuat.",
            severity="info",
            reference_table="mis_stock_movements",
            reference_id=str(result.get("movement_id", movement["movement_id"])),
            target_roles=["manager", "admin"],
        )
        if new_stock <= 5:
            await create_internal_notification(
                "low_stock",
                title="Stok menipis",
                message=f"Stok produk setelah mutasi tersisa {new_stock} unit.",
                severity="warning",
                reference_table="products",
                reference_id=payload.product_id,
                target_roles=["staf_gudang", "gudang", "manager", "admin"],
            )
        return result
