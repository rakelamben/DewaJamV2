from datetime import date, datetime, timedelta, timezone
from typing import Any

import httpx
from fastapi import HTTPException

from auth import InternalUser
from oas import _request


def _date_range(date_from: str | None, date_to: str | None) -> tuple[str, str]:
    try:
        end = date.fromisoformat(date_to) if date_to else datetime.now(timezone.utc).date()
        start = date.fromisoformat(date_from) if date_from else end - timedelta(days=29)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Format tanggal harus YYYY-MM-DD.") from exc
    if start > end:
        raise HTTPException(status_code=422, detail="Tanggal mulai tidak boleh melebihi tanggal akhir.")
    if (end - start).days > 366:
        raise HTTPException(status_code=422, detail="Rentang laporan maksimal 366 hari.")
    return start.isoformat(), end.isoformat()


def _number(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0


async def get_dashboard(user: InternalUser, *, date_from: str | None = None, date_to: str | None = None, channel: str | None = None) -> dict[str, Any]:
    start, end = _date_range(date_from, date_to)
    summary_params: dict[str, str] = {"select": "*", "and": f"(summary_date.gte.{start},summary_date.lte.{end})", "order": "summary_date.asc"}
    if channel:
        summary_params["channel"] = f"eq.{channel}"

    async with httpx.AsyncClient(timeout=20) as client:
        daily_rows = await _request(client, "GET", "mis_daily_sales_summary", params=summary_params)
        product_rows = await _request(client, "GET", "mis_product_daily_summary", params={"select": "*", "and": f"(summary_date.gte.{start},summary_date.lte.{end})", "order": "summary_date.desc", "limit": "10000"})
        products = await _request(client, "GET", "products", params={"select": "product_id,nama_barang,kategori,brand,stok,minimum_stok", "limit": "10000"})
        transaction_params = {"select": "status,total_harga,channel,tanggal_transaksi", "and": f"(tanggal_transaksi.gte.{start}T00:00:00Z,tanggal_transaksi.lte.{end}T23:59:59Z)", "limit": "10000"}
        if channel:
            transaction_params["channel"] = f"eq.{channel}"
        transaction_rows = await _request(client, "GET", "transactions", params=transaction_params)

    categories = {str(row.get("product_id")): row for row in products}
    daily_map: dict[str, dict[str, Any]] = {}
    channel_map: dict[str, dict[str, Any]] = {}
    totals = {"transactions": 0, "items": 0, "revenue": 0, "hpp": 0, "profit": 0, "shipping": 0, "unique_customers": 0, "new_customers": 0, "canceled": 0}
    for row in daily_rows:
        day = str(row.get("summary_date"))
        channel_name = str(row.get("channel") or "unknown")
        entry = daily_map.setdefault(day, {"date": day, "revenue": 0, "profit": 0, "transactions": 0, "items": 0})
        entry["revenue"] += _number(row.get("total_pendapatan") or row.get("gross_sales"))
        entry["profit"] += _number(row.get("gross_profit"))
        entry["transactions"] += int(_number(row.get("jumlah_transaksi")))
        entry["items"] += int(_number(row.get("jumlah_item_terjual")))
        channel_entry = channel_map.setdefault(channel_name, {"channel": channel_name, "revenue": 0, "profit": 0, "transactions": 0})
        channel_entry["revenue"] += _number(row.get("total_pendapatan") or row.get("gross_sales"))
        channel_entry["profit"] += _number(row.get("gross_profit"))
        channel_entry["transactions"] += int(_number(row.get("jumlah_transaksi")))
        totals["transactions"] += int(_number(row.get("jumlah_transaksi")))
        totals["items"] += int(_number(row.get("jumlah_item_terjual")))
        totals["revenue"] += _number(row.get("total_pendapatan") or row.get("gross_sales"))
        totals["hpp"] += _number(row.get("total_hpp"))
        totals["profit"] += _number(row.get("gross_profit"))
        totals["shipping"] += _number(row.get("pendapatan_ongkir"))
        totals["unique_customers"] += int(_number(row.get("pelanggan_unik")))
        totals["new_customers"] += int(_number(row.get("pelanggan_baru")))
        totals["canceled"] += int(_number(row.get("jumlah_transaksi_batal")))

    status_map: dict[str, dict[str, Any]] = {}
    for row in transaction_rows:
        status_name = str(row.get("status") or "unknown")
        current = status_map.setdefault(status_name, {"status": status_name, "count": 0, "revenue": 0})
        current["count"] += 1
        current["revenue"] += _number(row.get("total_harga"))
    if not daily_rows:
        for row in transaction_rows:
            if str(row.get("status") or "").lower() in {"canceled", "cancelled", "canceled"}:
                continue
            day = str(row.get("tanggal_transaksi") or "")[:10]
            if not day:
                continue
            entry = daily_map.setdefault(day, {"date": day, "revenue": 0, "profit": 0, "transactions": 0, "items": 0})
            entry["revenue"] += _number(row.get("total_harga"))
            entry["transactions"] += 1
            totals["revenue"] += _number(row.get("total_harga"))
            totals["transactions"] += 1
    product_map: dict[str, dict[str, Any]] = {}
    for row in product_rows:
        product_id = str(row.get("product_id"))
        entry = product_map.setdefault(product_id, {"product_id": product_id, "name": categories.get(product_id, {}).get("nama_barang", product_id), "qty": 0, "revenue": 0, "profit": 0})
        entry["qty"] += int(_number(row.get("qty_terjual")))
        entry["revenue"] += _number(row.get("pendapatan"))
        entry["profit"] += _number(row.get("profit"))
    low_stock = [{**row, "stock_threshold": int(_number(row.get("minimum_stok"))) or 5} for row in products if int(_number(row.get("stok"))) <= (int(_number(row.get("minimum_stok"))) or 5)]
    return {
        "period": {"date_from": start, "date_to": end, "channel": channel},
        "kpis": {**totals, "average_transaction": totals["revenue"] / totals["transactions"] if totals["transactions"] else 0, "margin": totals["profit"] / totals["revenue"] * 100 if totals["revenue"] else 0},
        "daily": list(daily_map.values()),
        "channels": list(channel_map.values()),
        "statuses": list(status_map.values()),
        "top_products": sorted(product_map.values(), key=lambda row: row["revenue"], reverse=True)[:10],
        "low_stock": sorted(low_stock, key=lambda row: int(_number(row.get("stok")))),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
