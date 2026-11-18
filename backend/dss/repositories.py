from collections import defaultdict
from datetime import date, timedelta
from statistics import median
from typing import Any
from uuid import uuid4

import httpx

from .database import request


async def load_product_rows(client: httpx.AsyncClient, *, category: str | None, window_days: int) -> list[dict[str, Any]]:
    params = {"select": "product_id,nama_barang,kategori,brand,harga,stok,minimum_stok,reorder_point,created_at"}
    if category: params["kategori"] = f"eq.{category}"
    products = await request(client, "GET", "products", params=params)
    ids = [str(row["product_id"]) for row in products]
    if not ids: return []
    in_ids = f"({','.join(ids)})"
    today = date.today()
    start = today - timedelta(days=window_days)
    previous_start = today - timedelta(days=window_days * 2)
    summaries = await request(client, "GET", "mis_product_daily_summary", params={"product_id": f"in.{in_ids}", "summary_date": f"gte.{previous_start}", "select": "product_id,summary_date,qty_terjual,profit,generated_at"})
    costs = await request(client, "GET", "mis_product_costs", params={"product_id": f"in.{in_ids}", "berlaku_dari": f"lte.{today}", "select": "product_id,harga_beli,berlaku_dari,berlaku_sampai,supplier_id,supplier_nama"})
    movements = await request(client, "GET", "mis_stock_movements", params={"product_id": f"in.{in_ids}", "tipe_mutasi": "eq.purchase_in", "select": "product_id,created_at", "order": "created_at.desc"})
    by_product: dict[str, dict[str, float]] = defaultdict(lambda: {"qty30": 0.0, "qty_prev": 0.0, "profit30": 0.0})
    for row in summaries:
        product_id = str(row["product_id"])
        summary_date = date.fromisoformat(str(row["summary_date"])[:10])
        if summary_date >= start:
            by_product[product_id]["qty30"] += float(row.get("qty_terjual") or 0)
            by_product[product_id]["profit30"] += float(row.get("profit") or 0)
        elif summary_date >= previous_start:
            by_product[product_id]["qty_prev"] += float(row.get("qty_terjual") or 0)
    active_cost: dict[str, dict[str, Any]] = {}
    for row in costs:
        if row.get("berlaku_sampai") and str(row["berlaku_sampai"])[:10] < str(today): continue
        product_id = str(row["product_id"])
        if product_id not in active_cost or str(row.get("berlaku_dari")) > str(active_cost[product_id].get("berlaku_dari")):
            active_cost[product_id] = row
    last_purchase: dict[str, str] = {}
    for row in movements:
        last_purchase.setdefault(str(row["product_id"]), str(row.get("created_at")))
    generated_values = [str(row.get("generated_at")) for row in summaries if row.get("generated_at")]
    latest_generated = max(generated_values) if generated_values else None
    result = []
    for product in products:
        product_id = str(product["product_id"])
        row = {**product, **by_product[product_id], **active_cost.get(product_id, {}), "last_purchase_in": last_purchase.get(product_id), "window_days": window_days, "latest_generated_at": latest_generated}
        result.append(row)
    return result


async def load_supplier_rows(client: httpx.AsyncClient, *, category: str | None, window_days: int, min_purchases: int) -> list[dict[str, Any]]:
    suppliers = await request(client, "GET", "suppliers", params={"is_active": "eq.true", "select": "supplier_id,nama,is_active"})
    purchases = await request(client, "GET", "supplier_purchases", params={"tanggal_pesan": f"gte.{date.today() - timedelta(days=window_days)}", "status": "in.(diterima,diterima_sebagian)", "select": "purchase_id,supplier_id,tanggal_pesan,tanggal_estimasi_terima,tanggal_terima,status"})
    purchase_ids = [str(item["purchase_id"]) for item in purchases]
    items = await request(client, "GET", "supplier_purchase_items", params={"purchase_id": f"in.({','.join(purchase_ids)})", "select": "purchase_id,product_id,qty_pesan,qty_terima,qty_rusak,qty_retur,harga_beli_satuan"}) if purchase_ids else []
    product_ids = list({str(item["product_id"]) for item in items})
    products = await request(client, "GET", "products", params={"product_id": f"in.({','.join(product_ids)})", "select": "product_id,kategori"}) if product_ids else []
    categories = {str(row["product_id"]): row.get("kategori") for row in products}
    if category: items = [item for item in items if categories.get(str(item["product_id"])) == category]
    by_purchase: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in items: by_purchase[str(item["purchase_id"])].append(item)
    price_values: dict[str, list[float]] = defaultdict(list)
    for item in items: price_values[str(item["product_id"])].append(float(item.get("harga_beli_satuan") or 0))
    by_supplier: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for purchase in purchases:
        if not by_purchase.get(str(purchase["purchase_id"])): continue
        by_supplier[str(purchase["supplier_id"])].append(purchase)
    output = []
    for supplier in suppliers:
        supplier_id = str(supplier["supplier_id"])
        supplier_purchases = by_supplier.get(supplier_id, [])
        if len(supplier_purchases) < min_purchases:
            output.append({**supplier, "_excluded_reason": f"data PO kurang (n < {min_purchases})"})
            continue
        supplier_items = [item for purchase in supplier_purchases for item in by_purchase[str(purchase["purchase_id"])] ]
        indexes = []
        total_ordered = total_received = total_defect = 0.0
        lead_times = []
        on_time = 0
        on_time_total = 0
        for purchase in supplier_purchases:
            purchase_items = by_purchase[str(purchase["purchase_id"])]
            for item in purchase_items:
                prices = price_values[str(item["product_id"])]
                if prices and median(prices) > 0: indexes.append((float(item["harga_beli_satuan"]) / median(prices)) * float(item.get("qty_pesan") or 0))
                total_ordered += float(item.get("qty_pesan") or 0)
                total_received += float(item.get("qty_terima") or 0)
                total_defect += float(item.get("qty_rusak") or 0) + float(item.get("qty_retur") or 0)
            if purchase.get("tanggal_terima") and purchase.get("tanggal_pesan"):
                lead_times.append((date.fromisoformat(str(purchase["tanggal_terima"])[:10]) - date.fromisoformat(str(purchase["tanggal_pesan"])[:10])).days)
            if purchase.get("tanggal_estimasi_terima") and purchase.get("tanggal_terima"):
                on_time_total += 1
                if str(purchase["tanggal_terima"])[:10] <= str(purchase["tanggal_estimasi_terima"])[:10]: on_time += 1
        if not on_time_total:
            output.append({**supplier, "_excluded_reason": "tidak ada PO dengan tanggal estimasi dan tanggal terima"})
            continue
        output.append({**supplier, "price_index": sum(indexes) / sum(float(item.get("qty_pesan") or 0) for item in supplier_items) if indexes else 1, "lead_time": sum(lead_times) / len(lead_times) if lead_times else 0, "fill_rate": total_received / total_ordered * 100 if total_ordered else 0, "defect_rate": total_defect / total_received * 100 if total_received else 0, "on_time_rate": on_time / on_time_total * 100, "purchase_count": len(supplier_purchases), "product_count": len({str(item["product_id"]) for item in supplier_items})})
    return output


async def list_rows(client: httpx.AsyncClient, table: str, params: dict[str, str] | None = None) -> list[dict[str, Any]]:
    return await request(client, "GET", table, params=params or {"select": "*"})


async def create_row(client: httpx.AsyncClient, table: str, body: dict[str, Any]) -> dict[str, Any]:
    rows = await request(client, "POST", table, body=body, prefer="return=representation")
    return rows[0] if rows else body
