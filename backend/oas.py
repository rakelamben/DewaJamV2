import logging
import hashlib
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote
from uuid import uuid4

import httpx
from fastapi import HTTPException

from auth import InternalUser

logger = logging.getLogger(__name__)


async def _request(*args: Any, **kwargs: Any) -> list[dict[str, Any]]:
    # Lazy import avoids a circular dependency because POS also emits OAS
    # events.
    from pos import _request as pos_request

    return await pos_request(*args, **kwargs)

NOTIFICATION_TYPES = {
    "low_stock",
    "stock_movement_created",
    "stock_movement_failed",
    "pos_transaction_created",
    "marketplace_order_created",
    "marketplace_payment_confirmed",
    "marketplace_order_processing",
    "payment_pending",
    "system_error",
    "security_event",
    "internal_message",
    "document_created",
    "document_uploaded",
    "document_upload_failed",
    "workflow_created",
    "workflow_approved",
    "workflow_rejected",
    "workflow_executed",
    "workflow_failed",
    "workflow_stock_conflict",
    "correspondence_created",
    "correspondence_updated",
    "correspondence_document_uploaded",
    "correspondence_disposition_created",
    "correspondence_disposition_started",
    "correspondence_disposition_completed",
    "correspondence_disposition_cancelled",
    "knowledge_published",
    "knowledge_updated",
    "knowledge_archived",
    "knowledge_attachment_uploaded",
    "dss_restock",
}
NOTIFICATION_SEVERITIES = {"info", "success", "warning", "critical"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _dedupe_key(notification_type: str, reference_id: str | None, target: str, fingerprint: str) -> str:
    digest = hashlib.sha256(fingerprint.encode()).hexdigest()[:16]
    return f"{notification_type}:{reference_id or '-'}:{target}:{digest}"


async def record_activity(
    actor: InternalUser | None,
    *,
    action: str,
    resource_type: str,
    resource_id: str | None,
    module: str,
    status: str,
    description: str,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Best-effort audit logging; never breaks the business operation."""
    # The project already has activity_logs with the legacy columns
    # (log_id/personnel_id/table_name/detail). Keep that contract and place
    # the richer OAS fields in detail for backward compatibility.
    body = {
        "log_id": str(uuid4()),
        "personnel_id": actor.entity_id if actor else None,
        "action": action,
        "table_name": resource_type,
        "record_id": resource_id,
        "detail": {
            "actor_user_id": actor.auth_user_id if actor else None,
            "actor_role": actor.role if actor else None,
            "module": module,
            "status": status,
            "description": description,
            "metadata": metadata or {},
        },
        "created_at": _now(),
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await _request(client, "POST", "activity_logs", body=body, prefer="return=minimal")
    except Exception:
        logger.exception("Gagal mencatat activity log %s %s", module, action)


async def create_internal_notification(
    notification_type: str,
    *,
    title: str,
    message: str,
    severity: str = "info",
    reference_table: str | None = None,
    reference_id: str | None = None,
    target_user_id: str | None = None,
    target_roles: list[str] | None = None,
) -> None:
    """Best-effort notification creation with a stable deduplication key."""
    if notification_type not in NOTIFICATION_TYPES:
        raise ValueError(f"Tipe notifikasi tidak dikenal: {notification_type}")
    if severity not in NOTIFICATION_SEVERITIES:
        raise ValueError(f"Severity notifikasi tidak dikenal: {severity}")

    targets = [("user", target_user_id)] if target_user_id else []
    targets.extend(("role", role) for role in (target_roles or []))
    if not targets:
        targets = [("broadcast", "broadcast")]

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            for target_kind, target in targets:
                dedupe = _dedupe_key(
                    notification_type,
                    reference_id,
                    f"{target_kind}:{target}",
                    f"{title}:{message}",
                )
                body = {
                    "notification_id": str(uuid4()),
                    "type": notification_type,
                    "title": title,
                    "message": message,
                    "severity": severity,
                    "reference_table": reference_table,
                    "reference_id": reference_id,
                    "target_user_id": target if target_kind == "user" else None,
                    "target_role": target if target_kind == "role" else None,
                    "is_read": False,
                    "read_at": None,
                    "dedupe_key": dedupe,
                    "created_at": _now(),
                }
                await _request(
                    client,
                    "POST",
                    "internal_notifications",
                    body=body,
                    prefer="return=minimal,resolution=ignore-duplicates",
                )
    except Exception:
        logger.exception("Gagal membuat notification %s", notification_type)


async def list_notifications(user: InternalUser, *, unread: bool | None = None) -> list[dict[str, Any]]:
    params: dict[str, str] = {
        "select": "*",
        "or": f"(target_user_id.eq.{user.auth_user_id},target_role.eq.{user.role},and(target_user_id.is.null,target_role.is.null))",
        "order": "created_at.desc",
        "limit": "100",
    }
    if unread is not None:
        params["is_read"] = f"eq.{str(unread).lower()}"
    async with httpx.AsyncClient(timeout=10) as client:
        return await _request(client, "GET", "internal_notifications", params=params)


async def unread_count(user: InternalUser) -> int:
    rows = await list_notifications(user, unread=True)
    return len(rows)


async def mark_notification_read(notification_id: str, user: InternalUser) -> dict[str, Any]:
    params = {
        "notification_id": f"eq.{quote(notification_id)}",
        "or": f"(target_user_id.eq.{user.auth_user_id},target_role.eq.{user.role},and(target_user_id.is.null,target_role.is.null))",
    }
    async with httpx.AsyncClient(timeout=10) as client:
        rows = await _request(
            client,
            "PATCH",
            "internal_notifications",
            params=params,
            body={"is_read": True, "read_at": _now()},
            prefer="return=representation",
        )
    if not rows:
        raise HTTPException(status_code=404, detail="Notifikasi tidak ditemukan.")
    return rows[0]


async def mark_all_notifications_read(user: InternalUser) -> dict[str, int]:
    params = {
        "is_read": "eq.false",
        "or": f"(target_user_id.eq.{user.auth_user_id},target_role.eq.{user.role},and(target_user_id.is.null,target_role.is.null))",
    }
    async with httpx.AsyncClient(timeout=10) as client:
        rows = await _request(
            client,
            "PATCH",
            "internal_notifications",
            params=params,
            body={"is_read": True, "read_at": _now()},
            prefer="return=representation",
        )
    return {"updated": len(rows)}


async def list_activity_logs(
    *,
    actor_user_id: str | None = None,
    module: str | None = None,
    action: str | None = None,
    status: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    params: dict[str, str] = {"select": "*", "order": "created_at.desc", "limit": str(min(limit, 500))}
    if actor_user_id:
        # Legacy activity_logs stores the personnel id. This filter is kept
        # for future auth-user based migrations and is applied below when
        # the richer actor id is available in detail.
        params["personnel_id"] = f"eq.{actor_user_id}"
    if action:
        params["action"] = f"eq.{action}"
    async with httpx.AsyncClient(timeout=10) as client:
        rows = await _request(client, "GET", "activity_logs", params=params)
    normalized = []
    for row in rows:
        detail = row.get("detail") if isinstance(row.get("detail"), dict) else {}
        if module and detail.get("module") != module:
            continue
        if status and detail.get("status") != status:
            continue
        normalized.append({
            "activity_id": row.get("log_id"),
            "actor_user_id": detail.get("actor_user_id"),
            "actor_role": detail.get("actor_role"),
            "action": row.get("action"),
            "resource_type": row.get("table_name"),
            "resource_id": row.get("record_id"),
            "module": detail.get("module", "legacy"),
            "status": detail.get("status", "success"),
            "description": detail.get("description", ""),
            "metadata": detail.get("metadata", {}),
            "created_at": row.get("created_at"),
        })
    return normalized
