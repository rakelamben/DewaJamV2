from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import httpx
from fastapi import HTTPException

from auth import InternalUser
from oas import create_internal_notification, record_activity

from .constants import ROLE_SCENARIO_ACCESS
from .core.ahp import build_matrix, compute_weights, consistency
from .core.pipeline import run_pipeline
from .database import request
from .repositories import load_product_rows, load_supplier_rows
from .scenarios import SCENARIOS, Scenario, build_alternative, classify, prefilter, recommendation


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_scenario(code: str) -> Scenario:
    scenario = SCENARIOS.get(code.upper())
    if not scenario:
        raise HTTPException(status_code=404, detail="Skenario DSS tidak ditemukan.")
    return scenario


def _create_pair_map(scenario: Scenario, pairs: dict[str, float]) -> dict[tuple[int, int], float]:
    indexes = {item.code: index for index, item in enumerate(scenario.criteria)}
    converted: dict[tuple[int, int], float] = {}
    for key, value in pairs.items():
        parts = key.replace("-", "/").split("/")
        if len(parts) != 2 or parts[0] not in indexes or parts[1] not in indexes:
            raise HTTPException(status_code=422, detail=f"Pairwise tidak valid: {key}.")
        first, second = indexes[parts[0]], indexes[parts[1]]
        if first == second or value <= 0:
            raise HTTPException(status_code=422, detail="Pairwise harus membandingkan dua kriteria dengan nilai positif.")
        if first > second:
            first, second, value = second, first, 1 / value
        converted[(first, second)] = float(value)
    return converted


async def sync_registry(client: httpx.AsyncClient) -> dict[str, int]:
    result = {"scenarios_created": 0, "criteria_created": 0, "weights_created": 0}
    for scenario in SCENARIOS.values():
        rows = await request(client, "GET", "iss_dss_scenarios", params={"kode": f"eq.{scenario.code}", "select": "*"})
        if rows:
            scenario_row = rows[0]
            await request(client, "PATCH", "iss_dss_scenarios", params={"scenario_id": f"eq.{scenario_row['scenario_id']}"}, body={"nama": scenario.name, "alternative_type": scenario.alternative_type, "is_active": True}, prefer="return=minimal")
        else:
            scenario_row = {"scenario_id": str(uuid4())}
            await request(client, "POST", "iss_dss_scenarios", body={**scenario_row, "kode": scenario.code, "nama": scenario.name, "deskripsi": scenario.name, "alternative_type": scenario.alternative_type, "is_active": True}, prefer="return=representation")
            result["scenarios_created"] += 1
        scenario_id = str(scenario_row["scenario_id"])
        criteria_rows = await request(client, "GET", "iss_dss_criteria", params={"scenario_id": f"eq.{scenario_id}", "select": "*"})
        existing = {str(row["kode"]): row for row in criteria_rows}
        for criterion in scenario.criteria:
            body = {"scenario_id": scenario_id, "kode": criterion.code, "nama": criterion.name, "satuan": criterion.unit, "is_benefit": criterion.is_benefit, "urutan": criterion.order, "is_active": True}
            if criterion.code in existing:
                await request(client, "PATCH", "iss_dss_criteria", params={"criteria_id": f"eq.{existing[criterion.code]['criteria_id']}"}, body=body, prefer="return=minimal")
            else:
                await request(client, "POST", "iss_dss_criteria", body={"criteria_id": str(uuid4()), **body}, prefer="return=minimal")
                result["criteria_created"] += 1
        for row in criteria_rows:
            if str(row["kode"]) not in {item.code for item in scenario.criteria}:
                await request(client, "PATCH", "iss_dss_criteria", params={"criteria_id": f"eq.{row['criteria_id']}"}, body={"is_active": False}, prefer="return=minimal")
        active = await request(client, "GET", "iss_dss_weight_sets", params={"scenario_id": f"eq.{scenario_id}", "status": "eq.active", "select": "weight_set_id"})
        if not active:
            matrix = build_matrix(scenario.default_pairwise, len(scenario.criteria))
            weights = compute_weights(matrix)
            lambda_max, ci, cr = consistency(matrix, weights)
            weight_id = str(uuid4())
            await request(client, "POST", "iss_dss_weight_sets", body={"weight_set_id": weight_id, "scenario_id": scenario_id, "nama": "Default", "lambda_max": lambda_max, "ci": ci, "cr": cr, "status": "active", "activated_at": now()}, prefer="return=minimal")
            criteria_rows = await request(client, "GET", "iss_dss_criteria", params={"scenario_id": f"eq.{scenario_id}", "select": "criteria_id,kode"})
            by_code = {str(row["kode"]): row["criteria_id"] for row in criteria_rows}
            for index, criterion in enumerate(scenario.criteria):
                await request(client, "POST", "iss_dss_weights", body={"weight_set_id": weight_id, "criteria_id": by_code[criterion.code], "bobot": weights[index]}, prefer="return=minimal")
            for (first, second), value in scenario.default_pairwise.items():
                await request(client, "POST", "iss_dss_pairwise", body={"weight_set_id": weight_id, "criteria_1": by_code[scenario.criteria[first].code], "criteria_2": by_code[scenario.criteria[second].code], "nilai": value}, prefer="return=minimal")
            result["weights_created"] += 1
    return result


async def list_scenarios(client: httpx.AsyncClient) -> list[dict[str, Any]]:
    rows = await request(client, "GET", "iss_dss_scenarios", params={"is_active": "eq.true", "order": "kode.asc"})
    output = []
    for row in rows:
        scenario = SCENARIOS.get(str(row["kode"]))
        criteria = await request(client, "GET", "iss_dss_criteria", params={"scenario_id": f"eq.{row['scenario_id']}", "is_active": "eq.true", "order": "urutan.asc"})
        active = await request(client, "GET", "iss_dss_weight_sets", params={"scenario_id": f"eq.{row['scenario_id']}", "status": "eq.active", "select": "*"})
        output.append({**row, "criteria": criteria, "active_weight_set": active[0] if active else None, "default_params": scenario.default_params if scenario else {}})
    return output


async def create_weight_draft(client: httpx.AsyncClient, user: InternalUser, code: str, pairs: dict[str, float], name: str) -> dict[str, Any]:
    scenario = get_scenario(code)
    converted = _create_pair_map(scenario, pairs)
    try:
        matrix = build_matrix(converted, len(scenario.criteria))
        weights = compute_weights(matrix)
        lambda_max, ci, cr = consistency(matrix, weights)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    scenario_rows = await request(client, "GET", "iss_dss_scenarios", params={"kode": f"eq.{scenario.code}", "select": "scenario_id"})
    if not scenario_rows: raise HTTPException(status_code=409, detail="Registry DSS belum disinkronkan.")
    scenario_id = scenario_rows[0]["scenario_id"]
    weight_id = str(uuid4())
    await request(client, "POST", "iss_dss_weight_sets", body={"weight_set_id": weight_id, "scenario_id": scenario_id, "nama": name, "lambda_max": lambda_max, "ci": ci, "cr": cr, "status": "draft", "created_by": user.entity_id}, prefer="return=minimal")
    criteria = await request(client, "GET", "iss_dss_criteria", params={"scenario_id": f"eq.{scenario_id}", "is_active": "eq.true", "select": "criteria_id,kode", "order": "urutan.asc"})
    by_code = {str(row["kode"]): row["criteria_id"] for row in criteria}
    for index, criterion in enumerate(scenario.criteria):
        await request(client, "POST", "iss_dss_weights", body={"weight_set_id": weight_id, "criteria_id": by_code[criterion.code], "bobot": weights[index]}, prefer="return=minimal")
    for (first, second), value in converted.items():
        await request(client, "POST", "iss_dss_pairwise", body={"weight_set_id": weight_id, "criteria_1": by_code[scenario.criteria[first].code], "criteria_2": by_code[scenario.criteria[second].code], "nilai": value}, prefer="return=minimal")
    await record_activity(user, action="create", resource_type="iss_dss_weight_sets", resource_id=weight_id, module="dss", status="success", description="Membuat draft bobot DSS.", metadata={"scenario": scenario.code, "cr": cr})
    return {"weight_set_id": weight_id, "scenario": scenario.code, "weights": dict(zip((item.code for item in scenario.criteria), weights)), "lambda_max": lambda_max, "ci": ci, "cr": cr, "status": "draft"}


async def activate_weight(client: httpx.AsyncClient, user: InternalUser, weight_id: str) -> dict[str, Any]:
    rows = await request(client, "GET", "iss_dss_weight_sets", params={"weight_set_id": f"eq.{weight_id}", "select": "*"})
    if not rows: raise HTTPException(status_code=404, detail="Weight set tidak ditemukan.")
    weight = rows[0]
    if float(weight.get("cr") or 1) > .1: raise HTTPException(status_code=422, detail=f"CR {weight['cr']} lebih besar dari 0.1.")
    await request(client, "PATCH", "iss_dss_weight_sets", params={"scenario_id": f"eq.{weight['scenario_id']}", "status": "eq.active"}, body={"status": "archived"}, prefer="return=minimal")
    updated = await request(client, "PATCH", "iss_dss_weight_sets", params={"weight_set_id": f"eq.{weight_id}", "status": "eq.draft"}, body={"status": "active", "activated_at": now()}, prefer="return=representation")
    if not updated: raise HTTPException(status_code=409, detail="Weight set bukan draft atau sudah berubah.")
    await record_activity(user, action="update", resource_type="iss_dss_weight_sets", resource_id=weight_id, module="dss", status="success", description="Mengaktifkan bobot DSS.")
    return updated[0]


async def run_scenario(client: httpx.AsyncClient, user: InternalUser, code: str, scope: dict[str, Any], overrides: dict[str, Any], weight_id: str | None, persist: bool) -> dict[str, Any]:
    scenario = get_scenario(code)
    if scenario.code not in ROLE_SCENARIO_ACCESS.get(user.role, set()): raise HTTPException(status_code=403, detail=f"Role {user.role} tidak dapat menjalankan {scenario.code}.")
    params = {**scenario.default_params, **overrides}
    rows = await load_product_rows(client, category=scope.get("kategori"), window_days=int(params["window_days"])) if scenario.alternative_type == "product" else await load_supplier_rows(client, category=scope.get("kategori"), window_days=int(params["window_days"]), min_purchases=int(params["min_purchases"]))
    alternatives = [build_alternative(scenario, row) for row in rows]
    scenario_rows = await request(client, "GET", "iss_dss_scenarios", params={"kode": f"eq.{scenario.code}", "select": "scenario_id"})
    if not scenario_rows: raise HTTPException(status_code=409, detail="Registry DSS belum disinkronkan.")
    scenario_id = scenario_rows[0]["scenario_id"]
    weight_params = {"scenario_id": f"eq.{scenario_id}", "status": "eq.active", "select": "*"}
    if weight_id: weight_params["weight_set_id"] = f"eq.{weight_id}"
    weight_rows = await request(client, "GET", "iss_dss_weight_sets", params=weight_params)
    if not weight_rows: raise HTTPException(status_code=422, detail="Weight set aktif tidak ditemukan.")
    weight = weight_rows[0]
    criteria_rows = await request(client, "GET", "iss_dss_criteria", params={"scenario_id": f"eq.{scenario_id}", "is_active": "eq.true", "select": "criteria_id,kode", "order": "urutan.asc"})
    criteria_by_id = {str(row["criteria_id"]): str(row["kode"]) for row in criteria_rows}
    weight_rows = await request(client, "GET", "iss_dss_weights", params={"weight_set_id": f"eq.{weight['weight_set_id']}", "select": "criteria_id,bobot"})
    weights = {criteria_by_id[str(row["criteria_id"])]: float(row["bobot"]) for row in weight_rows if str(row["criteria_id"]) in criteria_by_id}
    if set(weights) != {item.code for item in scenario.criteria}: raise HTTPException(status_code=422, detail="Weight set tidak lengkap.")
    result = run_pipeline(alternatives, scenario.criteria, weights, prefilter=lambda item, values: prefilter(scenario, item, values), group_key=lambda item: item.meta.get("category") if scenario.alternative_type == "product" else None, classify=lambda score, values: classify(scenario, score, values), recommend=lambda item, score, status, values: recommendation(scenario, item, score, status, values), params=params)
    if rows and scenario.alternative_type == "product" and rows[0].get("latest_generated_at"):
        latest = str(rows[0]["latest_generated_at"])
        if latest[:10] < str(datetime.now(timezone.utc).date()):
            result.warnings.append({"kode": "MIS_STALE", "pesan": "Data MIS lebih lama dari satu hari."})
    output = {"scenario": scenario.code, "weight_set": {"id": weight["weight_set_id"], "cr": weight.get("cr")}, "scope": scope, "params": params, "warnings": result.warnings, "excluded": [item.__dict__ for item in result.excluded], "results": result.results, "persisted": persist}
    if not persist: return output
    run_id = str(uuid4())
    await request(client, "POST", "iss_dss_runs", body={"run_id": run_id, "scenario_id": scenario_id, "weight_set_id": weight["weight_set_id"], "scope": scope, "params": params, "warnings": result.warnings, "excluded": output["excluded"], "run_by": user.entity_id, "created_at": now()}, prefer="return=minimal")
    for item in result.results:
        await request(client, "POST", "iss_dss_results", body={"result_id": str(uuid4()), "run_id": run_id, "product_id": item["id"] if item["type"] == "product" else None, "supplier_id": item["id"] if item["type"] == "supplier" else None, "group_key": item["group_key"], "skor": item["skor"], "ranking": item["ranking"], "status": item["status"], "input_values": item["input_values"], "contributions": item["contributions"], "recommendation": item["recommendation"], "decision": "pending"}, prefer="return=minimal")
    await record_activity(user, action="create", resource_type="iss_dss_runs", resource_id=run_id, module="dss", status="success", description=f"Menjalankan DSS {scenario.code}.", metadata={"result_count": len(result.results)})
    if scenario.code == "RESTOCK" and any(item["status"] == "Restock Segera" for item in result.results):
        request_id = str(uuid4())
        await request(client, "POST", "workflow_requests", body={"request_id": request_id, "tipe_request": "dss_restock", "reference_table": "iss_dss_runs", "reference_id": run_id, "deskripsi": "Rekomendasi restock segera dari DSS.", "requested_by": user.entity_id, "current_status": "pending", "title": "Rekomendasi restock DSS", "priority": "high", "requested_at": now(), "metadata": {"run_id": run_id, "scenario": scenario.code}, "created_at": now(), "updated_at": now()}, prefer="return=minimal")
        await request(client, "POST", "workflow_approvals", body={"approval_id": str(uuid4()), "request_id": request_id, "status": "pending", "created_at": now()}, prefer="return=minimal")
        await request(client, "PATCH", "iss_dss_runs", params={"run_id": f"eq.{run_id}"}, body={"workflow_request_id": request_id}, prefer="return=minimal")
        await create_internal_notification("dss_restock", title="Rekomendasi restock DSS", message="Terdapat produk yang perlu segera direstock.", severity="warning", reference_table="iss_dss_runs", reference_id=run_id, target_roles=["manager", "admin"])
        output["workflow_request_id"] = request_id
    output["run_id"] = run_id
    return output


async def list_runs(client: httpx.AsyncClient, code: str) -> list[dict[str, Any]]:
    scenario = get_scenario(code)
    rows = await request(client, "GET", "iss_dss_scenarios", params={"kode": f"eq.{scenario.code}", "select": "scenario_id"})
    if not rows: return []
    return await request(client, "GET", "iss_dss_runs", params={"scenario_id": f"eq.{rows[0]['scenario_id']}", "order": "created_at.desc", "limit": "50"})


async def get_run(client: httpx.AsyncClient, run_id: str) -> dict[str, Any]:
    runs = await request(client, "GET", "iss_dss_runs", params={"run_id": f"eq.{run_id}", "select": "*"})
    if not runs: raise HTTPException(status_code=404, detail="Run DSS tidak ditemukan.")
    results = await request(client, "GET", "iss_dss_results", params={"run_id": f"eq.{run_id}", "order": "group_key.asc,ranking.asc"})
    return {**runs[0], "results": results}


async def decide_result(client: httpx.AsyncClient, user: InternalUser, result_id: str, decision: str, note: str | None) -> dict[str, Any]:
    if decision == "rejected" and not (note or "").strip(): raise HTTPException(status_code=422, detail="Catatan wajib diisi saat menolak rekomendasi.")
    rows = await request(client, "GET", "iss_dss_results", params={"result_id": f"eq.{result_id}", "decision": "eq.pending", "select": "*"})
    if not rows: raise HTTPException(status_code=404, detail="Hasil DSS tidak ditemukan atau sudah diputuskan.")
    updated = await request(client, "PATCH", "iss_dss_results", params={"result_id": f"eq.{result_id}", "decision": "eq.pending"}, body={"decision": decision, "decision_by": user.entity_id, "decision_note": note, "decided_at": now()}, prefer="return=representation")
    if not updated: raise HTTPException(status_code=409, detail="Hasil DSS sudah diputuskan user lain.")
    await record_activity(user, action="update", resource_type="iss_dss_results", resource_id=result_id, module="dss", status="success", description=f"Keputusan DSS: {decision}.", metadata={"note": note})
    return updated[0]
