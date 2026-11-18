import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from auth import ROLE_CAPABILITIES, InternalUser, require_capability
from customer_auth import customer_bearer, get_customer_profile

from .schemas import ConsultBody, DecisionBody, RuleCreateBody, RuleUpdateBody
from .services import (
    create_rule,
    decide_es_result,
    get_consultation_detail,
    get_customer_advisor_schema,
    get_domain_context,
    list_consultations,
    list_domain_rules,
    list_domains_for_user,
    run_consultation,
    sync_registry,
    update_rule,
)

for _es_role in ("staf_gudang", "gudang", "staf_operasional", "kasir"):
    ROLE_CAPABILITIES.setdefault(_es_role, set()).update({"es.view", "es.consult", "es.decide"})
ROLE_CAPABILITIES.setdefault("manager", set()).update(
    {"es.view", "es.consult", "es.rules.manage", "es.decide"}
)

router = APIRouter(tags=["Expert System"])


async def _call(function, *args, **kwargs):
    try:
        async with httpx.AsyncClient(timeout=45) as client:
            return await function(client, *args, **kwargs)
    except HTTPException:
        raise
    except RuntimeError as error:
        raise HTTPException(status_code=502, detail=f"Gagal mengakses data Sistem Pakar: {error}") from error


@router.get("/api/es/domains")
async def read_es_domains(user: InternalUser = Depends(require_capability("es.view"))):
    return await _call(list_domains_for_user, user)


@router.post("/api/es/admin/sync")
async def sync_es_registry(_: InternalUser = Depends(require_capability("es.rules.manage"))):
    return await _call(sync_registry)


@router.get("/api/es/domains/{code}")
@router.get("/api/es/domains/{code}/context")
async def read_es_domain_context(
    code: str,
    reference_id: str | None = None,
    user: InternalUser = Depends(require_capability("es.view")),
):
    return await _call(get_domain_context, user, code, reference_id)


@router.post("/api/es/domains/{code}/consult")
async def create_es_consultation(
    code: str,
    payload: ConsultBody,
    user: InternalUser = Depends(require_capability("es.consult")),
):
    return await _call(run_consultation, code, payload, internal_user=user)


@router.get("/api/es/domains/{code}/consultations")
async def read_es_consultations(
    code: str,
    _: InternalUser = Depends(require_capability("es.view")),
):
    return await _call(list_consultations, code)


@router.get("/api/es/consultations/{consultation_id}")
async def read_es_consultation_detail(
    consultation_id: str,
    _: InternalUser = Depends(require_capability("es.view")),
):
    return await _call(get_consultation_detail, consultation_id)


@router.get("/api/es/domains/{code}/rules")
async def read_es_domain_rules(
    code: str,
    _: InternalUser = Depends(require_capability("es.view")),
):
    return await _call(list_domain_rules, code)


@router.post("/api/es/domains/{code}/rules", status_code=201)
async def add_es_domain_rule(
    code: str,
    payload: RuleCreateBody,
    user: InternalUser = Depends(require_capability("es.rules.manage")),
):
    return await _call(create_rule, user, code, payload)


@router.patch("/api/es/rules/{rule_id}")
async def edit_es_rule(
    rule_id: str,
    payload: RuleUpdateBody,
    user: InternalUser = Depends(require_capability("es.rules.manage")),
):
    return await _call(update_rule, user, rule_id, payload)


@router.post("/api/es/results/{result_id}/decision")
async def decide_es_consultation_result(
    result_id: str,
    payload: DecisionBody,
    user: InternalUser = Depends(require_capability("es.decide")),
):
    return await _call(decide_es_result, user, result_id, payload.decision, payload.note)


@router.get("/api/customer/es/advisor")
async def read_customer_watch_advisor():
    return await _call(get_customer_advisor_schema)


@router.post("/api/customer/es/advisor")
@router.post("/api/customer/es/advisor/consult")
async def consult_customer_watch_advisor(
    payload: ConsultBody,
    credentials: HTTPAuthorizationCredentials | None = Depends(customer_bearer),
):
    customer_profile = None
    if credentials and credentials.credentials:
        try:
            customer_profile = await get_customer_profile(credentials)
        except HTTPException:
            customer_profile = None
    return await _call(
        run_consultation,
        "CUST_WATCH_ADVISOR",
        payload,
        internal_user=None,
        customer_profile=customer_profile,
    )
