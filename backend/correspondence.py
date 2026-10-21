from datetime import date, datetime, timezone
from typing import Any
from uuid import uuid4

import httpx
from fastapi import HTTPException
from pydantic import BaseModel, Field

from auth import InternalUser
from oas import _request, create_internal_notification, record_activity

CORRESPONDENCE_TYPES = {"masuk", "keluar"}
CORRESPONDENCE_STATUSES = {"draft", "diterima", "dicatat", "didisposisikan", "diproses", "dikirim", "selesai", "diarsipkan"}
DISPOSITION_STATUSES = {"belum", "sedang_diproses", "selesai", "dibatalkan"}


class CorrespondenceCreateInput(BaseModel):
    tipe: str
    nomor_surat: str | None = None
    jenis_surat: str | None = None
    sifat_surat: str = "biasa"
    perihal: str = Field(min_length=1, max_length=255)
    asal_tujuan: str = Field(min_length=1, max_length=255)
    tanggal_surat: date | None = None
    tanggal_terima: date | None = None
    tanggal_kirim: date | None = None
    ringkasan: str | None = None
    file_url: str | None = None
    storage_bucket: str | None = None
    storage_path: str | None = None
    file_name: str | None = None
    mime_type: str | None = None
    file_size: int | None = None
    status: str | None = None
    reference_table: str | None = None
    reference_id: str | None = None


class CorrespondenceUpdateInput(BaseModel):
    perihal: str | None = None
    jenis_surat: str | None = None
    sifat_surat: str | None = None
    asal_tujuan: str | None = None
    ringkasan: str | None = None
    status: str | None = None


class DispositionCreateInput(BaseModel):
    disposisi_ke: str
    instruksi: str = Field(min_length=1, max_length=2000)
    priority: str = "normal"
    due_date: date | None = None


class DispositionUpdateInput(BaseModel):
    status: str
    catatan: str | None = None
    completion_note: str | None = None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _ensure_personnel(personnel_id: str) -> None:
    async with httpx.AsyncClient(timeout=10) as client:
        rows = await _request(client, "GET", "staff", params={"personnel_id": f"eq.{personnel_id}", "select": "personnel_id"})
        if not rows:
            rows = await _request(client, "GET", "managers", params={"personnel_id": f"eq.{personnel_id}", "select": "personnel_id"})
        if not rows:
            rows = await _request(client, "GET", "admins", params={"personnel_id": f"eq.{personnel_id}", "select": "personnel_id"})
    if not rows:
        raise HTTPException(status_code=404, detail="Personnel penerima tidak ditemukan.")


async def _next_agenda(tipe: str) -> str:
    prefix = "SM" if tipe == "masuk" else "SK"
    year = datetime.now(timezone.utc).year
    async with httpx.AsyncClient(timeout=10) as client:
        rows = await _request(client, "GET", "correspondence", params={"nomor_agenda": f"like.{prefix}-{year}-%", "select": "nomor_agenda", "order": "created_at.desc", "limit": "1"})
    number = 1
    if rows:
        try:
            number = int(str(rows[0]["nomor_agenda"]).split("-")[-1]) + 1
        except (ValueError, IndexError):
            number = 1
    return f"{prefix}-{year}-{number:04d}"


async def list_correspondence(tipe: str | None = None, status: str | None = None, search: str | None = None) -> list[dict[str, Any]]:
    params: dict[str, str] = {"select": "*", "order": "created_at.desc", "limit": "200"}
    if tipe:
        params["tipe"] = f"eq.{tipe}"
    if status:
        params["status"] = f"eq.{status}"
    if search:
        params["or"] = f"(perihal.ilike.*{search}*,asal_tujuan.ilike.*{search}*,nomor_agenda.ilike.*{search}*)"
    async with httpx.AsyncClient(timeout=10) as client:
        return await _request(client, "GET", "correspondence", params=params)


async def get_correspondence(correspondence_id: str) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=10) as client:
        rows = await _request(client, "GET", "correspondence", params={"correspondence_id": f"eq.{correspondence_id}", "select": "*"})
        if not rows:
            raise HTTPException(status_code=404, detail="Surat tidak ditemukan.")
        dispositions = await _request(client, "GET", "correspondence_dispositions", params={"correspondence_id": f"eq.{correspondence_id}", "order": "created_at.desc"})
    return {**rows[0], "dispositions": dispositions}


async def create_correspondence(payload: CorrespondenceCreateInput, user: InternalUser) -> dict[str, Any]:
    if payload.tipe not in CORRESPONDENCE_TYPES:
        raise HTTPException(status_code=422, detail="Tipe surat tidak valid.")
    if payload.status and payload.status not in CORRESPONDENCE_STATUSES:
        raise HTTPException(status_code=422, detail="Status surat tidak valid.")
    agenda = await _next_agenda(payload.tipe)
    default_status = "draft" if payload.tipe == "keluar" else "dicatat"
    body = {
        "correspondence_id": str(uuid4()),
        "nomor_agenda": agenda,
        "nomor_surat": payload.nomor_surat,
        "tipe": payload.tipe,
        "jenis_surat": payload.jenis_surat,
        "sifat_surat": payload.sifat_surat,
        "perihal": payload.perihal.strip(),
        "asal_tujuan": payload.asal_tujuan.strip(),
        "tanggal_surat": str(payload.tanggal_surat) if payload.tanggal_surat else None,
        "tanggal_terima": str(payload.tanggal_terima) if payload.tanggal_terima else None,
        "tanggal_kirim": str(payload.tanggal_kirim) if payload.tanggal_kirim else None,
        "ringkasan": payload.ringkasan,
        "file_url": payload.file_url,
        "storage_bucket": payload.storage_bucket,
        "storage_path": payload.storage_path,
        "file_name": payload.file_name,
        "mime_type": payload.mime_type,
        "file_size": payload.file_size,
        "status": payload.status or default_status,
        "created_by": user.entity_id,
        "reference_table": payload.reference_table,
        "reference_id": payload.reference_id,
        "created_at": _now(),
        "updated_at": _now(),
    }
    async with httpx.AsyncClient(timeout=10) as client:
        rows = await _request(client, "POST", "correspondence", body=body, prefer="return=representation")
    result = rows[0] if rows else body
    await record_activity(user, action="create", resource_type="correspondence", resource_id=body["correspondence_id"], module="correspondence", status="success", description=f"Mencatat surat {payload.tipe}.", metadata={"nomor_agenda": agenda, "perihal": payload.perihal})
    await create_internal_notification("correspondence_created", title="Surat baru", message=f"{agenda} — {payload.perihal}", reference_table="correspondence", reference_id=body["correspondence_id"], target_roles=["manager", "admin"])
    return result


async def update_correspondence(correspondence_id: str, payload: CorrespondenceUpdateInput, user: InternalUser) -> dict[str, Any]:
    if payload.status and payload.status not in CORRESPONDENCE_STATUSES:
        raise HTTPException(status_code=422, detail="Status surat tidak valid.")
    current = await get_correspondence(correspondence_id)
    changes = {key: value for key, value in payload.model_dump().items() if value is not None}
    if not changes:
        return current
    changes["updated_by"] = user.entity_id
    changes["updated_at"] = _now()
    async with httpx.AsyncClient(timeout=10) as client:
        rows = await _request(client, "PATCH", "correspondence", params={"correspondence_id": f"eq.{correspondence_id}"}, body=changes, prefer="return=representation")
    await record_activity(user, action="update", resource_type="correspondence", resource_id=correspondence_id, module="correspondence", status="success", description="Mengubah data surat.", metadata={"from_status": current.get("status"), "to_status": payload.status})
    return rows[0] if rows else await get_correspondence(correspondence_id)


async def archive_correspondence(correspondence_id: str, user: InternalUser) -> dict[str, Any]:
    await get_correspondence(correspondence_id)
    async with httpx.AsyncClient(timeout=10) as client:
        rows = await _request(client, "PATCH", "correspondence", params={"correspondence_id": f"eq.{correspondence_id}"}, body={"status": "diarsipkan", "archived_at": _now(), "updated_by": user.entity_id, "updated_at": _now()}, prefer="return=representation")
    await record_activity(user, action="archive", resource_type="correspondence", resource_id=correspondence_id, module="correspondence", status="success", description="Mengarsipkan surat.")
    return rows[0] if rows else await get_correspondence(correspondence_id)


async def list_dispositions(correspondence_id: str, user: InternalUser) -> list[dict[str, Any]]:
    await get_correspondence(correspondence_id)
    async with httpx.AsyncClient(timeout=10) as client:
        return await _request(client, "GET", "correspondence_dispositions", params={"correspondence_id": f"eq.{correspondence_id}", "order": "created_at.desc"})


async def create_disposition(correspondence_id: str, payload: DispositionCreateInput, user: InternalUser) -> dict[str, Any]:
    if user.role not in {"manager", "admin"}:
        raise HTTPException(status_code=403, detail="Hanya manager atau admin yang dapat membuat disposisi.")
    await get_correspondence(correspondence_id)
    await _ensure_personnel(payload.disposisi_ke)
    disposition_id = str(uuid4())
    body = {"disposition_id": disposition_id, "correspondence_id": correspondence_id, "disposisi_ke": payload.disposisi_ke, "instruksi": payload.instruksi.strip(), "status": "belum", "catatan": None, "created_by": user.entity_id, "priority": payload.priority, "due_date": str(payload.due_date) if payload.due_date else None, "created_at": _now(), "updated_at": _now()}
    async with httpx.AsyncClient(timeout=10) as client:
        rows = await _request(client, "POST", "correspondence_dispositions", body=body, prefer="return=representation")
        await _request(client, "PATCH", "correspondence", params={"correspondence_id": f"eq.{correspondence_id}"}, body={"status": "didisposisikan", "updated_at": _now()}, prefer="return=minimal")
    await record_activity(user, action="create", resource_type="correspondence_disposition", resource_id=disposition_id, module="correspondence", status="success", description="Membuat disposisi surat.", metadata={"correspondence_id": correspondence_id, "disposisi_ke": payload.disposisi_ke})
    await create_internal_notification("correspondence_disposition_created", title="Disposisi baru", message=payload.instruksi, reference_table="correspondence_dispositions", reference_id=disposition_id, target_roles=["manager", "admin"])
    return rows[0] if rows else body


async def update_disposition(disposition_id: str, payload: DispositionUpdateInput, user: InternalUser) -> dict[str, Any]:
    if payload.status not in DISPOSITION_STATUSES:
        raise HTTPException(status_code=422, detail="Status disposisi tidak valid.")
    async with httpx.AsyncClient(timeout=10) as client:
        rows = await _request(client, "GET", "correspondence_dispositions", params={"disposition_id": f"eq.{disposition_id}", "select": "*"})
        if not rows:
            raise HTTPException(status_code=404, detail="Disposisi tidak ditemukan.")
        current = rows[0]
        if user.role not in {"manager", "admin"} and str(current.get("disposisi_ke")) != user.entity_id:
            raise HTTPException(status_code=403, detail="Disposisi bukan milik Anda.")
        if payload.status == "selesai" and not (payload.completion_note or payload.catatan or "").strip():
            raise HTTPException(status_code=422, detail="Catatan penyelesaian wajib diisi.")
        body = {"status": payload.status, "catatan": payload.catatan or payload.completion_note, "completion_note": payload.completion_note, "updated_by": user.entity_id, "updated_at": _now()}
        updated = await _request(client, "PATCH", "correspondence_dispositions", params={"disposition_id": f"eq.{disposition_id}"}, body=body, prefer="return=representation")
    await record_activity(user, action="status_change", resource_type="correspondence_disposition", resource_id=disposition_id, module="correspondence", status="success", description="Mengubah status disposisi.", metadata={"from_status": current.get("status"), "to_status": payload.status})
    if payload.status == "selesai":
        await create_internal_notification("correspondence_disposition_completed", title="Disposisi selesai", message=payload.completion_note or payload.catatan or "Disposisi telah diselesaikan.", severity="success", reference_table="correspondence_dispositions", reference_id=disposition_id, target_roles=["manager", "admin"])
    return updated[0] if updated else {**current, **body}
