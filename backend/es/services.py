from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import httpx
from fastapi import HTTPException

from auth import InternalUser
from oas import create_internal_notification, record_activity

from .constants import CUSTOMER_DOMAIN_CODES, INTERNAL_ROLE_DOMAIN_ACCESS
from .core.engine import run_inference
from .core.matcher import match_products_for_conclusion
from .core.types import ExpertRuleSpec, RuleClause
from .database import request
from .domains import DOMAINS, DomainDefinition
from .fact_extractors import extract_db_facts
from .repositories import load_active_products, load_knowledge_references, load_reference_options
from .schemas import ConsultBody, RuleCreateBody, RuleUpdateBody


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_domain_def(code: str) -> DomainDefinition:
    domain = DOMAINS.get(code.upper())
    if not domain:
        raise HTTPException(status_code=404, detail="Domain Sistem Pakar tidak ditemukan.")
    return domain


def _row_to_rule_spec(row: dict[str, Any]) -> ExpertRuleSpec:
    raw_conds = row.get("kondisi") if isinstance(row.get("kondisi"), list) else []
    clauses = [
        RuleClause(
            fact=str(item.get("fact") or ""),
            op=str(item.get("op") or "eq"),
            value=item.get("value"),
        )
        for item in raw_conds
        if isinstance(item, dict) and item.get("fact")
    ]
    return ExpertRuleSpec(
        code=str(row.get("kode") or ""),
        name=str(row.get("nama") or ""),
        conditions=clauses,
        conclusion_kind="intermediate_fact" if row.get("jenis_konklusi") == "intermediate_fact" else "final_conclusion",
        conclusion_code=str(row.get("kesimpulan_kode") or ""),
        conclusion_value=row.get("kesimpulan_nilai"),
        conclusion_title=str(row.get("kesimpulan_judul") or ""),
        explanation=str(row.get("penjelasan") or ""),
        recommendation=row.get("rekomendasi") if isinstance(row.get("rekomendasi"), dict) else {},
        cf_expert=float(row.get("cf_pakar") or 0.8),
        priority=int(row.get("prioritas") or 10),
        knowledge_source_table=row.get("knowledge_source_table"),
        knowledge_source_id=str(row["knowledge_source_id"]) if row.get("knowledge_source_id") else None,
    )


async def sync_registry(client: httpx.AsyncClient) -> dict[str, int]:
    summary = {"domains_synced": 0, "facts_synced": 0, "rules_synced": 0}
    for domain in DOMAINS.values():
        rows = await request(client, "GET", "iss_es_domains", params={"kode": f"eq.{domain.code}", "select": "*"})
        body_domain = {
            "kode": domain.code,
            "nama": domain.name,
            "deskripsi": domain.description,
            "target_role": domain.target_role,
            "entity_type": domain.entity_type,
            "is_active": True,
        }
        if rows:
            domain_id = str(rows[0]["domain_id"])
            await request(
                client,
                "PATCH",
                "iss_es_domains",
                params={"domain_id": f"eq.{domain_id}"},
                body=body_domain,
                prefer="return=minimal",
            )
        else:
            domain_id = str(uuid4())
            await request(
                client,
                "POST",
                "iss_es_domains",
                body={"domain_id": domain_id, **body_domain, "created_at": now()},
                prefer="return=minimal",
            )
        summary["domains_synced"] += 1

        existing_facts = await request(
            client, "GET", "iss_es_facts", params={"domain_id": f"eq.{domain_id}", "select": "*"}
        )
        facts_by_code = {str(item["kode"]): item for item in existing_facts}
        for fact in domain.facts:
            fact_body = {
                "domain_id": domain_id,
                "kode": fact.code,
                "nama": fact.name,
                "pertanyaan": fact.question,
                "tipe_nilai": fact.value_type,
                "sumber_fakta": fact.source,
                "opsi_nilai": fact.options,
                "urutan": fact.order,
                "is_required": fact.is_required,
                "is_active": True,
            }
            if fact.code in facts_by_code:
                await request(
                    client,
                    "PATCH",
                    "iss_es_facts",
                    params={"fact_id": f"eq.{facts_by_code[fact.code]['fact_id']}"},
                    body=fact_body,
                    prefer="return=minimal",
                )
            else:
                await request(
                    client,
                    "POST",
                    "iss_es_facts",
                    body={"fact_id": str(uuid4()), **fact_body},
                    prefer="return=minimal",
                )
            summary["facts_synced"] += 1

        existing_rules = await request(
            client, "GET", "iss_es_rules", params={"domain_id": f"eq.{domain_id}", "select": "*"}
        )
        rules_by_code = {str(item["kode"]): item for item in existing_rules}
        for rule in domain.rules:
            rule_body = {
                "domain_id": domain_id,
                "kode": rule.code,
                "nama": rule.name,
                "kondisi": [{"fact": c.fact, "op": c.op, "value": c.value} for c in rule.conditions],
                "jenis_konklusi": rule.conclusion_kind,
                "kesimpulan_kode": rule.conclusion_code,
                "kesimpulan_nilai": str(rule.conclusion_value) if rule.conclusion_value is not None else None,
                "kesimpulan_judul": rule.conclusion_title,
                "penjelasan": rule.explanation,
                "rekomendasi": rule.recommendation,
                "cf_pakar": rule.cf_expert,
                "prioritas": rule.priority,
                "status": "active",
                "updated_at": now(),
            }
            if rule.code not in rules_by_code:
                await request(
                    client,
                    "POST",
                    "iss_es_rules",
                    body={"rule_id": str(uuid4()), **rule_body, "created_at": now()},
                    prefer="return=minimal",
                )
                summary["rules_synced"] += 1

    return summary


async def list_domains_for_user(client: httpx.AsyncClient, user: InternalUser) -> list[dict[str, Any]]:
    allowed = INTERNAL_ROLE_DOMAIN_ACCESS.get(user.role, set())
    rows = await request(client, "GET", "iss_es_domains", params={"is_active": "eq.true", "order": "kode.asc"})
    active_codes = {str(item["kode"]) for item in rows}
    if not rows or not (set(DOMAINS) <= active_codes):
        await sync_registry(client)
        rows = await request(client, "GET", "iss_es_domains", params={"is_active": "eq.true", "order": "kode.asc"})

    output: list[dict[str, Any]] = []
    for row in rows:
        code = str(row["kode"])
        if code not in allowed or code not in DOMAINS:
            continue
        domain_id = str(row["domain_id"])
        facts = await request(
            client,
            "GET",
            "iss_es_facts",
            params={"domain_id": f"eq.{domain_id}", "is_active": "eq.true", "order": "urutan.asc"},
        )
        rules = await request(
            client,
            "GET",
            "iss_es_rules",
            params={"domain_id": f"eq.{domain_id}", "status": "eq.active", "select": "rule_id,kode,jenis_konklusi"},
        )
        user_facts_count = sum(1 for f in facts if str(f.get("sumber_fakta")) == "user_input")
        output.append({
            **row,
            "facts": facts,
            "active_rule_count": len(rules),
            "active_rules_count": len(rules),
            "user_facts_count": user_facts_count,
        })
    return output


async def get_domain_context(
    client: httpx.AsyncClient, user: InternalUser, code: str, reference_id: str | None = None
) -> dict[str, Any]:
    domain = get_domain_def(code)
    if domain.code not in INTERNAL_ROLE_DOMAIN_ACCESS.get(user.role, set()):
        raise HTTPException(status_code=403, detail=f"Role {user.role} tidak memiliki akses ke domain {domain.code}.")

    domain_row, _ = await _load_domain_row_and_rules(client, domain)
    domain_id = str(domain_row["domain_id"])
    facts = await request(
        client,
        "GET",
        "iss_es_facts",
        params={"domain_id": f"eq.{domain_id}", "is_active": "eq.true", "order": "urutan.asc"},
    )
    rules = await request(
        client,
        "GET",
        "iss_es_rules",
        params={"domain_id": f"eq.{domain_id}", "order": "prioritas.asc,kode.asc"},
    )
    user_facts_list = [f for f in facts if str(f.get("sumber_fakta")) == "user_input"]
    db_facts_spec = [f for f in facts if str(f.get("sumber_fakta")) == "db_derived"]
    inferred_facts_spec = [f for f in facts if str(f.get("sumber_fakta")) == "inferred"]

    options = await load_reference_options(client, domain.code)
    selected_ref = reference_id or (options[0]["id"] if options and domain.entity_type != "kpi" else None)

    db_facts: dict[str, Any] = {}
    meta: dict[str, Any] = {}
    if domain.entity_type == "kpi" or selected_ref:
        try:
            db_facts, meta = await extract_db_facts(client, domain.code, selected_ref)
        except HTTPException:
            db_facts, meta = {}, {}

    knowledge_refs = await load_knowledge_references(client, domain.code)
    active_rules_count = sum(1 for r in rules if str(r.get("status")) == "active")

    return {
        "domain": {
            **domain_row,
            "active_rules_count": active_rules_count,
            "user_facts_count": len(user_facts_list),
        },
        "facts": facts,
        "user_facts": user_facts_list,
        "db_facts_spec": db_facts_spec,
        "inferred_facts_spec": inferred_facts_spec,
        "rules": rules,
        "entity_type": domain.entity_type,
        "reference_options": options,
        "knowledge_references": [
            {
                "table": str(item.get("source_table") or "knowledge_policies"),
                "id": str(item.get("source_id") or ""),
                "label": str(item.get("judul") or "Dokumen SOP"),
                "kategori": str(item.get("versi") or ""),
            }
            for item in knowledge_refs
        ],
        "selected_reference_id": selected_ref,
        "db_facts": db_facts,
        "reference_meta": meta,
    }


async def _load_domain_row_and_rules(
    client: httpx.AsyncClient, domain: DomainDefinition
) -> tuple[dict[str, Any], list[ExpertRuleSpec]]:
    rows = await request(client, "GET", "iss_es_domains", params={"kode": f"eq.{domain.code}", "select": "*"})
    if not rows:
        await sync_registry(client)
        rows = await request(client, "GET", "iss_es_domains", params={"kode": f"eq.{domain.code}", "select": "*"})
    if not rows:
        raise HTTPException(status_code=409, detail="Domain Sistem Pakar belum disinkronkan.")
    domain_row = rows[0]
    rule_rows = await request(
        client,
        "GET",
        "iss_es_rules",
        params={"domain_id": f"eq.{domain_row['domain_id']}", "status": "eq.active", "order": "prioritas.asc"},
    )
    rules = [_row_to_rule_spec(row) for row in rule_rows] if rule_rows else list(domain.rules)
    return domain_row, rules


async def _maybe_trigger_workflow(
    client: httpx.AsyncClient,
    *,
    domain: DomainDefinition,
    user: InternalUser,
    reference_id: str | None,
    user_facts: dict[str, Any],
    meta: dict[str, Any],
    top_result: dict[str, Any],
    consultation_id: str,
) -> str | None:
    rec = top_result.get("recommendation") if isinstance(top_result.get("recommendation"), dict) else {}
    wf_action = rec.get("workflow_action") if isinstance(rec.get("workflow_action"), dict) else {}
    if not wf_action.get("can_trigger"):
        return None

    tipe_mutasi = str(wf_action.get("tipe_mutasi") or "adjustment")
    product_id = reference_id if domain.entity_type == "product" else meta.get("first_product_id")
    if not product_id:
        return None

    prods = await request(
        client,
        "GET",
        "products",
        params={"product_id": f"eq.{product_id}", "select": "product_id,nama_barang,stok"},
    )
    if not prods:
        return None
    product = prods[0]
    old_stock = int(product.get("stok") or 0)
    raw_qty = abs(int(float(user_facts.get("W_DIFF_QTY") or meta.get("W_PO_DEFECT_QTY") or 1)))
    qty_abs = max(1, raw_qty)

    if tipe_mutasi in {"damaged", "return_out"}:
        delta = -qty_abs
    elif tipe_mutasi == "return_in":
        delta = qty_abs
    else:
        anomaly = str(user_facts.get("W_ANOMALY_TYPE") or "")
        delta = -qty_abs if anomaly == "stok_fisik_kurang_hilang" else qty_abs

    expected_stock = max(0, old_stock + delta)
    request_id = str(uuid4())
    alasan = f"[ES {domain.code}] {top_result.get('conclusion_title')} — {wf_action.get('alasan_template') or ''}".strip()

    wf_body = {
        "request_id": request_id,
        "tipe_request": f"stock_{tipe_mutasi}",
        "reference_table": "products",
        "reference_id": str(product_id),
        "deskripsi": alasan,
        "requested_by": user.entity_id,
        "current_status": "pending",
        "title": f"[ES] {tipe_mutasi} - {product['nama_barang']}",
        "priority": "high",
        "requested_at": now(),
        "metadata": {
            "product_id": str(product_id),
            "product_name": product["nama_barang"],
            "tipe_mutasi": tipe_mutasi,
            "qty_change": delta,
            "stok_sebelum": old_stock,
            "stok_diharapkan": expected_stock,
            "es_consultation_id": consultation_id,
            "es_domain": domain.code,
        },
        "created_at": now(),
        "updated_at": now(),
    }
    await request(client, "POST", "workflow_requests", body=wf_body, prefer="return=minimal")
    await request(
        client,
        "POST",
        "workflow_approvals",
        body={"approval_id": str(uuid4()), "request_id": request_id, "status": "pending", "created_at": now()},
        prefer="return=minimal",
    )
    await create_internal_notification(
        "es_workflow_created",
        title=f"Rekomendasi Workflow Sistem Pakar ({domain.code})",
        message=f"{top_result.get('conclusion_title')} untuk {product['nama_barang']} menunggu persetujuan.",
        severity="warning",
        reference_table="workflow_requests",
        reference_id=request_id,
        target_roles=["manager", "admin"],
    )
    return request_id


async def run_consultation(
    client: httpx.AsyncClient,
    code: str,
    payload: ConsultBody,
    *,
    internal_user: InternalUser | None = None,
    customer_profile: dict[str, Any] | None = None,
) -> dict[str, Any]:
    domain = get_domain_def(code)
    if internal_user:
        if domain.code not in INTERNAL_ROLE_DOMAIN_ACCESS.get(internal_user.role, set()):
            raise HTTPException(
                status_code=403,
                detail=f"Role {internal_user.role} tidak diizinkan menjalankan {domain.code}.",
            )
    else:
        if domain.code not in CUSTOMER_DOMAIN_CODES:
            raise HTTPException(status_code=403, detail="Domain ini hanya tersedia untuk staf internal.")

    domain_row, rules = await _load_domain_row_and_rules(client, domain)
    db_facts, meta = await extract_db_facts(client, domain.code, payload.reference_id)

    effective_user_facts = payload.user_facts or payload.facts or {}
    effective_user_cfs = payload.user_cfs or payload.cf_inputs or {}
    effective_create_wf = payload.create_workflow_action or payload.create_workflow

    output = run_inference(
        rules,
        user_facts=effective_user_facts,
        user_cfs=effective_user_cfs,
        db_facts=db_facts,
    )

    products: list[dict[str, Any]] = []
    if domain.code in {"CUST_WATCH_ADVISOR", "STAFF_POS_CROSSSELL"} and output.results:
        products = await load_active_products(client)

    knowledge_refs: list[dict[str, Any]] = []
    if internal_user and output.results:
        knowledge_refs = await load_knowledge_references(client, domain.code)

    combined_facts = {**db_facts, **effective_user_facts, **output.inferred_facts}
    main_product = meta.get("main_product") if isinstance(meta, dict) else None
    rules_by_code_spec = {r.code: r for r in rules}

    serialized_results: list[dict[str, Any]] = []
    for item in output.results:
        matched_prods = (
            match_products_for_conclusion(
                item.recommendation,
                products,
                working_facts=combined_facts,
                main_product=main_product,
            )
            if products
            else []
        )
        normalized_prods = [
            {
                **p,
                "sku": str(p.get("sku") or p.get("brand") or p.get("kategori") or "DEWA-JAM"),
                "nama": str(p.get("nama") or p.get("nama_barang") or "Produk Jam"),
                "match_reasons": p.get("match_reasons") or [str(p.get("alasan_cocok") or "Sesuai kriteria pakar")],
            }
            for p in matched_prods
        ]
        enriched_traces = []
        for tr in item.matched_rules:
            rspec = rules_by_code_spec.get(str(tr.get("rule_code") or ""))
            clauses_trace = []
            if rspec:
                for cl in rspec.conditions:
                    clauses_trace.append({
                        "fact": cl.fact,
                        "op": cl.op,
                        "expected": cl.value,
                        "actual": combined_facts.get(cl.fact),
                        "cf_user": effective_user_cfs.get(cl.fact, 1.0),
                        "weight": 1.0,
                    })
            enriched_traces.append({
                **tr,
                "conclusion_type": tr.get("conclusion_kind", "final_conclusion"),
                "conclusion_title": item.conclusion_title,
                "priority": rspec.priority if rspec else 10,
                "matched_clauses": clauses_trace,
            })

        row_dict = asdict(item)
        row_dict["urutan"] = item.ranking
        row_dict["explanation"] = item.diagnosis_summary
        row_dict["matched_rules"] = enriched_traces
        row_dict["fired_rules"] = enriched_traces
        row_dict["matched_products"] = normalized_prods
        row_dict["knowledge_refs"] = knowledge_refs
        row_dict["decision"] = "pending"
        serialized_results.append(row_dict)

    inferred_structured = {
        k: {"value": v, "cf": output.inferred_cfs.get(k, 0.8)}
        for k, v in output.inferred_facts.items()
    }

    if internal_user:
        actor_type = "personnel"
        personnel_id = internal_user.entity_id
        customer_id = None
    elif customer_profile and customer_profile.get("customer_id"):
        actor_type = "customer"
        personnel_id = None
        customer_id = str(customer_profile["customer_id"])
    else:
        actor_type = "guest"
        personnel_id = None
        customer_id = None

    ref_table_map = {
        "product": "products",
        "purchase": "supplier_purchases",
        "workflow": "workflow_requests",
    }
    reference_table = ref_table_map.get(domain.entity_type) if payload.reference_id else None

    response_payload: dict[str, Any] = {
        "domain": domain.code,
        "domain_name": domain.name,
        "actor_type": actor_type,
        "reference_table": reference_table,
        "reference_id": payload.reference_id,
        "user_facts": effective_user_facts,
        "user_cfs": effective_user_cfs,
        "db_facts": db_facts,
        "inferred_facts": inferred_structured,
        "intermediate_traces": output.intermediate_traces,
        "warnings": output.warnings,
        "results": serialized_results,
        "persisted": payload.persist,
    }

    if not payload.persist:
        return response_payload

    consultation_id = str(uuid4())
    workflow_request_id: str | None = None
    if effective_create_wf and internal_user and serialized_results:
        workflow_request_id = await _maybe_trigger_workflow(
            client,
            domain=domain,
            user=internal_user,
            reference_id=payload.reference_id,
            user_facts=effective_user_facts,
            meta=meta,
            top_result=serialized_results[0],
            consultation_id=consultation_id,
        )

    await request(
        client,
        "POST",
        "iss_es_consultations",
        body={
            "consultation_id": consultation_id,
            "domain_id": str(domain_row["domain_id"]),
            "actor_type": actor_type,
            "personnel_id": personnel_id,
            "customer_id": customer_id,
            "reference_table": reference_table,
            "reference_id": payload.reference_id,
            "user_facts": effective_user_facts,
            "db_facts": db_facts,
            "inferred_facts": inferred_structured,
            "warnings": output.warnings,
            "workflow_request_id": workflow_request_id,
            "created_at": now(),
        },
        prefer="return=minimal",
    )

    for item in serialized_results:
        result_id = str(uuid4())
        item["result_id"] = result_id
        await request(
            client,
            "POST",
            "iss_es_results",
            body={
                "result_id": result_id,
                "consultation_id": consultation_id,
                "ranking": item["ranking"],
                "kesimpulan_kode": item["conclusion_code"],
                "kesimpulan_judul": item["conclusion_title"],
                "cf_kombinasi": item["cf_combined"],
                "tingkat_keyakinan": item["confidence_level"],
                "ringkasan_diagnosis": item["diagnosis_summary"],
                "rekomendasi": item["recommendation"],
                "matched_rules": item["matched_rules"],
                "matched_products": item["matched_products"],
                "knowledge_refs": item["knowledge_refs"],
                "decision": "pending",
            },
            prefer="return=minimal",
        )

    if internal_user:
        await record_activity(
            internal_user,
            action="create",
            resource_type="iss_es_consultations",
            resource_id=consultation_id,
            module="es",
            status="success",
            description=f"Menjalankan konsultasi Sistem Pakar {domain.code}.",
            metadata={"result_count": len(serialized_results), "workflow_request_id": workflow_request_id},
        )

    response_payload["consultation_id"] = consultation_id
    response_payload["workflow_request_id"] = workflow_request_id
    return response_payload


async def list_consultations(client: httpx.AsyncClient, code: str) -> list[dict[str, Any]]:
    domain = get_domain_def(code)
    rows = await request(client, "GET", "iss_es_domains", params={"kode": f"eq.{domain.code}", "select": "domain_id"})
    if not rows:
        return []
    consults = await request(
        client,
        "GET",
        "iss_es_consultations",
        params={"domain_id": f"eq.{rows[0]['domain_id']}", "order": "created_at.desc", "limit": "30"},
    )
    if not consults:
        return []
    ids = ",".join(str(item["consultation_id"]) for item in consults)
    results = await request(
        client,
        "GET",
        "iss_es_results",
        params={"consultation_id": f"in.({ids})", "order": "ranking.asc"},
    )
    by_consult: dict[str, list[dict[str, Any]]] = {}
    for row in results:
        by_consult.setdefault(str(row["consultation_id"]), []).append(row)
    return [
        {
            **item,
            "results": by_consult.get(str(item["consultation_id"]), []),
            "results_count": len(by_consult.get(str(item["consultation_id"]), [])),
            "top_result": (by_consult.get(str(item["consultation_id"]), []) or [None])[0],
        }
        for item in consults
    ]


async def get_consultation_detail(client: httpx.AsyncClient, consultation_id: str) -> dict[str, Any]:
    rows = await request(
        client, "GET", "iss_es_consultations", params={"consultation_id": f"eq.{consultation_id}", "select": "*"}
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Sesi konsultasi tidak ditemukan.")
    results = await request(
        client,
        "GET",
        "iss_es_results",
        params={"consultation_id": f"eq.{consultation_id}", "order": "ranking.asc"},
    )
    return {**rows[0], "results": results}


async def list_domain_rules(client: httpx.AsyncClient, code: str) -> dict[str, Any]:
    domain = get_domain_def(code)
    domain_row, _ = await _load_domain_row_and_rules(client, domain)
    domain_id = str(domain_row["domain_id"])
    facts = await request(
        client,
        "GET",
        "iss_es_facts",
        params={"domain_id": f"eq.{domain_id}", "is_active": "eq.true", "order": "urutan.asc"},
    )
    rules = await request(
        client,
        "GET",
        "iss_es_rules",
        params={"domain_id": f"eq.{domain_id}", "order": "prioritas.asc,kode.asc"},
    )
    knowledge_refs = await load_knowledge_references(client, domain.code)
    return {
        "domain": domain_row,
        "facts": facts,
        "rules": rules,
        "knowledge_references": [
            {
                "table": str(item.get("source_table") or "knowledge_policies"),
                "id": str(item.get("source_id") or ""),
                "label": str(item.get("judul") or "Dokumen SOP"),
                "kategori": str(item.get("versi") or ""),
            }
            for item in knowledge_refs
        ],
    }


async def create_rule(
    client: httpx.AsyncClient, user: InternalUser, code: str, payload: RuleCreateBody
) -> dict[str, Any]:
    domain = get_domain_def(code)
    domain_row, _ = await _load_domain_row_and_rules(client, domain)
    domain_id = str(domain_row["domain_id"])
    rule_id = str(uuid4())
    body = {
        "rule_id": rule_id,
        "domain_id": domain_id,
        "kode": payload.kode.strip().upper(),
        "nama": payload.nama.strip(),
        "kondisi": [item.model_dump() for item in payload.kondisi],
        "jenis_konklusi": payload.jenis_konklusi,
        "kesimpulan_kode": payload.kesimpulan_kode.strip().upper(),
        "kesimpulan_nilai": payload.kesimpulan_nilai,
        "kesimpulan_judul": payload.kesimpulan_judul.strip(),
        "penjelasan": payload.penjelasan.strip(),
        "rekomendasi": payload.rekomendasi,
        "cf_pakar": payload.cf_pakar,
        "prioritas": payload.prioritas,
        "status": payload.status,
        "created_by": user.entity_id,
        "created_at": now(),
        "updated_at": now(),
    }
    created = await request(client, "POST", "iss_es_rules", body=body, prefer="return=representation")
    await record_activity(
        user,
        action="create",
        resource_type="iss_es_rules",
        resource_id=rule_id,
        module="es",
        status="success",
        description=f"Menambah aturan pakar {body['kode']} pada {domain.code}.",
    )
    return created[0] if created else body


async def update_rule(
    client: httpx.AsyncClient, user: InternalUser, rule_id: str, payload: RuleUpdateBody
) -> dict[str, Any]:
    changes: dict[str, Any] = {"updated_at": now()}
    if payload.nama is not None:
        changes["nama"] = payload.nama.strip()
    if payload.kondisi is not None:
        changes["kondisi"] = [item.model_dump() for item in payload.kondisi]
    if payload.kesimpulan_judul is not None:
        changes["kesimpulan_judul"] = payload.kesimpulan_judul.strip()
    if payload.penjelasan is not None:
        changes["penjelasan"] = payload.penjelasan.strip()
    if payload.rekomendasi is not None:
        changes["rekomendasi"] = payload.rekomendasi
    if payload.cf_pakar is not None:
        changes["cf_pakar"] = payload.cf_pakar
    if payload.prioritas is not None:
        changes["prioritas"] = payload.prioritas
    if payload.status is not None:
        changes["status"] = payload.status

    updated = await request(
        client,
        "PATCH",
        "iss_es_rules",
        params={"rule_id": f"eq.{rule_id}"},
        body=changes,
        prefer="return=representation",
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Aturan pakar tidak ditemukan.")
    await record_activity(
        user,
        action="update",
        resource_type="iss_es_rules",
        resource_id=rule_id,
        module="es",
        status="success",
        description="Memperbarui aturan Sistem Pakar.",
        metadata=changes,
    )
    return updated[0]


async def decide_es_result(
    client: httpx.AsyncClient, user: InternalUser, result_id: str, decision: str, note: str | None
) -> dict[str, Any]:
    if decision == "rejected" and not (note or "").strip():
        raise HTTPException(status_code=422, detail="Catatan wajib diisi saat menolak rekomendasi pakar.")
    updated = await request(
        client,
        "PATCH",
        "iss_es_results",
        params={"result_id": f"eq.{result_id}"},
        body={
            "decision": decision,
            "decision_by": user.entity_id,
            "decision_note": note,
            "decided_at": now(),
        },
        prefer="return=representation",
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Hasil konsultasi tidak ditemukan.")
    await record_activity(
        user,
        action="update",
        resource_type="iss_es_results",
        resource_id=result_id,
        module="es",
        status="success",
        description=f"Keputusan hasil Sistem Pakar: {decision}.",
        metadata={"note": note},
    )
    return updated[0]


async def get_customer_advisor_schema(client: httpx.AsyncClient) -> dict[str, Any]:
    domain = get_domain_def("CUST_WATCH_ADVISOR")
    domain_row, _ = await _load_domain_row_and_rules(client, domain)
    facts = await request(
        client,
        "GET",
        "iss_es_facts",
        params={
            "domain_id": f"eq.{domain_row['domain_id']}",
            "sumber_fakta": "eq.user_input",
            "is_active": "eq.true",
            "order": "urutan.asc",
        },
    )
    return {"domain": domain_row, "questions": facts}
