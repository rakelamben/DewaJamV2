import re
from datetime import datetime, timezone
from pathlib import PurePosixPath
from typing import Any
from uuid import uuid4

import httpx
from fastapi import HTTPException
from pydantic import BaseModel, Field

from auth import InternalUser
from config import SUPABASE_SECRET_KEY, SUPABASE_URL, SUPABASE_DB_SCHEMA
from oas import create_internal_notification, record_activity, _request

DOCUMENT_BUCKET = "internal-documents"
ALLOWED_DOCUMENT_TYPES = {"pdf", "doc", "docx", "jpg", "jpeg", "png", "webp"}
MAX_DOCUMENT_SIZE = 10 * 1024 * 1024


class MessageCreateInput(BaseModel):
    receiver_id: str | None = None
    target_role: str | None = None
    subject: str | None = Field(default=None, max_length=255)
    body: str = Field(min_length=1, max_length=5000)
    reference_table: str | None = None
    reference_id: str | None = None


class DocumentCreateInput(BaseModel):
    tipe_dokumen: str = Field(min_length=1, max_length=80)
    judul: str = Field(min_length=1, max_length=255)
    deskripsi: str | None = None
    status: str = "draft"
    transaction_id: str | None = None
    reference_table: str | None = None
    reference_id: str | None = None
    storage_bucket: str = DOCUMENT_BUCKET
    storage_path: str = Field(min_length=1, max_length=500)
    file_name: str = Field(min_length=1, max_length=255)
    mime_type: str = Field(min_length=1, max_length=100)
    file_size: int = Field(gt=0, le=MAX_DOCUMENT_SIZE)


def _storage_headers() -> dict[str, str]:
    return {
        "apikey": SUPABASE_SECRET_KEY,
        "Authorization": f"Bearer {SUPABASE_SECRET_KEY}",
        "Content-Type": "application/json",
    }


async def _personnel_rows() -> list[dict[str, Any]]:
    async with httpx.AsyncClient(timeout=10) as client:
        rows: list[dict[str, Any]] = []
        for table, personnel_type, select in (
            ("admins", "admin", "personnel_id,nama"),
            ("managers", "manager", "personnel_id,nama"),
            ("staff", "staff", "personnel_id,nama,role,manager_id"),
        ):
            for row in await _request(client, "GET", table, params={"select": select, "order": "nama.asc"}):
                rows.append({**row, "personnel_type": personnel_type, "status": "active"})
        return sorted(rows, key=lambda row: str(row.get("nama", "")).lower())


async def list_personnel(search: str | None = None, role: str | None = None) -> list[dict[str, Any]]:
    rows = await _personnel_rows()
    query = (search or "").strip().lower()
    return [
        row for row in rows
        if (not query or query in str(row.get("nama", "")).lower())
        and (not role or row.get("role", row.get("personnel_type")) == role)
    ]


async def _ensure_personnel(personnel_id: str) -> dict[str, Any]:
    rows = await _personnel_rows()
    person = next((row for row in rows if str(row.get("personnel_id")) == personnel_id), None)
    if not person:
        raise HTTPException(status_code=404, detail="Personnel tidak ditemukan atau tidak aktif.")
    return person


async def _personnel_auth_id(personnel_id: str) -> str | None:
    async with httpx.AsyncClient(timeout=10) as client:
        profiles = await _request(client, "GET", "user_profiles", params={"entity_type": "eq.personnel", "entity_id": f"eq.{personnel_id}", "select": "auth_user_id"})
    return str(profiles[0]["auth_user_id"]) if profiles else None


async def list_messages(user: InternalUser) -> list[dict[str, Any]]:
    async with httpx.AsyncClient(timeout=10) as client:
        return await _request(client, "GET", "messages", params={
            "select": "*",
            "or": f"(receiver_id.eq.{user.entity_id},target_role.eq.{user.role},and(receiver_id.is.null,target_role.is.null))",
            "order": "created_at.desc",
            "limit": "100",
        })


async def send_message(payload: MessageCreateInput, user: InternalUser) -> dict[str, Any]:
    if not payload.receiver_id and not payload.target_role:
        raise HTTPException(status_code=422, detail="Penerima atau target role wajib dipilih.")
    if payload.receiver_id:
        await _ensure_personnel(payload.receiver_id)
    if payload.target_role and payload.target_role not in {"admin", "manager", "kasir", "gudang", "staf_operasional", "staf_gudang"}:
        raise HTTPException(status_code=422, detail="Target role tidak valid.")

    body = {
        "message_id": str(uuid4()),
        "sender_id": user.entity_id,
        "receiver_id": payload.receiver_id,
        "target_role": payload.target_role,
        "subject": payload.subject,
        "body": payload.body.strip(),
        "reference_table": payload.reference_table,
        "reference_id": payload.reference_id,
        "is_read": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    async with httpx.AsyncClient(timeout=10) as client:
        rows = await _request(client, "POST", "messages", body=body, prefer="return=representation")
    result = rows[0] if rows else body
    if payload.receiver_id:
        target_auth_id = await _personnel_auth_id(payload.receiver_id)
        if target_auth_id:
            await create_internal_notification("internal_message", title="Pesan internal baru", message=payload.subject or "Anda menerima pesan internal.", reference_table="messages", reference_id=body["message_id"], target_user_id=target_auth_id)
    if payload.target_role:
        await create_internal_notification("internal_message", title="Pesan internal baru", message=payload.subject or "Ada pesan broadcast baru.", reference_table="messages", reference_id=body["message_id"], target_roles=[payload.target_role])
    await record_activity(user, action="create", resource_type="message", resource_id=body["message_id"], module="messages", status="success", description="Mengirim pesan internal.", metadata={"receiver_id": payload.receiver_id, "target_role": payload.target_role})
    return result


async def mark_message_read(message_id: str, user: InternalUser) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=10) as client:
        rows = await _request(client, "PATCH", "messages", params={"message_id": f"eq.{message_id}", "receiver_id": f"eq.{user.entity_id}"}, body={"is_read": True, "read_at": datetime.now(timezone.utc).isoformat()}, prefer="return=representation")
    if not rows:
        raise HTTPException(status_code=404, detail="Pesan tidak ditemukan.")
    await record_activity(user, action="read", resource_type="message", resource_id=message_id, module="messages", status="success", description="Membaca pesan internal.")
    return rows[0]


async def get_document(document_id: str, user: InternalUser) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=10) as client:
        rows = await _request(client, "GET", "documents", params={"document_id": f"eq.{document_id}", "select": "*"})
    if not rows:
        raise HTTPException(status_code=404, detail="Dokumen tidak ditemukan.")
    return rows[0]


async def list_documents(user: InternalUser, status: str | None = None, tipe_dokumen: str | None = None) -> list[dict[str, Any]]:
    params: dict[str, str] = {"select": "*", "order": "created_at.desc", "limit": "100"}
    if status:
        params["status"] = f"eq.{status}"
    if tipe_dokumen:
        params["tipe_dokumen"] = f"eq.{tipe_dokumen}"
    async with httpx.AsyncClient(timeout=10) as client:
        return await _request(client, "GET", "documents", params=params)


async def create_upload_path(file_name: str, file_size: int, mime_type: str, user: InternalUser) -> dict[str, str]:
    suffix = PurePosixPath(file_name).suffix.lower().lstrip(".")
    if suffix not in ALLOWED_DOCUMENT_TYPES or file_size <= 0 or file_size > MAX_DOCUMENT_SIZE:
        raise HTTPException(status_code=422, detail="Format atau ukuran file tidak diizinkan.")
    safe_name = re.sub(r"[^a-zA-Z0-9._-]+", "-", PurePosixPath(file_name).name).strip("-") or "document"
    path = f"{user.auth_user_id}/{datetime.now(timezone.utc):%Y/%m}/{uuid4()}/{safe_name}"
    return {"bucket": DOCUMENT_BUCKET, "path": path, "file_name": safe_name, "mime_type": mime_type}


async def create_document(payload: DocumentCreateInput, user: InternalUser) -> dict[str, Any]:
    if payload.storage_bucket != DOCUMENT_BUCKET or payload.status not in {"draft", "final", "arsip"}:
        raise HTTPException(status_code=422, detail="Metadata dokumen tidak valid.")
    if not payload.storage_path.startswith(f"{user.auth_user_id}/"):
        raise HTTPException(status_code=403, detail="Path dokumen tidak sesuai dengan pengguna.")
    body = {"document_id": str(uuid4()), "tipe_dokumen": payload.tipe_dokumen, "judul": payload.judul.strip(), "deskripsi": payload.deskripsi, "status": payload.status, "created_by": user.entity_id, "transaction_id": payload.transaction_id, "reference_table": payload.reference_table, "reference_id": payload.reference_id, "storage_bucket": payload.storage_bucket, "storage_path": payload.storage_path, "file_name": payload.file_name, "mime_type": payload.mime_type, "file_size": payload.file_size, "created_at": datetime.now(timezone.utc).isoformat(), "updated_at": datetime.now(timezone.utc).isoformat(), "visibility": "internal"}
    async with httpx.AsyncClient(timeout=10) as client:
        rows = await _request(client, "POST", "documents", body=body, prefer="return=representation")
    result = rows[0] if rows else body
    await record_activity(user, action="create", resource_type="document", resource_id=body["document_id"], module="documents", status="success", description="Membuat metadata dokumen.", metadata={"file_name": payload.file_name, "file_size": payload.file_size})
    await create_internal_notification("document_created", title="Dokumen internal baru", message=payload.judul, reference_table="documents", reference_id=body["document_id"], target_roles=["manager", "admin"])
    return result


async def document_download_url(document_id: str, user: InternalUser) -> dict[str, Any]:
    document = await get_document(document_id, user)
    bucket = document.get("storage_bucket") or DOCUMENT_BUCKET
    path = document.get("storage_path")
    if not path:
        raise HTTPException(status_code=404, detail="File dokumen belum tersedia.")
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(f"{SUPABASE_URL}/storage/v1/object/sign/{bucket}/{path}", headers=_storage_headers(), json={"expiresIn": 600})
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as error:
        raise HTTPException(status_code=502, detail="Signed URL dokumen gagal dibuat.") from error
    data = response.json()
    signed = data.get("signedURL") or data.get("signedUrl") or data.get("signed_url")
    if signed and signed.startswith("/"):
        signed = f"{SUPABASE_URL}/storage/v1{signed}"
    await record_activity(user, action="download", resource_type="document", resource_id=document_id, module="documents", status="success", description="Membuat signed URL dokumen.")
    return {"url": signed, "expires_in": 600}
