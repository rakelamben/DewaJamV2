from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import httpx
from fastapi import HTTPException
from pydantic import BaseModel, Field

from auth import InternalUser
from oas import _request, create_internal_notification, record_activity

APPROVAL_TYPES = {"adjustment", "damaged", "return_in", "return_out"}
MOVEMENT_DELTAS = {
    "damaged": lambda qty: -abs(qty),
    "return_in": lambda qty: abs(qty),
    "return_out": lambda qty: -abs(qty),
}


class WorkflowCreateInput(BaseModel):
    product_id: str
    tipe_mutasi: str
    qty_change: int
    alasan: str = Field(min_length=1, max_length=500)
    transaction_id: str | None = None
    attachment_document_id: str | None = None


class WorkflowDecisionInput(BaseModel):
    catatan: str | None = Field(default=None, max_length=1000)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _delta(movement_type: str, qty: int) -> int:
    if qty == 0:
        raise HTTPException(status_code=422, detail="Perubahan stok tidak boleh nol.")
    if movement_type == "adjustment":
        return qty
    return MOVEMENT_DELTAS[movement_type](qty)


async def _history(
    request_id: str,
    from_status: str | None,
    to_status: str,
    changed_by: str | None,
    reason: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await _request(client, "POST", "workflow_status_history", body={
                "history_id": str(uuid4()),
                "request_id": request_id,
                "from_status": from_status,
                "to_status": to_status,
                "changed_by": changed_by,
                "reason": reason,
                "metadata": metadata or {},
                "created_at": _now(),
            }, prefer="return=minimal")
    except Exception:
        # History is important but must not turn a successfully completed
        # business operation into a false failure.
        await record_activity(None, action="history_failed", resource_type="workflow_request", resource_id=request_id, module="workflow", status="failed", description="Gagal mencatat riwayat status workflow.")


async def create_workflow(payload: WorkflowCreateInput, user: InternalUser) -> dict[str, Any]:
    if payload.tipe_mutasi not in APPROVAL_TYPES:
        raise HTTPException(status_code=422, detail="Tipe mutasi ini tidak membutuhkan workflow approval.")
    delta = _delta(payload.tipe_mutasi, payload.qty_change)
    async with httpx.AsyncClient(timeout=15) as client:
        products = await _request(client, "GET", "products", params={"product_id": f"eq.{payload.product_id}", "select": "product_id,nama_barang,stok"})
        if not products:
            raise HTTPException(status_code=404, detail="Produk tidak ditemukan.")
        product = products[0]
        old_stock = int(product["stok"])
        expected_stock = old_stock + delta
        if expected_stock < 0:
            raise HTTPException(status_code=409, detail="Stok hasil request tidak boleh negatif.")
        request_id = str(uuid4())
        request_body = {
            "request_id": request_id,
            "tipe_request": f"stock_{payload.tipe_mutasi}",
            "reference_table": "products",
            "reference_id": payload.product_id,
            "deskripsi": payload.alasan.strip(),
            "requested_by": user.entity_id,
            "current_status": "pending",
            "title": f"{payload.tipe_mutasi} - {product['nama_barang']}",
            "priority": "normal",
            "requested_at": _now(),
            "metadata": {
                "product_id": payload.product_id,
                "product_name": product["nama_barang"],
                "tipe_mutasi": payload.tipe_mutasi,
                "qty_change": delta,
                "stok_sebelum": old_stock,
                "stok_diharapkan": expected_stock,
                "transaction_id": payload.transaction_id,
                "attachment_document_id": payload.attachment_document_id,
            },
            "created_at": _now(),
            "updated_at": _now(),
        }
        rows = await _request(client, "POST", "workflow_requests", body=request_body, prefer="return=representation")
        await _request(client, "POST", "workflow_approvals", body={
            "approval_id": str(uuid4()),
            "request_id": request_id,
            "approver_id": None,
            "status": "pending",
            "catatan": None,
            "created_at": _now(),
        }, prefer="return=minimal")
    await _history(request_id, None, "pending", user.entity_id, payload.alasan)
    await record_activity(user, action="create", resource_type="workflow_request", resource_id=request_id, module="workflow", status="success", description="Membuat request approval mutasi stok.", metadata=request_body["metadata"])
    await create_internal_notification("workflow_created", title="Approval stok baru", message=f"Request {payload.tipe_mutasi} untuk {product['nama_barang']} menunggu persetujuan.", reference_table="workflow_requests", reference_id=request_id, target_roles=["manager", "admin"])
    return rows[0] if rows else request_body


async def list_workflows(user: InternalUser, status: str | None = None) -> list[dict[str, Any]]:
    params: dict[str, str] = {"select": "*", "order": "created_at.desc", "limit": "200"}
    if status:
        params["current_status"] = f"eq.{status}"
    if user.role not in {"manager", "admin"}:
        params["requested_by"] = f"eq.{user.entity_id}"
    async with httpx.AsyncClient(timeout=10) as client:
        rows = await _request(client, "GET", "workflow_requests", params=params)
        approvals = await _request(client, "GET", "workflow_approvals", params={"request_id": f"in.({','.join(str(row['request_id']) for row in rows)})", "select": "*"}) if rows else []
    by_request = {str(row["request_id"]): row for row in approvals}
    return [{**row, "approval": by_request.get(str(row["request_id"]))} for row in rows]


async def get_workflow(request_id: str, user: InternalUser) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=10) as client:
        rows = await _request(client, "GET", "workflow_requests", params={"request_id": f"eq.{request_id}", "select": "*"})
        if not rows:
            raise HTTPException(status_code=404, detail="Workflow tidak ditemukan.")
        request = rows[0]
        if user.role not in {"manager", "admin"} and str(request.get("requested_by")) != user.entity_id:
            raise HTTPException(status_code=403, detail="Workflow bukan milik Anda.")
        approvals = await _request(client, "GET", "workflow_approvals", params={"request_id": f"eq.{request_id}", "select": "*"})
        history = await _request(client, "GET", "workflow_status_history", params={"request_id": f"eq.{request_id}", "order": "created_at.asc"})
    return {**request, "approval": approvals[0] if approvals else None, "history": history}


async def decide_workflow(request_id: str, decision: str, payload: WorkflowDecisionInput, user: InternalUser) -> dict[str, Any]:
    if user.role not in {"manager", "admin"}:
        raise HTTPException(status_code=403, detail="Hanya manager atau admin yang dapat memproses approval.")
    async with httpx.AsyncClient(timeout=20) as client:
        requests = await _request(client, "GET", "workflow_requests", params={"request_id": f"eq.{request_id}", "select": "*"})
        if not requests:
            raise HTTPException(status_code=404, detail="Workflow tidak ditemukan.")
        request = requests[0]
        if request.get("current_status") != "pending":
            raise HTTPException(status_code=409, detail="Workflow sudah tidak menunggu approval.")
        if str(request.get("requested_by")) == user.entity_id:
            raise HTTPException(status_code=403, detail="Pengaju tidak dapat menyetujui request sendiri.")
        if decision == "reject" and not (payload.catatan or "").strip():
            raise HTTPException(status_code=422, detail="Alasan penolakan wajib diisi.")
        approval_status = "approved" if decision == "approve" else "rejected"
        updated = await _request(client, "PATCH", "workflow_approvals", params={"request_id": f"eq.{request_id}", "status": "eq.pending"}, body={"approver_id": user.entity_id, "status": approval_status, "catatan": payload.catatan, "approved_at": _now(), "decided_at": _now(), "decision": decision}, prefer="return=representation")
        if not updated:
            raise HTTPException(status_code=409, detail="Approval sudah diproses oleh user lain.")
        next_status = "rejected" if decision == "reject" else "approved"
        request_updated = await _request(client, "PATCH", "workflow_requests", params={"request_id": f"eq.{request_id}", "current_status": "eq.pending"}, body={"current_status": next_status, "approved_at": _now() if decision == "approve" else None, "rejected_at": _now() if decision == "reject" else None, "updated_at": _now()}, prefer="return=representation")
        if not request_updated:
            raise HTTPException(status_code=409, detail="Status workflow berubah saat approval diproses.")
    await _history(request_id, "pending", "rejected" if decision == "reject" else "approved", user.entity_id, payload.catatan)
    await record_activity(user, action=decision, resource_type="workflow_request", resource_id=request_id, module="workflow", status="success", description=f"Workflow {decision}.", metadata={"catatan": payload.catatan})
    target = str(request.get("requested_by"))
    await create_internal_notification("workflow_rejected" if decision == "reject" else "workflow_approved", title=f"Workflow {decision}", message=payload.catatan or f"Workflow {decision} oleh {user.name}.", reference_table="workflow_requests", reference_id=request_id, target_roles=["staf_gudang", "gudang", "staf_operasional", "kasir"])
    if decision == "reject":
        return await get_workflow(request_id, user)
    return await execute_workflow(request, user)


async def execute_workflow(request: dict[str, Any], user: InternalUser) -> dict[str, Any]:
    metadata = request.get("metadata") or {}
    product_id = str(metadata.get("product_id") or request.get("reference_id"))
    delta = int(metadata.get("qty_change", 0))
    request_id = str(request["request_id"])
    async with httpx.AsyncClient(timeout=20) as client:
        products = await _request(client, "GET", "products", params={"product_id": f"eq.{product_id}", "select": "product_id,stok"})
        if not products:
            raise HTTPException(status_code=404, detail="Produk workflow tidak ditemukan.")
        old_stock = int(products[0]["stok"])
        expected_snapshot = int(metadata.get("stok_sebelum", old_stock))
        if old_stock != expected_snapshot:
            await _request(client, "PATCH", "workflow_requests", params={"request_id": f"eq.{request_id}"}, body={"current_status": "failed", "execution_error": "Stok berubah sejak request dibuat.", "updated_at": _now()}, prefer="return=minimal")
            await _history(request_id, "approved", "failed", user.entity_id, "Stok berubah sejak request dibuat.")
            await create_internal_notification("workflow_stock_conflict", title="Konflik stok", message="Workflow tidak dapat dieksekusi karena stok berubah.", severity="critical", reference_table="workflow_requests", reference_id=request_id, target_roles=["manager", "admin"])
            raise HTTPException(status_code=409, detail="Stok berubah sejak request dibuat. Workflow gagal dieksekusi.")
        new_stock = old_stock + delta
        if new_stock < 0:
            raise HTTPException(status_code=409, detail="Stok akhir tidak boleh negatif.")
        changed = await _request(client, "PATCH", "products", params={"product_id": f"eq.{product_id}", "stok": f"eq.{old_stock}"}, body={"stok": new_stock}, prefer="return=representation")
        if not changed:
            raise HTTPException(status_code=409, detail="Stok berubah oleh proses lain.")
        movement_id = str(uuid4())
        try:
            movement = await _request(client, "POST", "mis_stock_movements", body={"movement_id": movement_id, "product_id": product_id, "tipe_mutasi": metadata.get("tipe_mutasi"), "qty_change": delta, "stok_sebelum": old_stock, "stok_sesudah": new_stock, "transaction_id": metadata.get("transaction_id"), "alasan": request.get("deskripsi"), "created_by": user.entity_id, "workflow_request_id": request_id}, prefer="return=representation")
            result = movement[0] if movement else {"movement_id": movement_id}
            await _request(client, "PATCH", "workflow_requests", params={"request_id": f"eq.{request_id}", "current_status": "eq.approved"}, body={"current_status": "executed", "executed_by": user.entity_id, "executed_at": _now(), "updated_at": _now()}, prefer="return=minimal")
        except Exception:
            await _request(client, "PATCH", "products", params={"product_id": f"eq.{product_id}", "stok": f"eq.{new_stock}"}, body={"stok": old_stock}, prefer="return=minimal")
            await _request(client, "PATCH", "workflow_requests", params={"request_id": f"eq.{request_id}"}, body={"current_status": "failed", "execution_error": "Gagal membuat stock movement.", "updated_at": _now()}, prefer="return=minimal")
            await _history(request_id, "approved", "failed", user.entity_id, "Gagal membuat stock movement.")
            raise
    await _history(request_id, "approved", "executed", user.entity_id, "Stock movement berhasil dibuat.", {"movement_id": result.get("movement_id")})
    await record_activity(user, action="execute", resource_type="stock_movement", resource_id=str(result.get("movement_id")), module="workflow", status="success", description="Workflow berhasil dieksekusi menjadi stock movement.", metadata={"workflow_request_id": request_id, "stok_sebelum": old_stock, "stok_sesudah": new_stock})
    await create_internal_notification("workflow_executed", title="Workflow selesai dieksekusi", message="Approval berhasil diterapkan ke stok.", severity="success", reference_table="workflow_requests", reference_id=request_id, target_roles=["manager", "admin"])
    return await get_workflow(request_id, user)
