import csv
import io
from datetime import date
from typing import Any

import httpx
from fastapi import HTTPException

from oas import _request


def validate_period(date_from: date, date_to: date) -> None:
    if date_from > date_to:
        raise HTTPException(status_code=422, detail="Tanggal mulai tidak boleh melebihi tanggal akhir.")
    if (date_to - date_from).days > 366:
        raise HTTPException(status_code=422, detail="Rentang laporan maksimal 366 hari.")


async def sales_report(client: httpx.AsyncClient, date_from: date, date_to: date, channel: str | None = None) -> dict[str, Any]:
    validate_period(date_from, date_to)
    params: dict[str, str] = {"select": "*", "summary_date": f"gte.{date_from}", "and": f"(summary_date.lte.{date_to})", "order": "summary_date.asc"}
    if channel:
        params["channel"] = f"eq.{channel}"
    rows = await _request(client, "GET", "mis_daily_sales_summary", params=params)
    items = [{"date": row.get("summary_date"), "channel": row.get("channel"), "transactions": int(row.get("jumlah_transaksi") or 0), "items": int(row.get("jumlah_item_terjual") or 0), "gross_sales": float(row.get("gross_sales") or 0), "shipping_revenue": float(row.get("pendapatan_ongkir") or 0), "total_revenue": float(row.get("total_pendapatan") or 0), "canceled": int(row.get("jumlah_transaksi_batal") or 0)} for row in rows]
    return {"period": {"date_from": date_from.isoformat(), "date_to": date_to.isoformat(), "channel": channel}, "summary": {"transactions": sum(row["transactions"] for row in items), "items": sum(row["items"] for row in items), "revenue": sum(row["total_revenue"] for row in items), "shipping": sum(row["shipping_revenue"] for row in items), "canceled": sum(row["canceled"] for row in items)}, "items": items}


async def profitability_report(client: httpx.AsyncClient, date_from: date, date_to: date, product_id: str | None = None) -> dict[str, Any]:
    validate_period(date_from, date_to)
    params: dict[str, str] = {"select": "*", "summary_date": f"gte.{date_from}", "and": f"(summary_date.lte.{date_to})", "order": "pendapatan.desc", "limit": "10000"}
    if product_id:
        params["product_id"] = f"eq.{product_id}"
    rows = await _request(client, "GET", "mis_product_daily_summary", params=params)
    products = await _request(client, "GET", "products", params={"select": "product_id,nama_barang,kategori,brand", "limit": "10000"})
    product_map = {row["product_id"]: row for row in products}
    grouped: dict[str, dict[str, Any]] = {}
    for row in rows:
        key = str(row.get("product_id"))
        item = grouped.setdefault(key, {"product_id": key, "product_name": product_map.get(key, {}).get("nama_barang", key), "category": product_map.get(key, {}).get("kategori"), "brand": product_map.get(key, {}).get("brand"), "qty_sold": 0, "revenue": 0, "hpp": 0, "profit": 0})
        item["qty_sold"] += int(row.get("qty_terjual") or 0)
        item["revenue"] += float(row.get("pendapatan") or 0)
        item["hpp"] += float(row.get("total_hpp") or 0)
        item["profit"] += float(row.get("profit") or 0)
    items = [{**item, "margin_percentage": item["profit"] / item["revenue"] * 100 if item["revenue"] else 0} for item in grouped.values()]
    revenue = sum(row["revenue"] for row in items)
    hpp = sum(row["hpp"] for row in items)
    profit = sum(row["profit"] for row in items)
    return {"period": {"date_from": date_from.isoformat(), "date_to": date_to.isoformat()}, "summary": {"revenue": revenue, "hpp": hpp, "gross_profit": profit, "margin_percentage": profit / revenue * 100 if revenue else 0}, "items": sorted(items, key=lambda row: row["revenue"], reverse=True)}


async def inventory_report(client: httpx.AsyncClient, date_from: date, date_to: date, stock_status: str = "all", category: str | None = None) -> dict[str, Any]:
    validate_period(date_from, date_to)
    params: dict[str, str] = {"select": "product_id,nama_barang,kategori,brand,stok,minimum_stok,reorder_point", "order": "nama_barang.asc", "limit": "10000"}
    if category:
        params["kategori"] = f"eq.{category}"
    products = await _request(client, "GET", "products", params=params)
    movements = await _request(client, "GET", "mis_stock_movements", params={"select": "product_id,created_at", "created_at": f"gte.{date_from}T00:00:00Z", "and": f"(created_at.lte.{date_to}T23:59:59Z)", "order": "created_at.desc", "limit": "10000"})
    latest = {}
    for movement in movements:
        latest.setdefault(movement.get("product_id"), movement.get("created_at"))
    items = []
    for product in products:
        stock = int(product.get("stok") or 0)
        minimum = int(product.get("minimum_stok") or 0)
        state = "out_of_stock" if stock <= 0 else ("low_stock" if stock <= (minimum or 5) else "in_stock")
        if stock_status != "all" and stock_status != state:
            continue
        items.append({**product, "stock_status": state, "last_movement_at": latest.get(product.get("product_id"))})
    return {"period": {"date_from": date_from.isoformat(), "date_to": date_to.isoformat()}, "summary": {"total_products": len(products), "in_stock": sum(1 for row in items if row["stock_status"] == "in_stock"), "low_stock": sum(1 for row in items if row["stock_status"] == "low_stock"), "out_of_stock": sum(1 for row in items if row["stock_status"] == "out_of_stock"), "total_stock_units": sum(int(row.get("stok") or 0) for row in items)}, "items": items}


def to_csv(data: dict[str, Any], report_type: str) -> io.StringIO:
    output = io.StringIO()
    rows = data.get("items", [])
    writer = csv.DictWriter(output, fieldnames=list(rows[0].keys()) if rows else ["message"])
    writer.writeheader()
    if rows:
        writer.writerows(rows)
    else:
        writer.writerow({"message": f"Tidak ada data untuk {report_type}."})
    output.seek(0)
    return output
