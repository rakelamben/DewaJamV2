import httpx
from fastapi import APIRouter, Depends, HTTPException

from auth import InternalUser, require_capability

from .database import request
from .schemas import DecisionBody, PairwiseBody, RunBody, SupplierBody
from .services import activate_weight, create_weight_draft, decide_result, get_run, list_runs, list_scenarios, run_scenario, sync_registry


router = APIRouter(prefix="/api/dss", tags=["DSS"])


async def _call(function, *args, **kwargs):
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            return await function(client, *args, **kwargs)
    except HTTPException:
        raise
    except RuntimeError as error:
        raise HTTPException(status_code=502, detail="Gagal mengakses data DSS.") from error


@router.get("/scenarios")
async def read_scenarios(_: InternalUser = Depends(require_capability("dss.view"))):
    async def loader(client):
        result = await list_scenarios(client)
        if not result:
            await sync_registry(client)
            result = await list_scenarios(client)
        return result
    return await _call(loader)


@router.post("/admin/sync")
async def sync_dss(_: InternalUser = Depends(require_capability("dss.weights.manage"))):
    return await _call(sync_registry)


@router.post("/scenarios/{code}/weights")
async def create_dss_weights(code: str, payload: PairwiseBody, user: InternalUser = Depends(require_capability("dss.weights.manage"))):
    return await _call(create_weight_draft, user, code, payload.pairs, payload.nama)


@router.get("/scenarios/{code}/weights")
async def read_dss_weights(code: str, _: InternalUser = Depends(require_capability("dss.view"))):
    async def loader(client, scenario_code):
        rows = await request(client, "GET", "iss_dss_scenarios", params={"kode": f"eq.{scenario_code.upper()}", "select": "scenario_id,kode,nama"})
        if not rows: raise HTTPException(status_code=404, detail="Skenario DSS tidak ditemukan.")
        return {**rows[0], "weight_sets": await request(client, "GET", "iss_dss_weight_sets", params={"scenario_id": f"eq.{rows[0]['scenario_id']}", "order": "created_at.desc"})}
    return await _call(loader, code)


@router.post("/weights/{weight_id}/activate")
async def activate_dss_weight(weight_id: str, user: InternalUser = Depends(require_capability("dss.weights.manage"))):
    return await _call(activate_weight, user, weight_id)


@router.post("/scenarios/{code}/runs")
async def create_dss_run(code: str, payload: RunBody, user: InternalUser = Depends(require_capability("dss.run"))):
    return await _call(run_scenario, user, code, payload.scope, payload.params, payload.weight_set_id, payload.persist)


@router.get("/scenarios/{code}/runs")
async def read_dss_runs(code: str, _: InternalUser = Depends(require_capability("dss.view"))):
    return await _call(list_runs, code)


@router.get("/runs/{run_id}")
async def read_dss_run(run_id: str, _: InternalUser = Depends(require_capability("dss.view"))):
    return await _call(get_run, run_id)


@router.post("/results/{result_id}/decision")
async def decide_dss_result(result_id: str, payload: DecisionBody, user: InternalUser = Depends(require_capability("dss.decide"))):
    return await _call(decide_result, user, result_id, payload.decision, payload.note)


@router.get("/suppliers")
async def read_dss_suppliers(_: InternalUser = Depends(require_capability("dss.view"))):
    async def loader(client): return await request(client, "GET", "suppliers", params={"order": "nama.asc"})
    return await _call(loader)


@router.post("/suppliers", status_code=201)
async def create_dss_supplier(payload: SupplierBody, user: InternalUser = Depends(require_capability("dss.weights.manage"))):
    async def creator(client):
        from uuid import uuid4
        return (await request(client, "POST", "suppliers", body={"supplier_id": str(uuid4()), **payload.model_dump()}, prefer="return=representation"))[0]
    result = await _call(creator)
    await _audit_supplier(user, result["supplier_id"])
    return result


async def _audit_supplier(user: InternalUser, supplier_id: str) -> None:
    from oas import record_activity
    await record_activity(user, action="create", resource_type="suppliers", resource_id=supplier_id, module="dss", status="success", description="Membuat master supplier DSS.")
