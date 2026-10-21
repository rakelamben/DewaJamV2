from datetime import datetime, timezone
import re
from pathlib import PurePosixPath
from typing import Any, Literal
from uuid import UUID, uuid4

import httpx
from fastapi import HTTPException
from pydantic import BaseModel, Field, HttpUrl

from auth import InternalUser
from config import SUPABASE_DB_SCHEMA, SUPABASE_SECRET_KEY, SUPABASE_URL
from oas import _request, create_internal_notification, record_activity


KnowledgeType = Literal["policy", "faq", "article", "video", "case_study"]

TYPE_CONFIG: dict[str, dict[str, Any]] = {
    "policy": {
        "table": "knowledge_policies",
        "id": "policy_id",
        "title": "judul",
        "summary": "ringkasan",
        "search": "judul,ringkasan,konten",
    },
    "faq": {
        "table": "knowledge_faqs",
        "id": "faq_id",
        "title": "pertanyaan",
        "summary": "jawaban",
        "search": "pertanyaan,jawaban",
    },
    "article": {
        "table": "knowledge_articles",
        "id": "article_id",
        "title": "judul",
        "summary": "ringkasan",
        "search": "judul,ringkasan,konten",
    },
    "video": {
        "table": "knowledge_videos",
        "id": "video_id",
        "title": "judul",
        "summary": "deskripsi",
        "search": "judul,deskripsi",
    },
    "case_study": {
        "table": "knowledge_case_studies",
        "id": "case_study_id",
        "title": "judul",
        "summary": "ringkasan",
        "search": "judul,ringkasan,kronologi,analisis,solusi,pelajaran",
    },
}

SOURCE_TO_TYPE = {config["table"]: knowledge_type for knowledge_type, config in TYPE_CONFIG.items()}


class CategoryInput(BaseModel):
    nama_kategori: str = Field(min_length=1, max_length=120)
    deskripsi: str | None = Field(default=None, max_length=500)
    urutan: int = Field(default=0, ge=0)


class KnowledgeInput(BaseModel):
    category_id: str | None = None
    judul: str | None = Field(default=None, min_length=1, max_length=255)
    ringkasan: str | None = None
    konten: str | None = None
    pertanyaan: str | None = None
    jawaban: str | None = None
    deskripsi: str | None = None
    video_url: HttpUrl | None = None
    durasi_menit: int | None = Field(default=None, ge=0)
    thumbnail_url: HttpUrl | None = None
    kronologi: str | None = None
    analisis: str | None = None
    solusi: str | None = None
    pelajaran: str | None = None
    prioritas: int = Field(default=2, ge=1, le=3)
    nomor_versi: str = Field(default="v1.0", min_length=1, max_length=30)
    catatan_revisi: str | None = None
    tags: list[str] | None = None
    is_published: bool = False


class KnowledgeUpdateInput(KnowledgeInput):
    judul: str | None = Field(default=None, min_length=1, max_length=255)
    nomor_versi: str | None = Field(default=None, min_length=1, max_length=30)
    is_published: bool | None = None


class KnowledgeLifecycleInput(BaseModel):
    catatan_perubahan: str | None = Field(default=None, max_length=1000)
    alasan: str | None = Field(default=None, max_length=1000)


class AttachmentCreateInput(BaseModel):
    storage_bucket: str
    storage_path: str = Field(min_length=1, max_length=1000)
    file_name: str = Field(min_length=1, max_length=255)
    mime_type: str = Field(min_length=1, max_length=150)
    file_size: int = Field(gt=0, le=10 * 1024 * 1024)


def _type_config(knowledge_type: str) -> dict[str, Any]:
    config = TYPE_CONFIG.get(knowledge_type)
    if not config:
        raise HTTPException(status_code=422, detail="Tipe knowledge tidak valid.")
    return config


def _validate_uuid(value: str, label: str) -> str:
    try:
        return str(UUID(value))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"{label} tidak valid.") from exc


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


DOCUMENT_BUCKET = "internal-documents"
MAX_ATTACHMENT_SIZE = 10 * 1024 * 1024
ALLOWED_ATTACHMENT_TYPES = {"pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx", "jpg", "jpeg", "png", "webp"}


def _storage_headers(content_type: str = "application/json") -> dict[str, str]:
    return {
        "apikey": SUPABASE_SECRET_KEY,
        "Authorization": f"Bearer {SUPABASE_SECRET_KEY}",
        "Content-Type": content_type,
    }


def _status(row: dict[str, Any]) -> str:
    return str(row.get("status") or ("published" if row.get("is_published") else "draft"))


async def _create_version(
    knowledge_type: str,
    item_id: str,
    snapshot: dict[str, Any],
    user: InternalUser,
    *,
    version: str,
    change_type: str,
    note: str | None = None,
    restore_source_version_id: str | None = None,
) -> dict[str, Any]:
    body = {
        "version_id": str(uuid4()),
        "source_table": _type_config(knowledge_type)["table"],
        "source_id": item_id,
        "nomor_versi": version,
        "catatan_perubahan": note,
        "snapshot_data": snapshot,
        "diubah_oleh": user.entity_id,
        "created_at": _now(),
        "status": snapshot.get("status") or ("published" if snapshot.get("is_published") else "draft"),
        "change_type": change_type,
        "restore_source_version_id": restore_source_version_id,
    }
    async with httpx.AsyncClient(timeout=10) as client:
        rows = await _request(client, "POST", "knowledge_versions", body=body, prefer="return=representation")
    await record_activity(user, action="version_created", resource_type=body["source_table"], resource_id=item_id, module="knowledge", status="success", description="Membuat riwayat versi knowledge.", metadata={"version_id": body["version_id"], "version": version, "change_type": change_type})
    return rows[0] if rows else body


def _next_version(current: str | None, major: bool = False) -> str:
    value = (current or "v1.0").lstrip("vV")
    try:
        major_number, minor_number = (int(part) for part in value.split(".", 1))
    except ValueError:
        major_number, minor_number = 1, 0
    return f"v{major_number + 1}.0" if major else f"v{major_number}.{minor_number + 1}"


def _clean_tags(tags: list[str] | None) -> list[str] | None:
    if tags is None:
        return None
    result = list(dict.fromkeys(tag.strip() for tag in tags if tag.strip()))
    return result or None


async def _categories_by_id() -> dict[str, dict[str, Any]]:
    async with httpx.AsyncClient(timeout=10) as client:
        rows = await _request(client, "GET", "knowledge_categories", params={"select": "*", "order": "urutan.asc,nama_kategori.asc"})
    return {str(row["category_id"]): row for row in rows}


async def list_categories() -> list[dict[str, Any]]:
    async with httpx.AsyncClient(timeout=10) as client:
        return await _request(client, "GET", "knowledge_categories", params={"select": "*", "order": "urutan.asc,nama_kategori.asc"})


async def create_category(payload: CategoryInput, user: InternalUser) -> dict[str, Any]:
    body = {"category_id": str(uuid4()), **payload.model_dump(), "nama_kategori": payload.nama_kategori.strip(), "created_at": _now()}
    async with httpx.AsyncClient(timeout=10) as client:
        rows = await _request(client, "POST", "knowledge_categories", body=body, prefer="return=representation")
    await record_activity(user, action="create", resource_type="knowledge_categories", resource_id=body["category_id"], module="knowledge", status="success", description="Membuat kategori knowledge.", metadata={"name": body["nama_kategori"]})
    return rows[0] if rows else body


async def update_category(category_id: str, payload: CategoryInput, user: InternalUser) -> dict[str, Any]:
    category_id = _validate_uuid(category_id, "Category ID")
    body = {**payload.model_dump(), "nama_kategori": payload.nama_kategori.strip()}
    async with httpx.AsyncClient(timeout=10) as client:
        rows = await _request(client, "PATCH", "knowledge_categories", params={"category_id": f"eq.{category_id}"}, body=body, prefer="return=representation")
    if not rows:
        raise HTTPException(status_code=404, detail="Kategori tidak ditemukan.")
    await record_activity(user, action="update", resource_type="knowledge_categories", resource_id=category_id, module="knowledge", status="success", description="Mengubah kategori knowledge.")
    return rows[0]


async def delete_category(category_id: str, user: InternalUser) -> dict[str, bool]:
    category_id = _validate_uuid(category_id, "Category ID")
    async with httpx.AsyncClient(timeout=10) as client:
        used = await _request(client, "GET", "knowledge_policies", params={"category_id": f"eq.{category_id}", "select": "policy_id", "limit": "1"})
        used += await _request(client, "GET", "knowledge_faqs", params={"category_id": f"eq.{category_id}", "select": "faq_id", "limit": "1"})
        used += await _request(client, "GET", "knowledge_articles", params={"category_id": f"eq.{category_id}", "select": "article_id", "limit": "1"})
        used += await _request(client, "GET", "knowledge_videos", params={"category_id": f"eq.{category_id}", "select": "video_id", "limit": "1"})
        used += await _request(client, "GET", "knowledge_case_studies", params={"category_id": f"eq.{category_id}", "select": "case_study_id", "limit": "1"})
        if used:
            raise HTTPException(status_code=409, detail="Kategori masih digunakan oleh konten.")
        rows = await _request(client, "DELETE", "knowledge_categories", params={"category_id": f"eq.{category_id}"}, prefer="return=representation")
    if not rows:
        raise HTTPException(status_code=404, detail="Kategori tidak ditemukan.")
    await record_activity(user, action="delete", resource_type="knowledge_categories", resource_id=category_id, module="knowledge", status="success", description="Menghapus kategori knowledge.")
    return {"deleted": True}


async def _validate_category(category_id: str | None) -> str | None:
    if not category_id:
        return None
    category_id = _validate_uuid(category_id, "Category ID")
    async with httpx.AsyncClient(timeout=10) as client:
        rows = await _request(client, "GET", "knowledge_categories", params={"category_id": f"eq.{category_id}", "select": "category_id", "limit": "1"})
    if not rows:
        raise HTTPException(status_code=422, detail="Kategori tidak ditemukan.")
    return category_id


def _content_body(knowledge_type: str, payload: KnowledgeInput | KnowledgeUpdateInput, user: InternalUser, *, create: bool) -> dict[str, Any]:
    allowed_by_type = {
        "policy": {"category_id", "judul", "ringkasan", "konten", "prioritas", "nomor_versi", "catatan_revisi", "tags", "is_published"},
        "faq": {"category_id", "pertanyaan", "jawaban", "nomor_versi", "catatan_revisi", "tags", "is_published"},
        "article": {"category_id", "judul", "ringkasan", "konten", "nomor_versi", "catatan_revisi", "tags", "is_published"},
        "video": {"category_id", "judul", "deskripsi", "video_url", "durasi_menit", "thumbnail_url", "nomor_versi", "catatan_revisi", "tags", "is_published"},
        "case_study": {"category_id", "judul", "ringkasan", "kronologi", "analisis", "solusi", "pelajaran", "nomor_versi", "catatan_revisi", "tags", "is_published"},
    }
    raw = payload.model_dump(exclude_unset=not create, mode="json")
    body = {key: value for key, value in raw.items() if key in allowed_by_type[knowledge_type]}
    if "tags" in body:
        body["tags"] = _clean_tags(body["tags"])
    if create:
        published = bool(body.get("is_published"))
        body.update({"created_by": user.entity_id, "view_count": 0, "created_at": _now(), "updated_at": _now(), "status": "published" if published else "draft", "published_at": _now() if published else None, "published_by": user.entity_id if published else None})
    else:
        body["updated_at"] = _now()
        body["updated_by"] = user.entity_id
        if "is_published" in body:
            body["status"] = "published" if body["is_published"] else "draft"
    if body.get("judul") is not None:
        body["judul"] = body["judul"].strip()
    for key in ("ringkasan", "konten", "pertanyaan", "jawaban", "deskripsi", "kronologi", "analisis", "solusi", "pelajaran"):
        if isinstance(body.get(key), str):
            body[key] = body[key].strip()
    return body


def _ensure_required(knowledge_type: str, body: dict[str, Any], create: bool) -> None:
    required = {
        "policy": ("judul", "ringkasan", "konten"),
        "faq": ("pertanyaan", "jawaban"),
        "article": ("judul", "ringkasan", "konten"),
        "video": ("judul", "deskripsi", "video_url"),
        "case_study": ("judul", "ringkasan", "kronologi", "analisis", "solusi", "pelajaran"),
    }[knowledge_type]
    if create:
        missing = [field for field in required if not body.get(field)]
        if missing:
            raise HTTPException(status_code=422, detail=f"Field wajib belum diisi: {', '.join(missing)}.")


async def list_knowledge(knowledge_type: str, user: InternalUser, *, category_id: str | None = None, published: bool | None = None, status: str | None = None, search: str | None = None) -> list[dict[str, Any]]:
    config = _type_config(knowledge_type)
    params: dict[str, str] = {"select": "*", "order": "updated_at.desc", "limit": "100"}
    if category_id:
        params["category_id"] = f"eq.{_validate_uuid(category_id, 'Category ID')}"
    if status:
        if status not in {"draft", "published", "archived"}:
            raise HTTPException(status_code=422, detail="Status knowledge tidak valid.")
        params["status"] = f"eq.{status}"
    elif published is not None:
        params["status"] = "eq.published" if published else "neq.published"
    if search:
        params["or"] = "(" + ",".join(f"{field}.ilike.*{search.strip()}*" for field in config["search"].split(",")) + ")"
    if user.role not in {"admin", "manager"}:
        params["status"] = "eq.published"
    async with httpx.AsyncClient(timeout=10) as client:
        rows = await _request(client, "GET", config["table"], params=params)
    categories = await _categories_by_id()
    return [{**row, "knowledge_type": knowledge_type, "category": categories.get(str(row.get("category_id")))} for row in rows]


async def get_knowledge(knowledge_type: str, item_id: str, user: InternalUser, *, track_view: bool = True) -> dict[str, Any]:
    config = _type_config(knowledge_type)
    item_id = _validate_uuid(item_id, "Knowledge ID")
    params = {config["id"]: f"eq.{item_id}", "select": "*", "limit": "1"}
    if user.role not in {"admin", "manager"}:
        params["status"] = "eq.published"
    async with httpx.AsyncClient(timeout=10) as client:
        rows = await _request(client, "GET", config["table"], params=params)
        if not rows:
            raise HTTPException(status_code=404, detail="Konten knowledge tidak ditemukan.")
        item = rows[0]
        updated = await _request(client, "PATCH", config["table"], params={config["id"]: f"eq.{item_id}"}, body={"view_count": int(item.get("view_count") or 0) + 1}, prefer="return=representation") if track_view else []
    categories = await _categories_by_id()
    if track_view:
        await record_activity(user, action="read", resource_type=config["table"], resource_id=item_id, module="knowledge", status="success", description="Membaca konten knowledge.", metadata={"knowledge_type": knowledge_type})
    result = updated[0] if updated else item
    return {**result, "knowledge_type": knowledge_type, "category": categories.get(str(result.get("category_id")))}


async def create_knowledge(knowledge_type: str, payload: KnowledgeInput, user: InternalUser) -> dict[str, Any]:
    config = _type_config(knowledge_type)
    await _validate_category(payload.category_id)
    body = _content_body(knowledge_type, payload, user, create=True)
    _ensure_required(knowledge_type, body, True)
    item_id = str(uuid4())
    body[config["id"]] = item_id
    async with httpx.AsyncClient(timeout=10) as client:
        rows = await _request(client, "POST", config["table"], body=body, prefer="return=representation")
    result = rows[0] if rows else body
    await _create_version(knowledge_type, item_id, result, user, version=str(result.get("nomor_versi") or "v1.0"), change_type="create", note=payload.catatan_revisi)
    if result.get("status") == "published":
        await _notify_important_content(knowledge_type, result, user, "published")
    await record_activity(user, action="create", resource_type=config["table"], resource_id=item_id, module="knowledge", status="success", description="Membuat konten knowledge.", metadata={"knowledge_type": knowledge_type, "judul": body.get("judul") or body.get("pertanyaan")})
    return result


async def update_knowledge(knowledge_type: str, item_id: str, payload: KnowledgeUpdateInput, user: InternalUser) -> dict[str, Any]:
    config = _type_config(knowledge_type)
    item_id = _validate_uuid(item_id, "Knowledge ID")
    await _validate_category(payload.category_id)
    body = _content_body(knowledge_type, payload, user, create=False)
    if not body:
        raise HTTPException(status_code=422, detail="Tidak ada data yang diubah.")
    async with httpx.AsyncClient(timeout=10) as client:
        rows = await _request(client, "PATCH", config["table"], params={config["id"]: f"eq.{item_id}"}, body=body, prefer="return=representation")
    if not rows:
        raise HTTPException(status_code=404, detail="Konten knowledge tidak ditemukan.")
    result = rows[0]
    await _create_version(knowledge_type, item_id, result, user, version=str(result.get("nomor_versi") or _next_version(None)), change_type="update", note=payload.catatan_revisi)
    if result.get("status") == "published":
        await _notify_important_content(knowledge_type, result, user, "updated")
    action = "publish" if body.get("is_published") is True else "update"
    await record_activity(user, action=action, resource_type=config["table"], resource_id=item_id, module="knowledge", status="success", description="Mengubah konten knowledge.", metadata={"knowledge_type": knowledge_type})
    return result


async def delete_knowledge(knowledge_type: str, item_id: str, user: InternalUser) -> dict[str, bool]:
    config = _type_config(knowledge_type)
    item_id = _validate_uuid(item_id, "Knowledge ID")
    async with httpx.AsyncClient(timeout=10) as client:
        rows = await _request(client, "DELETE", config["table"], params={config["id"]: f"eq.{item_id}"}, prefer="return=representation")
        await _request(client, "DELETE", "knowledge_bookmarks", params={"source_table": f"eq.{config['table']}", "source_id": f"eq.{item_id}"})
    if not rows:
        raise HTTPException(status_code=404, detail="Konten knowledge tidak ditemukan.")
    await record_activity(user, action="delete", resource_type=config["table"], resource_id=item_id, module="knowledge", status="success", description="Menghapus konten knowledge.", metadata={"knowledge_type": knowledge_type})
    return {"deleted": True}


async def _get_raw_knowledge(knowledge_type: str, item_id: str) -> dict[str, Any]:
    config = _type_config(knowledge_type)
    item_id = _validate_uuid(item_id, "Knowledge ID")
    async with httpx.AsyncClient(timeout=10) as client:
        rows = await _request(client, "GET", config["table"], params={config["id"]: f"eq.{item_id}", "select": "*", "limit": "1"})
    if not rows:
        raise HTTPException(status_code=404, detail="Konten knowledge tidak ditemukan.")
    return rows[0]


def _ensure_visible(item: dict[str, Any], user: InternalUser) -> None:
    if user.role not in {"admin", "manager"} and _status(item) != "published":
        raise HTTPException(status_code=404, detail="Konten knowledge tidak ditemukan.")


async def list_versions(knowledge_type: str, item_id: str) -> list[dict[str, Any]]:
    config = _type_config(knowledge_type)
    item_id = _validate_uuid(item_id, "Knowledge ID")
    async with httpx.AsyncClient(timeout=10) as client:
        return await _request(client, "GET", "knowledge_versions", params={"source_table": f"eq.{config['table']}", "source_id": f"eq.{item_id}", "select": "version_id,source_table,source_id,nomor_versi,catatan_perubahan,diubah_oleh,created_at,status,change_type,restore_source_version_id", "order": "created_at.desc"})


async def get_version(knowledge_type: str, item_id: str, version_id: str) -> dict[str, Any]:
    config = _type_config(knowledge_type)
    item_id = _validate_uuid(item_id, "Knowledge ID")
    version_id = _validate_uuid(version_id, "Version ID")
    async with httpx.AsyncClient(timeout=10) as client:
        rows = await _request(client, "GET", "knowledge_versions", params={"version_id": f"eq.{version_id}", "source_table": f"eq.{config['table']}", "source_id": f"eq.{item_id}", "select": "*", "limit": "1"})
    if not rows:
        raise HTTPException(status_code=404, detail="Versi knowledge tidak ditemukan.")
    return rows[0]


async def publish_knowledge(knowledge_type: str, item_id: str, payload: KnowledgeLifecycleInput, user: InternalUser) -> dict[str, Any]:
    config = _type_config(knowledge_type)
    current = await _get_raw_knowledge(knowledge_type, item_id)
    if _status(current) == "archived":
        raise HTTPException(status_code=409, detail="Konten archived harus dipulihkan sebelum diterbitkan.")
    version = _next_version(str(current.get("nomor_versi") or "v1.0"))
    body = {"status": "published", "is_published": True, "nomor_versi": version, "published_at": _now(), "published_by": user.entity_id, "updated_at": _now(), "updated_by": user.entity_id, "catatan_revisi": payload.catatan_perubahan}
    async with httpx.AsyncClient(timeout=10) as client:
        rows = await _request(client, "PATCH", config["table"], params={config["id"]: f"eq.{item_id}"}, body=body, prefer="return=representation")
    result = rows[0] if rows else {**current, **body}
    await _create_version(knowledge_type, item_id, result, user, version=version, change_type="publish", note=payload.catatan_perubahan)
    await _notify_important_content(knowledge_type, result, user, "published")
    await record_activity(user, action="publish", resource_type=config["table"], resource_id=item_id, module="knowledge", status="success", description="Menerbitkan konten knowledge.", metadata={"version": version})
    return result


async def archive_knowledge(knowledge_type: str, item_id: str, payload: KnowledgeLifecycleInput, user: InternalUser) -> dict[str, Any]:
    config = _type_config(knowledge_type)
    current = await _get_raw_knowledge(knowledge_type, item_id)
    reason = (payload.alasan or payload.catatan_perubahan or "").strip()
    if not reason:
        raise HTTPException(status_code=422, detail="Alasan archive wajib diisi.")
    body = {"status": "archived", "is_published": False, "archived_at": _now(), "archived_by": user.entity_id, "updated_at": _now(), "updated_by": user.entity_id, "catatan_revisi": reason}
    async with httpx.AsyncClient(timeout=10) as client:
        rows = await _request(client, "PATCH", config["table"], params={config["id"]: f"eq.{item_id}"}, body=body, prefer="return=representation")
    result = rows[0] if rows else {**current, **body}
    await _create_version(knowledge_type, item_id, result, user, version=str(result.get("nomor_versi") or "v1.0"), change_type="archive", note=reason)
    await record_activity(user, action="archive", resource_type=config["table"], resource_id=item_id, module="knowledge", status="success", description="Mengarsipkan konten knowledge.", metadata={"reason": reason})
    return result


async def restore_knowledge(knowledge_type: str, item_id: str, user: InternalUser) -> dict[str, Any]:
    config = _type_config(knowledge_type)
    current = await _get_raw_knowledge(knowledge_type, item_id)
    if _status(current) != "archived":
        raise HTTPException(status_code=409, detail="Konten tidak sedang archived.")
    body = {"status": "draft", "is_published": False, "archived_at": None, "archived_by": None, "updated_at": _now(), "updated_by": user.entity_id, "nomor_versi": _next_version(str(current.get("nomor_versi") or "v1.0"))}
    async with httpx.AsyncClient(timeout=10) as client:
        rows = await _request(client, "PATCH", config["table"], params={config["id"]: f"eq.{item_id}"}, body=body, prefer="return=representation")
    result = rows[0] if rows else {**current, **body}
    await _create_version(knowledge_type, item_id, result, user, version=str(result["nomor_versi"]), change_type="restore", note="Memulihkan konten dari archive.")
    await record_activity(user, action="restore", resource_type=config["table"], resource_id=item_id, module="knowledge", status="success", description="Memulihkan konten knowledge dari archive.")
    return result


async def restore_version(knowledge_type: str, item_id: str, version_id: str, user: InternalUser) -> dict[str, Any]:
    config = _type_config(knowledge_type)
    current = await _get_raw_knowledge(knowledge_type, item_id)
    version = await get_version(knowledge_type, item_id, version_id)
    snapshot = version.get("snapshot_data") or {}
    input_data = KnowledgeInput(**{key: value for key, value in snapshot.items() if key in KnowledgeInput.model_fields})
    body = _content_body(knowledge_type, input_data, user, create=False)
    body.update({"status": "draft", "is_published": False, "nomor_versi": _next_version(str(current.get("nomor_versi") or "v1.0")), "updated_at": _now(), "updated_by": user.entity_id})
    async with httpx.AsyncClient(timeout=10) as client:
        rows = await _request(client, "PATCH", config["table"], params={config["id"]: f"eq.{item_id}"}, body=body, prefer="return=representation")
    result = rows[0] if rows else {**current, **body}
    await _create_version(knowledge_type, item_id, result, user, version=str(result["nomor_versi"]), change_type="restore", note=f"Restore versi {version.get('nomor_versi')}.", restore_source_version_id=version_id)
    await record_activity(user, action="version_restore", resource_type=config["table"], resource_id=item_id, module="knowledge", status="success", description="Memulihkan versi knowledge.", metadata={"source_version_id": version_id})
    return result


async def _notify_important_content(knowledge_type: str, item: dict[str, Any], user: InternalUser, event: str) -> None:
    tags = {str(tag).lower() for tag in (item.get("tags") or [])}
    important = knowledge_type == "policy" and (int(item.get("prioritas") or 2) == 1 or "wajib" in tags)
    if not important:
        return
    notification_type = "knowledge_published" if event == "published" else "knowledge_updated"
    title = str(item.get("judul") or item.get("pertanyaan") or "Konten knowledge diperbarui.")
    await create_internal_notification(notification_type, title="Knowledge penting tersedia", message=f"{title} ({item.get('nomor_versi') or 'versi terbaru'})", reference_table=TYPE_CONFIG[knowledge_type]["table"], reference_id=str(item.get(TYPE_CONFIG[knowledge_type]["id"])), target_roles=["admin", "manager", "staf_operasional", "staf_gudang", "gudang", "kasir"])


async def create_attachment_upload_path(knowledge_type: str, item_id: str, file_name: str, file_size: int, mime_type: str, user: InternalUser) -> dict[str, Any]:
    config = _type_config(knowledge_type)
    item_id = _validate_uuid(item_id, "Knowledge ID")
    await _get_raw_knowledge(knowledge_type, item_id)
    suffix = PurePosixPath(file_name).suffix.lower().lstrip(".")
    if suffix not in ALLOWED_ATTACHMENT_TYPES or file_size <= 0 or file_size > MAX_ATTACHMENT_SIZE:
        raise HTTPException(status_code=422, detail="Format atau ukuran lampiran tidak diizinkan.")
    safe_name = re.sub(r"[^a-zA-Z0-9._-]+", "-", PurePosixPath(file_name).name).strip("-") or "attachment"
    path = f"{user.auth_user_id}/kms/{config['table']}/{item_id}/{uuid4()}-{safe_name}"
    return {"bucket": DOCUMENT_BUCKET, "path": path, "file_name": safe_name, "mime_type": mime_type, "expires_in": 600}


async def list_attachments(knowledge_type: str, item_id: str, user: InternalUser) -> list[dict[str, Any]]:
    config = _type_config(knowledge_type)
    _ensure_visible(await _get_raw_knowledge(knowledge_type, item_id), user)
    async with httpx.AsyncClient(timeout=10) as client:
        return await _request(client, "GET", "knowledge_attachments", params={"source_table": f"eq.{config['table']}", "source_id": f"eq.{_validate_uuid(item_id, 'Knowledge ID')}", "status": "eq.active", "select": "*", "order": "created_at.desc"})


async def create_attachment(knowledge_type: str, item_id: str, payload: AttachmentCreateInput, user: InternalUser) -> dict[str, Any]:
    config = _type_config(knowledge_type)
    item_id = _validate_uuid(item_id, "Knowledge ID")
    _ensure_visible(await _get_raw_knowledge(knowledge_type, item_id), user)
    if payload.storage_bucket != DOCUMENT_BUCKET or not payload.storage_path.startswith(f"{user.auth_user_id}/kms/{config['table']}/{item_id}/"):
        raise HTTPException(status_code=403, detail="Path lampiran tidak sesuai dengan konten.")
    body = {"attachment_id": str(uuid4()), "source_table": config["table"], "source_id": item_id, "nama_file": payload.file_name, "file_url": payload.storage_path, "tipe_file": payload.mime_type, "ukuran_bytes": payload.file_size, "storage_bucket": payload.storage_bucket, "storage_path": payload.storage_path, "file_name": payload.file_name, "mime_type": payload.mime_type, "file_size": payload.file_size, "uploaded_by": user.entity_id, "status": "active", "created_at": _now()}
    async with httpx.AsyncClient(timeout=10) as client:
        rows = await _request(client, "POST", "knowledge_attachments", body=body, prefer="return=representation")
    result = rows[0] if rows else body
    await record_activity(user, action="attachment_uploaded", resource_type=config["table"], resource_id=item_id, module="knowledge", status="success", description="Mengunggah lampiran knowledge.", metadata={"attachment_id": body["attachment_id"], "file_name": payload.file_name})
    return result


async def attachment_download_url(attachment_id: str, user: InternalUser) -> dict[str, Any]:
    attachment_id = _validate_uuid(attachment_id, "Attachment ID")
    async with httpx.AsyncClient(timeout=10) as client:
        rows = await _request(client, "GET", "knowledge_attachments", params={"attachment_id": f"eq.{attachment_id}", "status": "eq.active", "select": "*", "limit": "1"})
    if not rows:
        raise HTTPException(status_code=404, detail="Lampiran tidak ditemukan.")
    attachment = rows[0]
    table = str(attachment.get("source_table"))
    knowledge_type = SOURCE_TO_TYPE.get(table)
    if not knowledge_type:
        raise HTTPException(status_code=404, detail="Sumber lampiran tidak valid.")
    _ensure_visible(await _get_raw_knowledge(knowledge_type, str(attachment["source_id"])), user)
    bucket = attachment.get("storage_bucket") or DOCUMENT_BUCKET
    path = attachment.get("storage_path") or attachment.get("file_url")
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(f"{SUPABASE_URL}/storage/v1/object/sign/{bucket}/{path}", headers=_storage_headers(), json={"expiresIn": 600})
    if response.status_code >= 400:
        raise HTTPException(status_code=502, detail="Signed URL lampiran gagal dibuat.")
    data = response.json()
    signed = data.get("signedURL") or data.get("signedUrl") or data.get("signed_url")
    if signed and signed.startswith("/"):
        signed = f"{SUPABASE_URL}/storage/v1{signed}"
    await record_activity(user, action="attachment_download", resource_type=table, resource_id=str(attachment["source_id"]), module="knowledge", status="success", description="Membuat signed URL lampiran.", metadata={"attachment_id": attachment_id})
    return {"url": signed, "expires_in": 600}


async def delete_attachment(attachment_id: str, user: InternalUser) -> dict[str, bool]:
    attachment_id = _validate_uuid(attachment_id, "Attachment ID")
    async with httpx.AsyncClient(timeout=10) as client:
        rows = await _request(client, "GET", "knowledge_attachments", params={"attachment_id": f"eq.{attachment_id}", "select": "*", "limit": "1"})
        if not rows:
            raise HTTPException(status_code=404, detail="Lampiran tidak ditemukan.")
        attachment = rows[0]
        bucket = attachment.get("storage_bucket") or DOCUMENT_BUCKET
        path = attachment.get("storage_path") or attachment.get("file_url")
        response = await client.delete(f"{SUPABASE_URL}/storage/v1/object/{bucket}/{path}", headers=_storage_headers())
        if response.status_code >= 400 and response.status_code != 404:
            raise HTTPException(status_code=502, detail="File lampiran gagal dihapus dari Storage.")
        await _request(client, "DELETE", "knowledge_attachments", params={"attachment_id": f"eq.{attachment_id}"})
    await record_activity(user, action="attachment_deleted", resource_type=str(attachment.get("source_table")), resource_id=str(attachment.get("source_id")), module="knowledge", status="success", description="Menghapus lampiran knowledge.", metadata={"attachment_id": attachment_id})
    return {"deleted": True}


async def search_knowledge(user: InternalUser, query: str, *, knowledge_type: str | None = None, category_id: str | None = None) -> list[dict[str, Any]]:
    if not query.strip():
        return []
    types = [knowledge_type] if knowledge_type else list(TYPE_CONFIG)
    results: list[dict[str, Any]] = []
    for item_type in types:
        results.extend(await list_knowledge(item_type, user, category_id=category_id, search=query))
    return sorted(results, key=lambda row: str(row.get("updated_at") or ""), reverse=True)[:100]


async def list_bookmarks(user: InternalUser) -> list[dict[str, Any]]:
    async with httpx.AsyncClient(timeout=10) as client:
        bookmarks = await _request(client, "GET", "knowledge_bookmarks", params={"personnel_id": f"eq.{user.entity_id}", "select": "*", "order": "created_at.desc"})
    results = []
    for bookmark in bookmarks:
        knowledge_type = SOURCE_TO_TYPE.get(bookmark.get("source_table"))
        if knowledge_type:
            try:
                item = await get_knowledge(knowledge_type, str(bookmark["source_id"]), user, track_view=False)
                results.append({"bookmark": bookmark, "item": item})
            except HTTPException:
                continue
    return results


async def add_bookmark(knowledge_type: str, item_id: str, user: InternalUser) -> dict[str, Any]:
    config = _type_config(knowledge_type)
    item_id = _validate_uuid(item_id, "Knowledge ID")
    await get_knowledge(knowledge_type, item_id, user, track_view=False)
    body = {"bookmark_id": str(uuid4()), "source_table": config["table"], "source_id": item_id, "personnel_id": user.entity_id, "created_at": _now()}
    async with httpx.AsyncClient(timeout=10) as client:
        existing = await _request(client, "GET", "knowledge_bookmarks", params={"source_table": f"eq.{config['table']}", "source_id": f"eq.{item_id}", "personnel_id": f"eq.{user.entity_id}", "select": "*", "limit": "1"})
        rows = existing or await _request(client, "POST", "knowledge_bookmarks", body=body, prefer="return=representation")
    await record_activity(user, action="bookmark", resource_type=config["table"], resource_id=item_id, module="knowledge", status="success", description="Menambahkan bookmark knowledge.")
    return rows[0] if rows else body


async def remove_bookmark(knowledge_type: str, item_id: str, user: InternalUser) -> dict[str, bool]:
    config = _type_config(knowledge_type)
    item_id = _validate_uuid(item_id, "Knowledge ID")
    async with httpx.AsyncClient(timeout=10) as client:
        rows = await _request(client, "DELETE", "knowledge_bookmarks", params={"source_table": f"eq.{config['table']}", "source_id": f"eq.{item_id}", "personnel_id": f"eq.{user.entity_id}"}, prefer="return=representation")
    if rows:
        await record_activity(user, action="unbookmark", resource_type=config["table"], resource_id=item_id, module="knowledge", status="success", description="Menghapus bookmark knowledge.")
    return {"deleted": bool(rows)}
