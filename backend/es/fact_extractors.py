from collections import defaultdict
from datetime import date, timedelta
from typing import Any

import httpx
from fastapi import HTTPException

from .database import request


def _num(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _infer_strap_from_text(name: str, category: str, tags: list[str]) -> str:
    joined = " ".join([name, category, *tags]).lower()
    if any(word in joined for word in ("kulit", "leather", "calf")):
        return "leather"
    if any(word in joined for word in ("rubber", "silicone", "resin", "karet", "sport")):
        return "rubber"
    if any(word in joined for word in ("nylon", "canvas", "nato")):
        return "nylon"
    return "stainless_steel"


async def extract_pos_crosssell_facts(
    client: httpx.AsyncClient, product_id: str | None
) -> tuple[dict[str, Any], dict[str, Any]]:
    if not product_id:
        raise HTTPException(status_code=422, detail="Pilih produk jam tangan utama terlebih dahulu.")
    rows = await request(
        client,
        "GET",
        "products",
        params={
            "product_id": f"eq.{product_id}",
            "select": "product_id,nama_barang,kategori,brand,harga,stok,tags,specs",
        },
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Produk utama tidak ditemukan.")
    product = rows[0]
    specs = product.get("specs") if isinstance(product.get("specs"), dict) else {}
    tags = [str(item) for item in (product.get("tags") or [])]
    lug_width = int(_num(specs.get("lug_width_mm"), 20))
    strap_material = str(
        specs.get("strap_material")
        or _infer_strap_from_text(str(product.get("nama_barang") or ""), str(product.get("kategori") or ""), tags)
    )
    facts = {
        "P_MAIN_CATEGORY": str(product.get("kategori") or "Jam Tangan Pria"),
        "P_MAIN_PRICE": _num(product.get("harga"), 0.0),
        "P_LUG_WIDTH": lug_width,
        "P_STRAP_MATERIAL": strap_material,
    }
    return facts, {"main_product": product}


async def extract_warehouse_qc_facts(
    client: httpx.AsyncClient, purchase_id: str | None
) -> tuple[dict[str, Any], dict[str, Any]]:
    if not purchase_id:
        raise HTTPException(status_code=422, detail="Pilih Purchase Order (PO) terlebih dahulu.")
    purchases = await request(
        client,
        "GET",
        "supplier_purchases",
        params={"purchase_id": f"eq.{purchase_id}", "select": "*"},
    )
    if not purchases:
        raise HTTPException(status_code=404, detail="Purchase Order (PO) tidak ditemukan.")
    po = purchases[0]
    items = await request(
        client,
        "GET",
        "supplier_purchase_items",
        params={"purchase_id": f"eq.{purchase_id}", "select": "*"},
    )
    total_ordered = sum(_num(item.get("qty_pesan")) for item in items)
    total_received = sum(_num(item.get("qty_terima")) for item in items)
    total_defect = sum(_num(item.get("qty_rusak")) for item in items)

    base_received = total_received if total_received > 0 else max(1.0, total_ordered)
    defect_pct = round((total_defect / base_received) * 100.0, 2)
    shortage_pct = (
        round((max(0.0, total_ordered - total_received) / total_ordered) * 100.0, 2)
        if total_ordered > 0
        else 0.0
    )

    delay_days = 0
    est_str = str(po.get("tanggal_estimasi_terima") or "")[:10]
    rec_str = str(po.get("tanggal_terima") or date.today().isoformat())[:10]
    if est_str:
        try:
            delay_days = max(0, (date.fromisoformat(rec_str) - date.fromisoformat(est_str)).days)
        except ValueError:
            delay_days = 0

    first_product_id = str(items[0]["product_id"]) if items else None
    facts = {
        "W_PO_DEFECT_PCT": defect_pct,
        "W_PO_SHORTAGE_PCT": shortage_pct,
        "W_PO_DELAY_DAYS": delay_days,
        "W_PO_DEFECT_QTY": int(total_defect if total_defect > 0 else 1),
    }
    meta = {
        "purchase": po,
        "items": items,
        "first_product_id": first_product_id,
    }
    return facts, meta


async def extract_warehouse_stock_anomaly_facts(
    client: httpx.AsyncClient, product_id: str | None
) -> tuple[dict[str, Any], dict[str, Any]]:
    if not product_id:
        raise HTTPException(status_code=422, detail="Pilih produk yang mengalami anomali stok terlebih dahulu.")
    rows = await request(
        client,
        "GET",
        "products",
        params={
            "product_id": f"eq.{product_id}",
            "select": "product_id,nama_barang,kategori,brand,harga,stok,minimum_stok,reorder_point",
        },
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Produk tidak ditemukan.")
    product = rows[0]
    costs = await request(
        client,
        "GET",
        "mis_product_costs",
        params={
            "product_id": f"eq.{product_id}",
            "select": "harga_beli,berlaku_dari",
            "order": "berlaku_dari.desc",
            "limit": "1",
        },
    )
    unit_cost = _num(costs[0].get("harga_beli"), _num(product.get("harga")) * 0.6) if costs else _num(product.get("harga")) * 0.6

    start_30d = (date.today() - timedelta(days=30)).isoformat()
    movements = await request(
        client,
        "GET",
        "mis_stock_movements",
        params={
            "product_id": f"eq.{product_id}",
            "created_at": f"gte.{start_30d}",
            "select": "movement_id",
        },
    )
    facts = {
        "W_SYS_STOCK": int(product.get("stok") or 0),
        "W_ROP": int(product.get("reorder_point") or 0),
        "W_UNIT_COST": round(unit_cost, 2),
        "W_MOVEMENT_30D": len(movements),
    }
    return facts, {"product": product}


async def extract_manager_kpi_facts(
    client: httpx.AsyncClient,
) -> tuple[dict[str, Any], dict[str, Any]]:
    start_30d = (date.today() - timedelta(days=30)).isoformat()
    sales = await request(
        client,
        "GET",
        "mis_daily_sales_summary",
        params={
            "summary_date": f"gte.{start_30d}",
            "select": "total_pendapatan,gross_profit",
        },
    )
    total_rev = sum(_num(row.get("total_pendapatan")) for row in sales)
    total_gp = sum(_num(row.get("gross_profit")) for row in sales)
    margin_pct = round((total_gp / total_rev) * 100.0, 2) if total_rev > 0 else 30.0

    products = await request(client, "GET", "products", params={"select": "product_id,stok"})
    total_sku = len(products)
    stockout_sku = sum(1 for item in products if int(item.get("stok") or 0) <= 0)
    stockout_pct = round((stockout_sku / total_sku) * 100.0, 2) if total_sku > 0 else 0.0

    costs = await request(
        client,
        "GET",
        "mis_product_costs",
        params={"select": "product_id,harga_beli,berlaku_dari", "order": "berlaku_dari.asc"},
    )
    history_by_prod: dict[str, list[float]] = defaultdict(list)
    for row in costs:
        history_by_prod[str(row.get("product_id"))].append(_num(row.get("harga_beli")))
    cost_hike_count = sum(1 for prices in history_by_prod.values() if len(prices) >= 2 and prices[-1] > prices[-2])

    restock_urgent = 0
    promo_aggressive = 0
    promo_blocked = 0
    try:
        scenarios = await request(client, "GET", "iss_dss_scenarios", params={"select": "scenario_id,kode"})
        by_code = {str(row["kode"]): str(row["scenario_id"]) for row in scenarios}
        if "RESTOCK" in by_code:
            runs = await request(
                client,
                "GET",
                "iss_dss_runs",
                params={"scenario_id": f"eq.{by_code['RESTOCK']}", "order": "created_at.desc", "limit": "1", "select": "run_id"},
            )
            if runs:
                results = await request(
                    client,
                    "GET",
                    "iss_dss_results",
                    params={"run_id": f"eq.{runs[0]['run_id']}", "select": "status"},
                )
                restock_urgent = sum(1 for item in results if str(item.get("status")) == "Restock Segera")
        if "PROMO" in by_code:
            runs = await request(
                client,
                "GET",
                "iss_dss_runs",
                params={"scenario_id": f"eq.{by_code['PROMO']}", "order": "created_at.desc", "limit": "1", "select": "run_id"},
            )
            if runs:
                results = await request(
                    client,
                    "GET",
                    "iss_dss_results",
                    params={"run_id": f"eq.{runs[0]['run_id']}", "select": "status,recommendation"},
                )
                for item in results:
                    st = str(item.get("status") or "")
                    rec = item.get("recommendation") if isinstance(item.get("recommendation"), dict) else {}
                    if st == "Promo Agresif":
                        promo_aggressive += 1
                    if st in {"Promo Agresif", "Promo Ringan"} and _num(rec.get("diskon_pct"), 0.0) <= 0:
                        promo_blocked += 1
    except Exception:
        pass

    pending_wf = await request(
        client,
        "GET",
        "workflow_requests",
        params={"current_status": "eq.pending", "select": "request_id"},
    )

    facts = {
        "M_KPI_MARGIN_PCT": margin_pct,
        "M_KPI_STOCKOUT_PCT": stockout_pct,
        "M_COST_HIKE_SKU_COUNT": cost_hike_count,
        "M_DSS_RESTOCK_URGENT_COUNT": restock_urgent,
        "M_DSS_PROMO_AGGRESSIVE_COUNT": promo_aggressive,
        "M_DSS_PROMO_BLOCKED_COUNT": promo_blocked,
        "M_PENDING_WORKFLOW_COUNT": len(pending_wf),
    }
    return facts, {"total_sku": total_sku, "stockout_sku": stockout_sku}


async def extract_manager_workflow_facts(
    client: httpx.AsyncClient, request_id: str | None
) -> tuple[dict[str, Any], dict[str, Any]]:
    if not request_id:
        raise HTTPException(status_code=422, detail="Pilih pengajuan Workflow terlebih dahulu.")
    rows = await request(
        client,
        "GET",
        "workflow_requests",
        params={"request_id": f"eq.{request_id}", "select": "*"},
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Workflow request tidak ditemukan.")
    wf = rows[0]
    meta = wf.get("metadata") if isinstance(wf.get("metadata"), dict) else {}
    product_id = meta.get("product_id") or (wf.get("reference_id") if wf.get("reference_table") == "products" else None)
    qty_abs = abs(int(_num(meta.get("qty_change"), 1)))
    resulting_stock = int(_num(meta.get("stok_diharapkan"), 0))
    has_attachment = "ya" if meta.get("attachment_document_id") else "tidak"

    unit_cost = 500_000.0
    if product_id:
        costs = await request(
            client,
            "GET",
            "mis_product_costs",
            params={
                "product_id": f"eq.{product_id}",
                "select": "harga_beli",
                "order": "berlaku_dari.desc",
                "limit": "1",
            },
        )
        if costs:
            unit_cost = _num(costs[0].get("harga_beli"), 500_000.0)
        else:
            prods = await request(
                client,
                "GET",
                "products",
                params={"product_id": f"eq.{product_id}", "select": "harga"},
            )
            if prods:
                unit_cost = _num(prods[0].get("harga"), 800_000.0) * 0.6

    facts = {
        "MW_REQ_TYPE": str(wf.get("tipe_request") or "stock_adjustment"),
        "MW_QTY_ABS": qty_abs,
        "MW_FINANCIAL_VALUE": round(qty_abs * unit_cost, 2),
        "MW_HAS_ATTACHMENT": has_attachment,
        "MW_RESULTING_STOCK": resulting_stock,
    }
    return facts, {"workflow": wf}


async def extract_db_facts(
    client: httpx.AsyncClient, domain_code: str, reference_id: str | None = None
) -> tuple[dict[str, Any], dict[str, Any]]:
    code = domain_code.upper()
    if code == "CUST_WATCH_ADVISOR":
        return {}, {}
    if code == "STAFF_POS_CROSSSELL":
        return await extract_pos_crosssell_facts(client, reference_id)
    if code == "WAREHOUSE_QC_INBOUND":
        return await extract_warehouse_qc_facts(client, reference_id)
    if code == "WAREHOUSE_STOCK_ANOMALY":
        return await extract_warehouse_stock_anomaly_facts(client, reference_id)
    if code == "MGR_KPI_DIAGNOSTIC":
        return await extract_manager_kpi_facts(client)
    if code == "MGR_WORKFLOW_APPROVAL":
        return await extract_manager_workflow_facts(client, reference_id)
    return {}, {}
