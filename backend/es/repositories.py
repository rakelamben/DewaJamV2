from typing import Any

import httpx

from .database import request


async def load_active_products(client: httpx.AsyncClient) -> list[dict[str, Any]]:
    try:
        return await request(
            client,
            "GET",
            "products",
            params={
                "select": "product_id,nama_barang,kategori,brand,harga,stok,gambar_url,tags,specs",
                "order": "nama_barang.asc",
            },
        )
    except RuntimeError:
        rows = await request(
            client,
            "GET",
            "products",
            params={
                "select": "product_id,nama_barang,kategori,brand,harga,stok,gambar_url,tags",
                "order": "nama_barang.asc",
            },
        )
        return [{**row, "specs": {}} for row in rows]


async def load_reference_options(client: httpx.AsyncClient, domain_code: str) -> list[dict[str, Any]]:
    code = domain_code.upper()
    if code == "STAFF_POS_CROSSSELL":
        rows = await request(
            client,
            "GET",
            "products",
            params={
                "kategori": "neq.Strap & Aksesoris",
                "select": "product_id,nama_barang,kategori,brand,harga,stok",
                "order": "nama_barang.asc",
            },
        )
        return [
            {
                "id": str(row["product_id"]),
                "label": f"{row['nama_barang']} ({row.get('kategori')}) — Stok: {row.get('stok')}",
                "reference_table": "products",
            }
            for row in rows
        ]

    if code == "WAREHOUSE_STOCK_ANOMALY":
        rows = await request(
            client,
            "GET",
            "products",
            params={
                "select": "product_id,nama_barang,kategori,stok,reorder_point",
                "order": "nama_barang.asc",
            },
        )
        return [
            {
                "id": str(row["product_id"]),
                "label": f"{row['nama_barang']} — Stok Sistem: {row.get('stok')} (ROP: {row.get('reorder_point') or 0})",
                "reference_table": "products",
            }
            for row in rows
        ]

    if code == "WAREHOUSE_QC_INBOUND":
        try:
            purchases = await request(
                client,
                "GET",
                "supplier_purchases",
                params={
                    "select": "purchase_id,no_po,tanggal_pesan,status,supplier_id",
                    "order": "tanggal_pesan.desc",
                    "limit": "50",
                },
            )
            return [
                {
                    "id": str(row["purchase_id"]),
                    "label": f"{row['no_po']} — Status: {row.get('status')} ({row.get('tanggal_pesan')})",
                    "reference_table": "supplier_purchases",
                }
                for row in purchases
            ]
        except RuntimeError:
            return []

    if code == "MGR_WORKFLOW_APPROVAL":
        rows = await request(
            client,
            "GET",
            "workflow_requests",
            params={
                "select": "request_id,title,tipe_request,current_status,created_at",
                "order": "created_at.desc",
                "limit": "50",
            },
        )
        return [
            {
                "id": str(row["request_id"]),
                "label": f"[{str(row.get('current_status') or '').upper()}] {row.get('title') or row.get('tipe_request')}",
                "reference_table": "workflow_requests",
            }
            for row in rows
        ]

    return []


async def load_knowledge_references(client: httpx.AsyncClient, domain_code: str) -> list[dict[str, Any]]:
    try:
        policies = await request(
            client,
            "GET",
            "knowledge_policies",
            params={
                "is_published": "eq.true",
                "select": "policy_id,judul,ringkasan,nomor_versi",
                "order": "prioritas.asc",
                "limit": "3",
            },
        )
        return [
            {
                "source_table": "knowledge_policies",
                "source_id": str(row["policy_id"]),
                "judul": row.get("judul"),
                "ringkasan": row.get("ringkasan"),
                "versi": row.get("nomor_versi"),
                "domain": domain_code,
            }
            for row in policies
        ]
    except Exception:
        return []
