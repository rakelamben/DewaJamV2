import logging
from typing import Any, Callable

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from config import SUPABASE_PUBLISHABLE_KEY, SUPABASE_SECRET_KEY, SUPABASE_URL

bearer_scheme = HTTPBearer(auto_error=False)
logger = logging.getLogger(__name__)


class InternalUser(BaseModel):
    auth_user_id: str
    email: str | None = None
    entity_type: str
    entity_id: str
    role: str
    name: str


# Capability map is intentionally kept in application code for this first
# foundation phase. It can later be backed by role_capabilities without
# changing the endpoint dependency API.
ROLE_CAPABILITIES: dict[str, set[str]] = {
    "admin": {"*"},
    "manager": {
        "internal.access",
        "notifications.view",
        "notifications.mark_read",
        "notifications.mark_all_read",
        "activity_log.view",
        "activity_log.export",
        "warehouse.view",
        "warehouse.movement.create",
        "pos.access",
        "pos.transaction.create",
        "pos.transaction.view",
        "marketplace.order.view",
        "messages.view",
        "messages.send",
        "messages.mark_read",
        "personnel.view",
        "documents.view",
        "documents.create",
        "documents.upload",
        "documents.download",
        "documents.update",
        "documents.archive",
        "documents.delete",
        "workflow.view",
        "workflow.create",
        "workflow.submit",
        "workflow.cancel",
        "workflow.approval.view",
        "workflow.approve",
        "workflow.reject",
        "workflow.execute",
        "workflow.history.view",
        "correspondence.view",
        "correspondence.create",
        "correspondence.update",
        "correspondence.archive",
        "correspondence.delete",
        "correspondence.upload",
        "correspondence.download",
        "correspondence.disposition.view",
        "correspondence.disposition.create",
        "correspondence.disposition.update",
        "correspondence.disposition.complete",
        "correspondence.disposition.cancel",
        "dss.view",
        "dss.run",
        "dss.weights.manage",
        "dss.decide",
        "es.view",
        "es.consult",
        "es.rules.manage",
        "es.decide",
    },
    "staf_gudang": {
        "internal.access",
        "notifications.view",
        "notifications.mark_read",
        "notifications.mark_all_read",
        "warehouse.view",
        "warehouse.movement.create",
        "marketplace.order.view",
        "messages.view",
        "messages.send",
        "messages.mark_read",
        "personnel.view",
        "documents.view",
        "documents.create",
        "documents.upload",
        "documents.download",
        "documents.update",
        "documents.archive",
        "workflow.view",
        "workflow.create",
        "workflow.submit",
        "workflow.cancel",
        "workflow.approval.view",
        "workflow.approve",
        "workflow.reject",
        "workflow.execute",
        "workflow.history.view",
        "correspondence.view",
        "correspondence.create",
        "correspondence.update",
        "correspondence.archive",
        "correspondence.upload",
        "correspondence.download",
        "correspondence.disposition.view",
        "correspondence.disposition.create",
        "correspondence.disposition.update",
        "correspondence.disposition.complete",
        "correspondence.disposition.cancel",
        "dss.view",
        "dss.run",
        "es.view",
        "es.consult",
        "es.decide",
    },
    "gudang": {
        "internal.access",
        "notifications.view",
        "notifications.mark_read",
        "notifications.mark_all_read",
        "warehouse.view",
        "warehouse.movement.create",
        "marketplace.order.view",
        "messages.view",
        "messages.send",
        "messages.mark_read",
        "personnel.view",
        "documents.view",
        "documents.create",
        "documents.upload",
        "documents.download",
        "workflow.view",
        "workflow.create",
        "workflow.submit",
        "workflow.cancel",
        "workflow.history.view",
        "correspondence.view",
        "correspondence.create",
        "correspondence.upload",
        "correspondence.download",
        "correspondence.disposition.view",
        "correspondence.disposition.update",
        "correspondence.disposition.complete",
    },
    "staf_operasional": {
        "internal.access",
        "notifications.view",
        "notifications.mark_read",
        "notifications.mark_all_read",
        "pos.access",
        "pos.transaction.create",
        "pos.transaction.view",
        "marketplace.order.view",
        "messages.view",
        "messages.send",
        "messages.mark_read",
        "personnel.view",
        "documents.view",
        "documents.create",
        "documents.upload",
        "documents.download",
        "workflow.view",
        "workflow.create",
        "workflow.submit",
        "workflow.cancel",
        "workflow.history.view",
        "correspondence.view",
        "correspondence.create",
        "correspondence.upload",
        "correspondence.download",
        "correspondence.disposition.view",
        "correspondence.disposition.update",
        "correspondence.disposition.complete",
    },
    "kasir": {
        "internal.access",
        "notifications.view",
        "notifications.mark_read",
        "notifications.mark_all_read",
        "pos.access",
        "pos.transaction.create",
        "pos.transaction.view",
        "marketplace.order.view",
        "messages.view",
        "messages.send",
        "messages.mark_read",
        "personnel.view",
        "documents.view",
        "documents.create",
        "documents.upload",
        "documents.download",
        "workflow.view",
        "workflow.create",
        "workflow.submit",
        "workflow.cancel",
        "workflow.history.view",
        "correspondence.view",
        "correspondence.download",
        "correspondence.disposition.view",
        "correspondence.disposition.update",
        "correspondence.disposition.complete",
    },
}

# KMS MVP permissions. Admin already has wildcard access; operational roles
# receive read/search/bookmark access while manager owns content governance.
_KNOWLEDGE_READ_CAPABILITIES = {
    "knowledge.view",
    "knowledge.search",
    "knowledge.bookmark",
    "knowledge.category.view",
}
_KNOWLEDGE_MANAGER_CAPABILITIES = _KNOWLEDGE_READ_CAPABILITIES | {
    "knowledge.create",
    "knowledge.update",
    "knowledge.publish",
    "knowledge.archive",
    "knowledge.delete",
    "knowledge.category.manage",
    "knowledge.version.view",
    "knowledge.version.restore",
    "knowledge.upload",
    "knowledge.download",
    "knowledge.notification.manage",
    "knowledge.editor.manage",
}
_MIS_MANAGER_CAPABILITIES = {
    "mis.dashboard.view",
    "mis.sales.view",
    "mis.inventory.view",
    "mis.profitability.view",
    "mis.kpi.view",
    "mis.kpi.manage",
    "mis.report.export",
    "mis.summary.refresh",
}
for _role in ("staf_gudang", "gudang", "staf_operasional", "kasir"):
    ROLE_CAPABILITIES[_role].add("mis.dashboard.view")
ROLE_CAPABILITIES["staf_operasional"].add("mis.sales.view")
ROLE_CAPABILITIES["staf_gudang"].add("mis.inventory.view")
ROLE_CAPABILITIES["gudang"].add("mis.inventory.view")
ROLE_CAPABILITIES["manager"].update(_MIS_MANAGER_CAPABILITIES)
for _role in ("staf_gudang", "gudang", "staf_operasional", "kasir"):
    ROLE_CAPABILITIES[_role].update(_KNOWLEDGE_READ_CAPABILITIES)
ROLE_CAPABILITIES["manager"].update(_KNOWLEDGE_MANAGER_CAPABILITIES)

def has_capability(user: InternalUser, capability: str) -> bool:
    capabilities = ROLE_CAPABILITIES.get(user.role, set())
    return "*" in capabilities or capability in capabilities


def require_capability(capability: str) -> Callable:
    async def dependency(
        current_user: InternalUser = Depends(get_current_internal_user),
    ) -> InternalUser:
        if not has_capability(current_user, capability):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role {current_user.role} tidak memiliki izin {capability}.",
            )
        return current_user

    return dependency


async def _get_json(
    client: httpx.AsyncClient,
    path: str,
    *,
    headers: dict[str, str],
    params: dict[str, str] | None = None,
) -> Any:
    response = await client.get(f"{SUPABASE_URL}{path}", headers=headers, params=params)
    if response.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Layanan Supabase tidak dapat diakses.",
        )
    return response.json()


async def get_current_internal_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> InternalUser:
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token diperlukan.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not SUPABASE_URL or not SUPABASE_PUBLISHABLE_KEY or not SUPABASE_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Konfigurasi Supabase backend belum lengkap.",
        )

    token = credentials.credentials
    auth_headers = {
        "apikey": SUPABASE_PUBLISHABLE_KEY,
        "Authorization": f"Bearer {token}",
    }
    db_headers = {
        "apikey": SUPABASE_SECRET_KEY,
        "Authorization": f"Bearer {SUPABASE_SECRET_KEY}",
        "Accept-Profile": "toko_jam",
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            auth_response = await client.get(
                f"{SUPABASE_URL}/auth/v1/user", headers=auth_headers
            )
            if auth_response.status_code in (401, 403):
                logger.info(
                    "Supabase menolak session dengan status %s: %s",
                    auth_response.status_code,
                    auth_response.text,
                )
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token Supabase tidak valid atau sudah kedaluwarsa.",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            if auth_response.status_code >= 400:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Layanan Supabase Auth tidak dapat diakses.",
                )

            auth_user = auth_response.json()
            auth_user_id = auth_user.get("id")
            if not auth_user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token Supabase tidak valid.",
                )

            profiles = await _get_json(
                client,
                "/rest/v1/user_profiles",
                headers=db_headers,
                params={
                    "auth_user_id": f"eq.{auth_user_id}",
                    "select": "auth_user_id,entity_type,entity_id",
                },
            )
            if not profiles:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Akun tidak memiliki profil internal.",
                )

            profile = profiles[0]
            profile_type = str(profile.get("entity_type", "")).strip().lower()
            profile_entity_id = profile.get("entity_id")

            if profile_type != "personnel" or not profile_entity_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Akun bukan personnel internal.",
                )

            personnel_rows = await _get_json(
                client,
                "/rest/v1/personnel",
                headers=db_headers,
                params={
                    "personnel_id": f"eq.{profile_entity_id}",
                    "select": "personnel_id,personnel_type",
                },
            )
            if not personnel_rows:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Data personnel tidak ditemukan.",
                )

            personnel = personnel_rows[0]
            personnel_type = str(personnel.get("personnel_type", "")).strip().lower()
            detail_config = {
                "admin": ("admins", "admin", "nama"),
                "manager": ("managers", "manager", "nama"),
                "staff": ("staff", None, "nama,role"),
            }.get(personnel_type)
            if not detail_config:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Tipe personnel tidak memiliki akses internal.",
                )

            table, fixed_role, select = detail_config
            entity_rows = await _get_json(
                client,
                f"/rest/v1/{table}",
                headers=db_headers,
                params={
                    "personnel_id": f"eq.{profile_entity_id}",
                    "select": select,
                },
            )
            if not entity_rows:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Detail akun personnel tidak ditemukan.",
                )

            entity = entity_rows[0]
            role = fixed_role or str(entity.get("role", "")).strip().lower()
            allowed_roles = {
                "admin",
                "manager",
                "staf_gudang",
                "staf_operasional",
                "kasir",
                "gudang",
            }
            if role not in allowed_roles:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Role akun tidak diizinkan untuk sistem internal.",
                )

            return InternalUser(
                auth_user_id=auth_user_id,
                email=auth_user.get("email"),
                entity_type="personnel",
                entity_id=profile_entity_id,
                role=role,
                name=entity.get("nama", ""),
            )
    except HTTPException:
        raise
    except httpx.HTTPError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Tidak dapat menghubungi Supabase.",
        ) from error
