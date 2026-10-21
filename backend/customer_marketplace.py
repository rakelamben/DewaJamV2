from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import httpx
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, Field

from customer_auth import customer_bearer, get_customer_profile
from oas import create_internal_notification, record_activity
from pos import _headers, _request


class AddressInput(BaseModel):
    label: str = Field(min_length=1, max_length=100)
    recipient_name: str = Field(min_length=1, max_length=255)
    recipient_phone: str = Field(min_length=1, max_length=50)
    address: str = Field(min_length=1)
    is_default: bool = False


class AddressUpdate(AddressInput):
    pass


class MarketplaceItemInput(BaseModel):
    product_id: str
    qty: int = Field(gt=0)


class MarketplaceCheckoutInput(BaseModel):
    items: list[MarketplaceItemInput] = Field(min_length=1)
    address_id: str | None = None
    fulfillment_method: str = "pickup"
    payment_method: str
    shipping_fee: Decimal = Field(default=Decimal("0"), ge=0)
    store_id: str | None = None


async def _customer(credentials: HTTPAuthorizationCredentials | None) -> dict[str, str | None]:
    return await get_customer_profile(credentials)


async def list_addresses(credentials: HTTPAuthorizationCredentials | None = Depends(customer_bearer)):
    profile = await _customer(credentials)
    async with httpx.AsyncClient(timeout=10) as client:
        return await _request(
            client,
            "GET",
            "customer_addresses",
            params={
                "customer_id": f"eq.{profile['customer_id']}",
                "select": "address_id,label,recipient_name,recipient_phone,address,is_default,created_at,updated_at",
                "order": "is_default.desc,created_at.desc",
            },
        )


async def create_address(payload: AddressInput, credentials: HTTPAuthorizationCredentials | None = Depends(customer_bearer)):
    profile = await _customer(credentials)
    async with httpx.AsyncClient(timeout=10) as client:
        if payload.is_default:
            await _request(
                client,
                "PATCH",
                "customer_addresses",
                params={"customer_id": f"eq.{profile['customer_id']}"},
                body={"is_default": False},
                prefer="return=minimal",
            )
        rows = await _request(
            client,
            "POST",
            "customer_addresses",
            body={
                "address_id": str(uuid4()),
                "customer_id": profile["customer_id"],
                **payload.model_dump(),
            },
            prefer="return=representation",
        )
        return rows[0] if rows else payload.model_dump()


async def update_address(address_id: str, payload: AddressUpdate, credentials: HTTPAuthorizationCredentials | None = Depends(customer_bearer)):
    profile = await _customer(credentials)
    async with httpx.AsyncClient(timeout=10) as client:
        if payload.is_default:
            await _request(client, "PATCH", "customer_addresses", params={"customer_id": f"eq.{profile['customer_id']}"}, body={"is_default": False}, prefer="return=minimal")
        rows = await _request(client, "PATCH", "customer_addresses", params={"address_id": f"eq.{address_id}", "customer_id": f"eq.{profile['customer_id']}"}, body=payload.model_dump(), prefer="return=representation")
        if not rows:
            raise HTTPException(status_code=404, detail="Alamat tidak ditemukan.")
        return rows[0]


async def delete_address(address_id: str, credentials: HTTPAuthorizationCredentials | None = Depends(customer_bearer)):
    profile = await _customer(credentials)
    async with httpx.AsyncClient(timeout=10) as client:
        rows = await _request(client, "DELETE", "customer_addresses", params={"address_id": f"eq.{address_id}", "customer_id": f"eq.{profile['customer_id']}"}, prefer="return=representation")
        if not rows:
            raise HTTPException(status_code=404, detail="Alamat tidak ditemukan.")
        return {"deleted": True}


async def create_marketplace_transaction(
    payload: MarketplaceCheckoutInput,
    credentials: HTTPAuthorizationCredentials | None = Depends(customer_bearer),
):
    profile = await _customer(credentials)
    if payload.payment_method not in {"virtual_account", "e_wallet", "store_payment"}:
        raise HTTPException(status_code=422, detail="Metode pembayaran marketplace tidak tersedia.")
    if payload.fulfillment_method not in {"pickup", "delivery"}:
        raise HTTPException(status_code=422, detail="Metode fulfillment tidak tersedia.")
    if payload.fulfillment_method == "delivery":
        if not payload.address_id:
            raise HTTPException(status_code=422, detail="Alamat wajib dipilih untuk delivery.")
        if payload.store_id:
            raise HTTPException(status_code=422, detail="Delivery tidak menggunakan store pickup.")
        if payload.payment_method == "store_payment":
            raise HTTPException(status_code=422, detail="Store payment hanya tersedia untuk pickup.")
    if payload.fulfillment_method == "pickup" and payload.address_id:
        raise HTTPException(status_code=422, detail="Pickup tidak menggunakan alamat delivery.")
    if payload.fulfillment_method == "pickup" and not payload.store_id:
        raise HTTPException(status_code=422, detail="Store pickup wajib dipilih.")

    quantities: dict[str, int] = {}
    for item in payload.items:
        quantities[item.product_id] = quantities.get(item.product_id, 0) + item.qty

    async with httpx.AsyncClient(timeout=15) as client:
        selected_address = None
        if payload.fulfillment_method == "delivery":
            address_rows = await _request(client, "GET", "customer_addresses", params={"address_id": f"eq.{payload.address_id}", "customer_id": f"eq.{profile['customer_id']}", "select": "*"})
            if not address_rows:
                raise HTTPException(status_code=422, detail="Alamat delivery tidak ditemukan.")
            selected_address = address_rows[0]
        selected_store = None
        if payload.fulfillment_method == "pickup":
            stores = await _request(client, "GET", "stores", params={"is_active": "eq.true", "select": "store_id,name,address,google_maps_url,opening_hours", "order": "name"})
            if payload.store_id:
                selected_store = next((store for store in stores if str(store["store_id"]) == payload.store_id), None)
            if not selected_store:
                raise HTTPException(status_code=422, detail="Store pickup tidak ditemukan atau tidak aktif.")
        products = await _request(
            client,
            "GET",
            "products",
            params={"product_id": f"in.({','.join(quantities)})", "select": "product_id,nama_barang,harga,stok"},
        )
        by_id = {str(product["product_id"]): product for product in products}
        if len(by_id) != len(quantities):
            raise HTTPException(status_code=422, detail="Ada produk yang tidak ditemukan.")

        transaction_id = str(uuid4())
        transaction_items = []
        subtotal = Decimal("0")
        for product_id, qty in quantities.items():
            product = by_id[product_id]
            if qty > int(product["stok"]):
                raise HTTPException(status_code=409, detail=f"Stok {product['nama_barang']} tidak mencukupi.")
            price = Decimal(str(product["harga"]))
            line_total = price * qty
            subtotal += line_total
            transaction_items.append({
                "item_id": str(uuid4()),
                "transaction_id": transaction_id,
                "product_id": product_id,
                "nama_barang_snapshot": product["nama_barang"],
                "harga_satuan": str(price),
                "qty": qty,
                "subtotal": str(line_total),
            })

        total = subtotal + payload.shipping_fee
        invoice = f"INV-{datetime.now(timezone.utc):%Y%m%d}-{uuid4().hex[:8].upper()}"
        transaction = {
            "transaction_id": transaction_id,
            "no_invoice": invoice,
            "customer_id": profile["customer_id"],
            "tanggal_transaksi": datetime.now(timezone.utc).isoformat(),
            "total_harga": str(total),
            "status": "selesai",
            "personnel_id": None,
            "channel": "marketplace",
            "order_status": "pending",
            "payment_status": "unpaid",
            "payment_method": payload.payment_method,
            "fulfillment_method": payload.fulfillment_method,
            "subtotal": str(subtotal),
            "shipping_fee": str(payload.shipping_fee),
            "paid_amount": None,
            "change_amount": None,
        }
        await _request(client, "POST", "transactions", body=transaction, prefer="return=minimal")
        await _request(client, "POST", "transaction_items", body=transaction_items, prefer="return=minimal")
        await _request(
            client,
            "POST",
            "payments",
            body={
                "payment_id": str(uuid4()),
                "transaction_id": transaction_id,
                "payment_method": payload.payment_method,
                "amount": str(total),
                "status": "pending",
                "reference": None,
                "paid_at": None,
            },
            prefer="return=minimal",
        )
        await _request(
            client,
            "POST",
            "fulfillments",
            body={
                "fulfillment_id": str(uuid4()),
                "transaction_id": transaction_id,
                "method": payload.fulfillment_method,
                "status": "pending",
                "shipping_fee": str(payload.shipping_fee),
                "recipient_name": selected_address["recipient_name"] if selected_address else None,
                "recipient_phone": selected_address["recipient_phone"] if selected_address else None,
                "address": selected_address["address"] if selected_address else None,
                "store_id": selected_store["store_id"] if selected_store else None,
                "notes": selected_store["name"] if selected_store else None,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
            prefer="return=minimal",
        )
        result = {
            "transaction_id": transaction_id,
            "no_invoice": invoice,
            "total_harga": str(total),
            "payment_status": "unpaid",
            "order_status": "pending",
            "payment_method": payload.payment_method,
            "fulfillment_method": payload.fulfillment_method,
        }
        await record_activity(
            None,
            action="create",
            resource_type="transaction",
            resource_id=transaction_id,
            module="marketplace",
            status="success",
            description=f"Order marketplace {invoice} berhasil dibuat.",
            metadata={
                "invoice": invoice,
                "customer_id": profile["customer_id"],
                "payment_method": payload.payment_method,
                "fulfillment_method": payload.fulfillment_method,
                "total": str(total),
            },
        )
        await create_internal_notification(
            "marketplace_order_created",
            title="Order marketplace baru",
            message=f"Order {invoice} menunggu proses pembayaran.",
            severity="info",
            reference_table="transactions",
            reference_id=transaction_id,
            target_roles=["staf_operasional", "kasir", "manager", "admin"],
        )
        await create_internal_notification(
            "payment_pending",
            title="Pembayaran marketplace menunggu",
            message=f"Pembayaran order {invoice} belum dikonfirmasi.",
            severity="warning",
            reference_table="payments",
            reference_id=transaction_id,
            target_roles=["staf_operasional", "kasir", "manager"],
        )
        return result


async def confirm_marketplace_payment(transaction_id: str, credentials: HTTPAuthorizationCredentials | None = Depends(customer_bearer)):
    profile = await _customer(credentials)
    async with httpx.AsyncClient(timeout=15) as client:
        transactions = await _request(client, "GET", "transactions", params={"transaction_id": f"eq.{transaction_id}", "customer_id": f"eq.{profile['customer_id']}", "channel": "eq.marketplace", "select": "*"})
        if not transactions:
            raise HTTPException(status_code=404, detail="Pesanan tidak ditemukan.")
        transaction = transactions[0]
        if transaction.get("payment_method") == "store_payment":
            raise HTTPException(status_code=422, detail="Store payment dikonfirmasi oleh toko.")
        if transaction.get("payment_status") == "paid":
            return await get_customer_order(transaction_id, credentials)

        items = await _request(client, "GET", "transaction_items", params={"transaction_id": f"eq.{transaction_id}", "select": "product_id,qty"})
        for item in items:
            products = await _request(client, "GET", "products", params={"product_id": f"eq.{item['product_id']}", "select": "stok"})
            if not products or int(products[0]["stok"]) < int(item["qty"]):
                raise HTTPException(status_code=409, detail="Stok produk tidak mencukupi.")
            old_stock = int(products[0]["stok"])
            qty = int(item["qty"])
            changed = await _request(client, "PATCH", "products", params={"product_id": f"eq.{item['product_id']}", "stok": f"eq.{old_stock}"}, body={"stok": old_stock - qty}, prefer="return=representation")
            if not changed:
                raise HTTPException(status_code=409, detail="Stok baru saja berubah. Silakan coba lagi.")
            await _request(client, "POST", "mis_stock_movements", body={"movement_id": str(uuid4()), "product_id": item["product_id"], "tipe_mutasi": "sale_out", "qty_change": -qty, "stok_sebelum": old_stock, "stok_sesudah": old_stock - qty, "transaction_id": transaction_id, "alasan": "Pembayaran marketplace dikonfirmasi"}, prefer="return=minimal")

        await _request(client, "PATCH", "transactions", params={"transaction_id": f"eq.{transaction_id}"}, body={"payment_status": "paid", "order_status": "processing"}, prefer="return=minimal")
        await _request(client, "PATCH", "payments", params={"transaction_id": f"eq.{transaction_id}"}, body={"status": "paid", "paid_at": datetime.now(timezone.utc).isoformat()}, prefer="return=minimal")
        await record_activity(
            None,
            action="confirm_payment",
            resource_type="transaction",
            resource_id=transaction_id,
            module="marketplace",
            status="success",
            description="Pembayaran marketplace dikonfirmasi customer.",
            metadata={"payment_method": transaction.get("payment_method")},
        )
        await create_internal_notification(
            "marketplace_payment_confirmed",
            title="Pembayaran marketplace dikonfirmasi",
            message=f"Pembayaran order {transaction.get('no_invoice', transaction_id)} berhasil dikonfirmasi.",
            severity="success",
            reference_table="transactions",
            reference_id=transaction_id,
            target_roles=["staf_operasional", "kasir", "staf_gudang", "gudang", "manager"],
        )
        await create_internal_notification(
            "marketplace_order_processing",
            title="Order marketplace perlu diproses",
            message=f"Order {transaction.get('no_invoice', transaction_id)} masuk status processing.",
            severity="info",
            reference_table="transactions",
            reference_id=transaction_id,
            target_roles=["staf_gudang", "gudang", "staf_operasional", "kasir"],
        )
        return await get_customer_order(transaction_id, credentials)


async def list_marketplace_stores():
    async with httpx.AsyncClient(timeout=10) as client:
        return await _request(client, "GET", "stores", params={"is_active": "eq.true", "select": "store_id,name,address,google_maps_url,opening_hours", "order": "name"})


async def list_customer_orders(credentials: HTTPAuthorizationCredentials | None = Depends(customer_bearer)):
    profile = await _customer(credentials)
    async with httpx.AsyncClient(timeout=10) as client:
        return await _request(
            client,
            "GET",
            "transactions",
            params={
                "customer_id": f"eq.{profile['customer_id']}",
                "channel": "eq.marketplace",
                "select": "transaction_id,no_invoice,tanggal_transaksi,total_harga,status,order_status,payment_status,payment_method,fulfillment_method",
                "order": "tanggal_transaksi.desc",
            },
        )


async def get_customer_order(transaction_id: str, credentials: HTTPAuthorizationCredentials | None = Depends(customer_bearer)):
    profile = await _customer(credentials)
    async with httpx.AsyncClient(timeout=10) as client:
        rows = await _request(client, "GET", "transactions", params={"transaction_id": f"eq.{transaction_id}", "customer_id": f"eq.{profile['customer_id']}", "channel": "eq.marketplace", "select": "*"})
        if not rows:
            raise HTTPException(status_code=404, detail="Pesanan tidak ditemukan.")
        transaction = rows[0]
        transaction["items"] = await _request(client, "GET", "transaction_items", params={"transaction_id": f"eq.{transaction_id}", "select": "*"})
        payments = await _request(client, "GET", "payments", params={"transaction_id": f"eq.{transaction_id}", "select": "*"})
        fulfillments = await _request(client, "GET", "fulfillments", params={"transaction_id": f"eq.{transaction_id}", "select": "*"})
        transaction["payment"] = payments[0] if payments else None
        transaction["fulfillment"] = fulfillments[0] if fulfillments else None
        return transaction
