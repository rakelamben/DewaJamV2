from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
import logging
from typing import Any
from uuid import uuid4

import httpx
from fastapi import HTTPException, status
from pydantic import BaseModel, Field

from auth import InternalUser
from config import SUPABASE_DB_SCHEMA, SUPABASE_SECRET_KEY, SUPABASE_URL
from oas import create_internal_notification, record_activity

logger = logging.getLogger(__name__)


class PosItemInput(BaseModel):
    product_id: str
    qty: int = Field(gt=0)


class PosTransactionInput(BaseModel):
    buyer_name: str = Field(min_length=1, max_length=255)
    buyer_phone: str = Field(min_length=1, max_length=50)
    items: list[PosItemInput] = Field(min_length=1)
    payment_method: str
    paid_amount: Decimal = Field(ge=0)
    reference: str | None = None


class CancelTransactionInput(BaseModel):
    reason: str | None = None


def _headers(prefer: str | None = None) -> dict[str, str]:
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


async def _request(
    client: httpx.AsyncClient,
    method: str,
    path: str,
    *,
    params: dict[str, str] | None = None,
    body: Any = None,
    prefer: str | None = None,
) -> list[dict[str, Any]]:
    response = await client.request(
        method,
        f"{SUPABASE_URL}/rest/v1/{path}",
        headers=_headers(prefer),
        params=params,
        json=body,
    )
    if response.status_code >= 400:
        logger.error(
            "Supabase POS error: %s %s returned %s: %s",
            method,
            path,
            response.status_code,
            response.text,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Gagal mengakses data POS.",
        )
    if not response.content:
        return []
    return response.json()


def _today_range() -> tuple[str, str]:
    # POS sementara menggunakan hari kalender UTC; timezone toko dapat dikonfigurasi kemudian.
    today = datetime.now(timezone.utc).date()
    start = datetime.combine(today, time.min, tzinfo=timezone.utc).isoformat()
    end = datetime.combine(today + timedelta(days=1), time.min, tzinfo=timezone.utc).isoformat()
    return start, end


async def list_products() -> list[dict[str, Any]]:
    async with httpx.AsyncClient(timeout=10) as client:
        return await _request(
            client,
            "GET",
            "products",
            params={
                "select": "product_id,nama_barang,kategori,harga,stok,deskripsi,gambar_url,brand,tags",
                "order": "nama_barang.asc",
            },
        )


async def get_product(product_id: str) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=10) as client:
        products = await _request(
            client,
            "GET",
            "products",
            params={
                "product_id": f"eq.{product_id}",
                "select": "product_id,nama_barang,kategori,harga,stok,deskripsi,gambar_url,brand,tags",
            },
        )
        if not products:
            raise HTTPException(status_code=404, detail="Produk tidak ditemukan.")
        return products[0]


async def create_transaction(payload: PosTransactionInput, current_user: InternalUser) -> dict[str, Any]:
    allowed_methods = {"tunai", "QRIS", "debit"}
    if payload.payment_method not in allowed_methods:
        raise HTTPException(status_code=422, detail="Metode pembayaran tidak tersedia.")

    buyer_phone = payload.buyer_phone.strip() or "9999"
    
    quantities: dict[str, int] = {}
    for item in payload.items:
        quantities[item.product_id] = quantities.get(item.product_id, 0) + item.qty

    async with httpx.AsyncClient(timeout=15) as client:
        product_ids = ",".join(quantities)
        products = await _request(
            client,
            "GET",
            "products",
            params={
                "product_id": f"in.({product_ids})",
                "select": "product_id,nama_barang,harga,stok",
            },
        )
        by_id = {str(product["product_id"]): product for product in products}
        if len(by_id) != len(quantities):
            raise HTTPException(status_code=422, detail="Ada produk yang tidak ditemukan.")

        transaction_id = str(uuid4())
        items: list[dict[str, Any]] = []
        
        subtotal = Decimal("0")
        for product_id, qty in quantities.items():
            product = by_id[product_id]
            stock = int(product["stok"])
            if qty > stock:
                raise HTTPException(
                    status_code=409,
                    detail=f"Stok {product['nama_barang']} tidak mencukupi.",
                )
            price = Decimal(str(product["harga"]))
            
            line_total = price * qty
            subtotal += line_total
            items.append(
                {
                    "item_id": str(uuid4()),
                    "transaction_id": transaction_id,
                    "product_id": product_id,
                    "nama_barang_snapshot": product["nama_barang"],
                    "harga_satuan": str(price),
                    "qty": qty,
                    "subtotal": str(line_total),
                }
            )

        total = subtotal
        if payload.paid_amount < total:
            raise HTTPException(status_code=422, detail="Nominal pembayaran kurang dari total transaksi.")

        invoice = f"POS-{datetime.now(timezone.utc):%Y%m%d}-{uuid4().hex[:8].upper()}"
        change = payload.paid_amount - total
        transaction = {
            "transaction_id": transaction_id,
            "no_invoice": invoice,
            "customer_id": None,
            "buyer_name_snapshot": payload.buyer_name.strip(),
            "buyer_phone_snapshot": buyer_phone,
            "tanggal_transaksi": datetime.now(timezone.utc).isoformat(),
            "total_harga": str(total),
            "status": "completed",
            "personnel_id": current_user.entity_id,
            "channel": "pos",
            "order_status": "completed",
            "payment_status": "paid",
            "payment_method": payload.payment_method,
            "fulfillment_method": None,
            "subtotal": str(subtotal),
            "shipping_fee": "0",
            "paid_amount": str(payload.paid_amount),
            "change_amount": str(change),
        }
        payment = {
            "payment_id": str(uuid4()),
            "transaction_id": transaction_id,
            "payment_method": payload.payment_method,
            "amount": str(payload.paid_amount),
            "status": "paid",
            "reference": payload.reference,
            "paid_at": datetime.now(timezone.utc).isoformat(),
        }

        await _request(client, "POST", "transactions", body=transaction, prefer="return=representation")
        await _request(client, "POST", "transaction_items", body=items, prefer="return=minimal")
        await _request(client, "POST", "payments", body=payment, prefer="return=minimal")

        for product_id, qty in quantities.items():
            product = by_id[product_id]
            old_stock = int(product["stok"])
            new_stock = old_stock - qty
            await _request(
                client,
                "PATCH",
                "products",
                params={"product_id": f"eq.{product_id}", "stok": f"eq.{old_stock}"},
                body={"stok": new_stock},
                prefer="return=minimal",
            )
            await _request(
                client,
                "POST",
                "mis_stock_movements",
                body={
                    "movement_id": str(uuid4()),
                    "product_id": product_id,
                    "tipe_mutasi": "sale_out",
                    "qty_change": -qty,
                    "stok_sebelum": old_stock,
                    "stok_sesudah": new_stock,
                    "transaction_id": transaction_id,
                    "alasan": "Penjualan POS",
                    "created_by": current_user.entity_id,
                },
                prefer="return=minimal",
            )

        transaction["items"] = items
        transaction["payment"] = payment
        await record_activity(
            current_user,
            action="create",
            resource_type="transaction",
            resource_id=transaction_id,
            module="pos",
            status="success",
            description=f"Transaksi POS {invoice} berhasil dibuat.",
            metadata={
                "invoice": invoice,
                "total": str(total),
                "payment_method": payload.payment_method,
                "item_count": len(items),
            },
        )
        await create_internal_notification(
            "pos_transaction_created",
            title="Transaksi POS baru",
            message=f"Transaksi {invoice} berhasil dibuat.",
            severity="success",
            reference_table="transactions",
            reference_id=transaction_id,
            target_roles=["manager", "admin"],
        )
        return transaction


async def list_today_transactions() -> list[dict[str, Any]]:
    start, end = _today_range()
    async with httpx.AsyncClient(timeout=10) as client:
        return await _request(
            client,
            "GET",
            "transactions",
            params={
                "select": "transaction_id,no_invoice,buyer_name_snapshot,buyer_phone_snapshot,tanggal_transaksi,total_harga,payment_method,status,order_status,payment_status,paid_amount,change_amount,personnel_id",
                "channel": "eq.pos",
                "tanggal_transaksi": f"gte.{start}",
                "and": f"(tanggal_transaksi.lt.{end})",
                "order": "tanggal_transaksi.desc",
            },
        )


async def get_transaction(transaction_id: str) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=10) as client:
        transactions = await _request(
            client,
            "GET",
            "transactions",
            params={"transaction_id": f"eq.{transaction_id}", "select": "*"},
        )
        if not transactions:
            raise HTTPException(status_code=404, detail="Transaksi tidak ditemukan.")
        transaction = transactions[0]
        transaction["items"] = await _request(
            client,
            "GET",
            "transaction_items",
            params={"transaction_id": f"eq.{transaction_id}", "select": "*"},
        )
        payments = await _request(
            client,
            "GET",
            "payments",
            params={"transaction_id": f"eq.{transaction_id}", "select": "*"},
        )
        transaction["payment"] = payments[0] if payments else None
        return transaction


async def cancel_transaction(
    transaction_id: str, payload: CancelTransactionInput, current_user: InternalUser
) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=15) as client:
        transactions = await _request(
            client,
            "GET",
            "transactions",
            params={"transaction_id": f"eq.{transaction_id}", "select": "*"},
        )
        if not transactions:
            raise HTTPException(status_code=404, detail="Transaksi tidak ditemukan.")
        transaction = transactions[0]
        if transaction.get("status") == "canceled":
            raise HTTPException(status_code=409, detail="Transaksi sudah dibatalkan.")

        items = await _request(
            client,
            "GET",
            "transaction_items",
            params={"transaction_id": f"eq.{transaction_id}", "select": "product_id,qty"},
        )
        for item in items:
            products = await _request(
                client,
                "GET",
                "products",
                params={"product_id": f"eq.{item['product_id']}", "select": "stok"},
            )
            if not products:
                continue
            old_stock = int(products[0]["stok"])
            qty = int(item["qty"])
            new_stock = old_stock + qty
            await _request(
                client,
                "PATCH",
                "products",
                params={"product_id": f"eq.{item['product_id']}"},
                body={"stok": new_stock},
                prefer="return=minimal",
            )
            await _request(
                client,
                "POST",
                "mis_stock_movements",
                body={
                    "movement_id": str(uuid4()),
                    "product_id": item["product_id"],
                    "tipe_mutasi": "sale_out",
                    "qty_change": qty,
                    "stok_sebelum": old_stock,
                    "stok_sesudah": new_stock,
                    "transaction_id": transaction_id,
                    "alasan": payload.reason or "Pembatalan transaksi POS",
                    "created_by": current_user.entity_id,
                },
                prefer="return=minimal",
            )

        await _request(
            client,
            "PATCH",
            "transactions",
            params={"transaction_id": f"eq.{transaction_id}"},
            body={"status": "canceled", "order_status": "canceled", "payment_status": "canceled"},
            prefer="return=minimal",
        )
        await _request(
            client,
            "PATCH",
            "payments",
            params={"transaction_id": f"eq.{transaction_id}"},
            body={"status": "canceled"},
            prefer="return=minimal",
        )
        return await get_transaction(transaction_id)
