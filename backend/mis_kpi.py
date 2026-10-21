from datetime import date, datetime, timezone
from typing import Any
from uuid import uuid4

import httpx
from fastapi import HTTPException, status
from pydantic import BaseModel, Field

from auth import InternalUser
from oas import _request


class KpiTargetCreate(BaseModel):
    kpi_id: str
    personnel_id: str | None = None
    periode_tipe: str = "monthly"
    periode_mulai: date
    periode_selesai: date
    nilai_target: float = Field(ge=0)
    nilai_peringatan: float | None = Field(default=None, ge=0)
    catatan: str | None = None


class KpiTargetUpdate(BaseModel):
    nilai_target: float | None = Field(default=None, ge=0)
    nilai_peringatan: float | None = Field(default=None, ge=0)
    catatan: str | None = None


def _validate_period(start: date, end: date) -> None:
    if start > end:
        raise HTTPException(status_code=422, detail="Periode mulai tidak boleh melebihi periode selesai.")


async def list_kpis(client: httpx.AsyncClient, active_only: bool = True) -> list[dict[str, Any]]:
    params = {"select": "*", "order": "nama_kpi.asc"}
    if active_only:
        params["is_active"] = "eq.true"
    return await _request(client, "GET", "mis_kpi_definitions", params=params)


async def list_targets(client: httpx.AsyncClient, params: dict[str, str]) -> list[dict[str, Any]]:
    targets = await _request(client, "GET", "mis_kpi_targets", params={"select": "*", **params})
    if not targets:
        return []
    kpi_ids = {str(target.get("kpi_id")) for target in targets if target.get("kpi_id")}
    definitions = await _request(client, "GET", "mis_kpi_definitions", params={"select": "kpi_id,kode_kpi,nama_kpi,satuan,arah_baik", "kpi_id": f"in.({','.join(kpi_ids)})"}) if kpi_ids else []
    definition_map = {str(item.get("kpi_id")): item for item in definitions}
    return [{**target, "mis_kpi_definitions": definition_map.get(str(target.get("kpi_id")))} for target in targets]


async def create_target(client: httpx.AsyncClient, payload: KpiTargetCreate, user: InternalUser) -> dict[str, Any]:
    _validate_period(payload.periode_mulai, payload.periode_selesai)
    if payload.nilai_peringatan is not None and payload.nilai_peringatan > payload.nilai_target:
        raise HTTPException(status_code=422, detail="Nilai peringatan tidak boleh melebihi target.")
    kpis = await _request(client, "GET", "mis_kpi_definitions", params={"kpi_id": f"eq.{payload.kpi_id}", "select": "kpi_id"})
    if not kpis:
        raise HTTPException(status_code=404, detail="Definisi KPI tidak ditemukan.")
    now = datetime.now(timezone.utc).isoformat()
    rows = await _request(
        client,
        "POST",
        "mis_kpi_targets",
        body={
            "target_id": str(uuid4()),
            "kpi_id": payload.kpi_id,
            "personnel_id": payload.personnel_id,
            "periode_tipe": payload.periode_tipe,
            "periode_mulai": payload.periode_mulai.isoformat(),
            "periode_selesai": payload.periode_selesai.isoformat(),
            "nilai_target": payload.nilai_target,
            "nilai_peringatan": payload.nilai_peringatan,
            "catatan": payload.catatan,
            "created_by": user.entity_id,
            "created_at": now,
            "updated_at": now,
        },
        prefer="return=representation",
    )
    return rows[0]


async def update_target(client: httpx.AsyncClient, target_id: str, payload: KpiTargetUpdate) -> dict[str, Any]:
    existing = await _request(client, "GET", "mis_kpi_targets", params={"target_id": f"eq.{target_id}", "select": "*"})
    if not existing:
        raise HTTPException(status_code=404, detail="Target KPI tidak ditemukan.")
    body = payload.model_dump(exclude_none=True)
    body["updated_at"] = datetime.now(timezone.utc).isoformat()
    target_value = payload.nilai_target if payload.nilai_target is not None else existing[0].get("nilai_target", 0)
    warning_value = payload.nilai_peringatan if payload.nilai_peringatan is not None else existing[0].get("nilai_peringatan")
    if warning_value is not None and warning_value > target_value:
        raise HTTPException(status_code=422, detail="Nilai peringatan tidak boleh melebihi target.")
    rows = await _request(client, "PATCH", "mis_kpi_targets", params={"target_id": f"eq.{target_id}"}, body=body, prefer="return=representation")
    return rows[0] if rows else {**existing[0], **body}


async def get_performance(client: httpx.AsyncClient, date_from: date, date_to: date, personnel_id: str | None = None) -> dict[str, Any]:
    _validate_period(date_from, date_to)
    daily = await _request(client, "GET", "mis_daily_sales_summary", params={"select": "*", "summary_date": f"gte.{date_from}", "and": f"(summary_date.lte.{date_to})"})
    products = await _request(client, "GET", "products", params={"select": "product_id,stok,minimum_stok", "limit": "10000"})
    kpis = await list_kpis(client)
    target_params = {"periode_mulai": f"lte.{date_to}", "periode_selesai": f"gte.{date_from}"}
    if personnel_id:
        target_params["or"] = f"(personnel_id.is.null,personnel_id.eq.{personnel_id})"
    targets = await list_targets(client, target_params)
    revenue = sum(float(row.get("total_pendapatan") or row.get("gross_sales") or 0) for row in daily)
    profit = sum(float(row.get("gross_profit") or 0) for row in daily)
    transactions = sum(int(row.get("jumlah_transaksi") or 0) for row in daily)
    stockout = sum(1 for row in products if int(row.get("stok") or 0) <= 0)
    actuals = {
        "KPI_TOTAL_SALES": revenue,
        "KPI_GROSS_PROFIT": profit,
        "KPI_TRANSACTION_COUNT": transactions,
        "KPI_GROSS_MARGIN": profit / revenue * 100 if revenue else 0,
        "KPI_STOCKOUT_RATE": stockout / len(products) * 100 if products else 0,
    }
    target_map = {row.get("kpi_id"): row for row in targets}
    items = []
    for kpi in kpis:
        target = target_map.get(kpi.get("kpi_id"))
        target_value = float(target["nilai_target"]) if target else None
        warning = float(target["nilai_peringatan"]) if target and target.get("nilai_peringatan") is not None else None
        actual = actuals.get(kpi.get("kode_kpi"), 0)
        direction = kpi.get("arah_baik", "higher")
        if target_value is None:
            state = "no_target"
            achievement = None
            variance = None
        elif direction == "lower":
            achievement = target_value / actual * 100 if actual else 100
            variance = target_value - actual
            state = "achieved" if actual <= target_value else ("warning" if warning is not None and actual <= warning else "failed")
        else:
            achievement = actual / target_value * 100 if target_value else 100
            variance = actual - target_value
            state = "achieved" if actual >= target_value else ("warning" if warning is not None and actual >= warning else "failed")
        items.append({"kpi_id": kpi.get("kpi_id"), "kode_kpi": kpi.get("kode_kpi"), "nama_kpi": kpi.get("nama_kpi"), "satuan": kpi.get("satuan"), "arah_baik": direction, "actual": actual, "target": target_value, "warning_threshold": warning, "achievement_percentage": achievement, "variance": variance, "status": state})
    return {"period": {"date_from": date_from.isoformat(), "date_to": date_to.isoformat()}, "items": items}
