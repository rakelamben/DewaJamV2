from datetime import date
from io import StringIO

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware

from auth import InternalUser, get_current_internal_user, require_capability
from config import FRONTEND_ORIGIN
from pos import (
    CancelTransactionInput,
    PosTransactionInput,
    cancel_transaction,
    create_transaction,
    get_transaction,
    get_product,
    list_products,
    list_today_transactions,
)
from customer_auth import CustomerProfileUpdate, CustomerRegisterInput, customer_bearer, get_customer_profile, register_customer, update_customer_profile
from customer_marketplace import (
    AddressInput,
    AddressUpdate,
    MarketplaceCheckoutInput,
    create_address,
    create_marketplace_transaction,
    confirm_marketplace_payment,
    delete_address,
    get_customer_order,
    list_addresses,
    list_customer_orders,
    list_marketplace_stores,
    update_address,
)
from customer_cart import CartItemInput, add_cart_item, clear_cart, delete_cart_item, get_cart, update_cart_item
from masterdata import ProductInput, StoreInput, create_master_product, create_master_store, delete_master_product, delete_master_store, list_master_products, list_master_stores, update_master_product, update_master_store
from warehouse import StockMovementInput, create_movement, get_movements, get_stock
from oas import (
    list_activity_logs,
    list_notifications,
    mark_all_notifications_read,
    mark_notification_read,
    unread_count,
)
from collaboration import (
    DocumentCreateInput,
    MessageCreateInput,
    create_document,
    create_upload_path,
    document_download_url,
    list_documents,
    list_messages,
    list_personnel,
    mark_message_read,
    send_message,
)
from workflow import (
    WorkflowCreateInput,
    WorkflowDecisionInput,
    create_workflow,
    decide_workflow,
    get_workflow,
    list_workflows,
)
from correspondence import (
    CorrespondenceCreateInput,
    CorrespondenceUpdateInput,
    DispositionCreateInput,
    DispositionUpdateInput,
    archive_correspondence,
    create_correspondence,
    create_disposition,
    get_correspondence,
    list_correspondence,
    list_dispositions,
    update_correspondence,
    update_disposition,
)
from knowledge import (
    AttachmentCreateInput,
    CategoryInput,
    KnowledgeInput,
    KnowledgeLifecycleInput,
    KnowledgeUpdateInput,
    add_bookmark,
    create_category,
    create_attachment,
    create_attachment_upload_path,
    create_knowledge,
    archive_knowledge,
    attachment_download_url,
    delete_attachment,
    delete_category,
    delete_knowledge,
    get_knowledge,
    list_bookmarks,
    list_categories,
    list_attachments,
    list_knowledge,
    list_versions,
    remove_bookmark,
    search_knowledge,
    get_version,
    publish_knowledge,
    restore_knowledge,
    restore_version,
    update_category,
    update_knowledge,
)
from mis import get_dashboard
from mis_kpi import KpiTargetCreate, KpiTargetUpdate, create_target, get_performance, list_kpis, list_targets, update_target
from mis_reports import inventory_report, profitability_report, sales_report, to_csv
from dss.routes import router as dss_router
from es.routes import router as es_router
import httpx

app = FastAPI(title="Test2 API")
app.include_router(dss_router)
app.include_router(es_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.get("/api/internal/mis/dashboard")
async def read_mis_dashboard(
    date_from: str | None = None,
    date_to: str | None = None,
    channel: str | None = None,
    current_user: InternalUser = Depends(require_capability("mis.dashboard.view")),
):
    return await get_dashboard(current_user, date_from=date_from, date_to=date_to, channel=channel)


def _period(date_from: date | None, date_to: date | None) -> tuple[date, date]:
    end = date_to or date.today()
    start = date_from or end.replace(day=1)
    return start, end


@app.get("/api/internal/mis/kpis")
async def read_kpis(
    active_only: bool = True,
    current_user: InternalUser = Depends(require_capability("mis.kpi.view")),
):
    del current_user
    async with httpx.AsyncClient(timeout=20) as client:
        return {"items": await list_kpis(client, active_only)}


@app.get("/api/internal/mis/kpis/targets")
async def read_kpi_targets(
    kpi_id: str | None = None,
    periode_tipe: str | None = None,
    periode_mulai: date | None = None,
    periode_selesai: date | None = None,
    personnel_id: str | None = None,
    current_user: InternalUser = Depends(require_capability("mis.kpi.view")),
):
    del current_user
    params = {}
    if kpi_id: params["kpi_id"] = f"eq.{kpi_id}"
    if periode_tipe: params["periode_tipe"] = f"eq.{periode_tipe}"
    if periode_mulai: params["periode_mulai"] = f"gte.{periode_mulai}"
    if periode_selesai: params["periode_selesai"] = f"lte.{periode_selesai}"
    if personnel_id: params["personnel_id"] = f"eq.{personnel_id}"
    async with httpx.AsyncClient(timeout=20) as client:
        return {"items": await list_targets(client, params)}


@app.post("/api/internal/mis/kpis/targets")
async def add_kpi_target(payload: KpiTargetCreate, current_user: InternalUser = Depends(require_capability("mis.kpi.manage"))):
    async with httpx.AsyncClient(timeout=20) as client:
        return await create_target(client, payload, current_user)


@app.patch("/api/internal/mis/kpis/targets/{target_id}")
async def edit_kpi_target(target_id: str, payload: KpiTargetUpdate, current_user: InternalUser = Depends(require_capability("mis.kpi.manage"))):
    del current_user
    async with httpx.AsyncClient(timeout=20) as client:
        return await update_target(client, target_id, payload)


@app.get("/api/internal/mis/kpis/performance")
async def read_kpi_performance(
    date_from: date | None = None,
    date_to: date | None = None,
    personnel_id: str | None = None,
    current_user: InternalUser = Depends(require_capability("mis.kpi.view")),
):
    del current_user
    start, end = _period(date_from, date_to)
    async with httpx.AsyncClient(timeout=20) as client:
        return await get_performance(client, start, end, personnel_id)


async def _report_data(report: str, date_from: date | None, date_to: date | None, channel: str | None = None, product_id: str | None = None, stock_status: str = "all", category: str | None = None):
    start, end = _period(date_from, date_to)
    async with httpx.AsyncClient(timeout=30) as client:
        if report == "sales": return await sales_report(client, start, end, channel)
        if report == "profitability": return await profitability_report(client, start, end, product_id)
        return await inventory_report(client, start, end, stock_status, category)


@app.get("/api/internal/mis/reports/sales")
async def read_sales_report(date_from: date | None = None, date_to: date | None = None, channel: str | None = None, current_user: InternalUser = Depends(require_capability("mis.sales.view"))):
    del current_user
    return await _report_data("sales", date_from, date_to, channel=channel)


@app.get("/api/internal/mis/reports/profitability")
async def read_profitability_report(date_from: date | None = None, date_to: date | None = None, product_id: str | None = None, current_user: InternalUser = Depends(require_capability("mis.profitability.view"))):
    del current_user
    return await _report_data("profitability", date_from, date_to, product_id=product_id)


@app.get("/api/internal/mis/reports/inventory")
async def read_inventory_report(date_from: date | None = None, date_to: date | None = None, stock_status: str = Query("all", pattern="^(all|in_stock|low_stock|out_of_stock)$"), category: str | None = None, current_user: InternalUser = Depends(require_capability("mis.inventory.view"))):
    del current_user
    return await _report_data("inventory", date_from, date_to, stock_status=stock_status, category=category)


@app.get("/api/internal/mis/reports/{report_type}/export")
async def export_mis_report(report_type: str, date_from: date | None = None, date_to: date | None = None, channel: str | None = None, product_id: str | None = None, stock_status: str = "all", category: str | None = None, current_user: InternalUser = Depends(require_capability("mis.report.export"))):
    if report_type not in {"sales", "profitability", "inventory"}:
        raise HTTPException(status_code=404, detail="Jenis laporan tidak ditemukan.")
    del current_user
    data = await _report_data(report_type, date_from, date_to, channel, product_id, stock_status, category)
    stream = to_csv(data, report_type)
    start, end = _period(date_from, date_to)
    return StreamingResponse(iter([stream.getvalue()]), media_type="text/csv; charset=utf-8", headers={"Content-Disposition": f'attachment; filename="{report_type}-report-{start}-{end}.csv"'})


@app.get("/")
def read_root():
    return {"message": "FastAPI backend berjalan"}


@app.get("/api/auth/me", response_model=InternalUser)
async def read_current_user(
    current_user: InternalUser = Depends(get_current_internal_user),
):
    return current_user


@app.post("/api/customer/register", status_code=201)
async def create_customer_profile(
    payload: CustomerRegisterInput,
    credentials: HTTPAuthorizationCredentials | None = Depends(customer_bearer),
):
    return await register_customer(payload, credentials)


@app.get("/api/customer/me")
async def read_customer_profile(
    credentials: HTTPAuthorizationCredentials | None = Depends(customer_bearer),
):
    return await get_customer_profile(credentials)


@app.patch("/api/customer/me")
async def edit_customer_profile(payload: CustomerProfileUpdate, credentials: HTTPAuthorizationCredentials | None = Depends(customer_bearer)):
    return await update_customer_profile(payload, credentials)


@app.get("/api/customer/cart")
async def read_customer_cart(credentials: HTTPAuthorizationCredentials | None = Depends(customer_bearer)):
    return await get_cart(credentials)


@app.post("/api/customer/cart/items")
async def add_customer_cart_item(payload: CartItemInput, credentials: HTTPAuthorizationCredentials | None = Depends(customer_bearer)):
    return await add_cart_item(payload, credentials)


@app.patch("/api/customer/cart/items/{cart_item_id}")
async def edit_customer_cart_item(cart_item_id: str, payload: CartItemInput, credentials: HTTPAuthorizationCredentials | None = Depends(customer_bearer)):
    return await update_cart_item(cart_item_id, payload, credentials)


@app.delete("/api/customer/cart/items/{cart_item_id}")
async def remove_customer_cart_item(cart_item_id: str, credentials: HTTPAuthorizationCredentials | None = Depends(customer_bearer)):
    return await delete_cart_item(cart_item_id, credentials)


@app.delete("/api/customer/cart")
async def empty_customer_cart(credentials: HTTPAuthorizationCredentials | None = Depends(customer_bearer)):
    return await clear_cart(credentials)


@app.get("/api/customer/addresses")
async def read_customer_addresses(credentials: HTTPAuthorizationCredentials | None = Depends(customer_bearer)):
    return await list_addresses(credentials)


@app.post("/api/customer/addresses", status_code=201)
async def add_customer_address(payload: AddressInput, credentials: HTTPAuthorizationCredentials | None = Depends(customer_bearer)):
    return await create_address(payload, credentials)


@app.patch("/api/customer/addresses/{address_id}")
async def edit_customer_address(address_id: str, payload: AddressUpdate, credentials: HTTPAuthorizationCredentials | None = Depends(customer_bearer)):
    return await update_address(address_id, payload, credentials)


@app.delete("/api/customer/addresses/{address_id}")
async def remove_customer_address(address_id: str, credentials: HTTPAuthorizationCredentials | None = Depends(customer_bearer)):
    return await delete_address(address_id, credentials)


@app.post("/api/marketplace/transactions", status_code=201)
async def create_marketplace_order(payload: MarketplaceCheckoutInput, credentials: HTTPAuthorizationCredentials | None = Depends(customer_bearer)):
    return await create_marketplace_transaction(payload, credentials)


@app.get("/api/customer/orders")
async def read_customer_orders(credentials: HTTPAuthorizationCredentials | None = Depends(customer_bearer)):
    return await list_customer_orders(credentials)


@app.post("/api/customer/orders/{transaction_id}/confirm-payment")
async def confirm_customer_payment(transaction_id: str, credentials: HTTPAuthorizationCredentials | None = Depends(customer_bearer)):
    return await confirm_marketplace_payment(transaction_id, credentials)


@app.get("/api/customer/orders/{transaction_id}")
async def read_customer_order(transaction_id: str, credentials: HTTPAuthorizationCredentials | None = Depends(customer_bearer)):
    return await get_customer_order(transaction_id, credentials)


@app.get("/api/pos/products")
async def read_pos_products(
    _: InternalUser = Depends(require_capability("pos.access")),
):
    return await list_products()


@app.get("/api/internal/masterdata/products")
async def read_master_products(_: InternalUser = Depends(require_capability("internal.access"))):
    return await list_master_products()


@app.post("/api/internal/masterdata/products", status_code=201)
async def add_master_product(payload: ProductInput, _: InternalUser = Depends(require_capability("internal.access"))):
    return await create_master_product(payload)


@app.patch("/api/internal/masterdata/products/{product_id}")
async def edit_master_product(product_id: str, payload: ProductInput, _: InternalUser = Depends(require_capability("internal.access"))):
    return await update_master_product(product_id, payload)


@app.delete("/api/internal/masterdata/products/{product_id}")
async def remove_master_product(product_id: str, _: InternalUser = Depends(require_capability("internal.access"))):
    return await delete_master_product(product_id)


@app.get("/api/internal/masterdata/stores")
async def read_master_stores(_: InternalUser = Depends(require_capability("internal.access"))):
    return await list_master_stores()


@app.post("/api/internal/masterdata/stores", status_code=201)
async def add_master_store(payload: StoreInput, _: InternalUser = Depends(require_capability("internal.access"))):
    return await create_master_store(payload)


@app.patch("/api/internal/masterdata/stores/{store_id}")
async def edit_master_store(store_id: str, payload: StoreInput, _: InternalUser = Depends(require_capability("internal.access"))):
    return await update_master_store(store_id, payload)


@app.delete("/api/internal/masterdata/stores/{store_id}")
async def remove_master_store(store_id: str, _: InternalUser = Depends(require_capability("internal.access"))):
    return await delete_master_store(store_id)


@app.get("/api/internal/warehouse/stock")
async def read_warehouse_stock(_: InternalUser = Depends(require_capability("warehouse.view"))):
    return await get_stock()


@app.get("/api/internal/warehouse/movements")
async def read_warehouse_movements(product_id: str | None = None, tipe_mutasi: str | None = None, _: InternalUser = Depends(require_capability("warehouse.view"))):
    return await get_movements(product_id, tipe_mutasi)


@app.post("/api/internal/warehouse/movements", status_code=201)
async def add_warehouse_movement(payload: StockMovementInput, current_user: InternalUser = Depends(require_capability("warehouse.movement.create"))):
    if payload.tipe_mutasi in {"adjustment", "damaged", "return_in", "return_out"}:
        raise HTTPException(status_code=409, detail="Tipe mutasi ini harus diajukan melalui workflow approval.")
    return await create_movement(payload, current_user)


@app.get("/api/marketplace/products")
async def read_marketplace_products():
    return await list_products()


@app.get("/api/marketplace/products/{product_id}")
async def read_marketplace_product(product_id: str):
    return await get_product(product_id)


@app.get("/api/marketplace/stores")
async def read_marketplace_stores():
    return await list_marketplace_stores()


@app.post("/api/pos/transactions")
async def create_pos_transaction(
    payload: PosTransactionInput,
    current_user: InternalUser = Depends(require_capability("pos.transaction.create")),
):
    return await create_transaction(payload, current_user)


@app.get("/api/pos/transactions/today")
async def read_today_pos_transactions(
    _: InternalUser = Depends(require_capability("pos.transaction.view")),
):
    return await list_today_transactions()


@app.get("/api/pos/transactions/{transaction_id}")
async def read_pos_transaction(
    transaction_id: str,
    _: InternalUser = Depends(require_capability("pos.transaction.view")),
):
    return await get_transaction(transaction_id)


@app.post("/api/pos/transactions/{transaction_id}/cancel")
async def cancel_pos_transaction(
    transaction_id: str,
    payload: CancelTransactionInput,
    current_user: InternalUser = Depends(require_capability("pos.transaction.create")),
):
    return await cancel_transaction(transaction_id, payload, current_user)


@app.get("/api/internal/notifications")
async def read_internal_notifications(
    unread: bool | None = None,
    current_user: InternalUser = Depends(require_capability("notifications.view")),
):
    return await list_notifications(current_user, unread=unread)


@app.get("/api/internal/notifications/unread-count")
async def read_internal_unread_count(
    current_user: InternalUser = Depends(require_capability("notifications.view")),
):
    return {"unread_count": await unread_count(current_user)}


@app.patch("/api/internal/notifications/{notification_id}/read")
async def read_one_internal_notification(
    notification_id: str,
    current_user: InternalUser = Depends(require_capability("notifications.mark_read")),
):
    return await mark_notification_read(notification_id, current_user)


@app.post("/api/internal/notifications/read-all")
async def read_all_internal_notifications(
    current_user: InternalUser = Depends(require_capability("notifications.mark_all_read")),
):
    return await mark_all_notifications_read(current_user)


@app.get("/api/internal/activity-logs")
async def read_internal_activity_logs(
    actor_user_id: str | None = None,
    module: str | None = None,
    action: str | None = None,
    status: str | None = None,
    limit: int = 100,
    _: InternalUser = Depends(require_capability("activity_log.view")),
):
    return await list_activity_logs(
        actor_user_id=actor_user_id,
        module=module,
        action=action,
        status=status,
        limit=limit,
    )


@app.get("/api/internal/personnel")
async def read_internal_personnel(
    search: str | None = None,
    role: str | None = None,
    _: InternalUser = Depends(require_capability("personnel.view")),
):
    return await list_personnel(search=search, role=role)


@app.get("/api/internal/messages")
async def read_internal_messages(
    current_user: InternalUser = Depends(require_capability("messages.view")),
):
    return await list_messages(current_user)


@app.post("/api/internal/messages", status_code=201)
async def create_internal_message(
    payload: MessageCreateInput,
    current_user: InternalUser = Depends(require_capability("messages.send")),
):
    return await send_message(payload, current_user)


@app.post("/api/internal/messages/{message_id}/read")
async def mark_internal_message_read(
    message_id: str,
    current_user: InternalUser = Depends(require_capability("messages.mark_read")),
):
    return await mark_message_read(message_id, current_user)


@app.get("/api/internal/documents")
async def read_internal_documents(
    status: str | None = None,
    tipe_dokumen: str | None = None,
    current_user: InternalUser = Depends(require_capability("documents.view")),
):
    return await list_documents(current_user, status=status, tipe_dokumen=tipe_dokumen)


@app.post("/api/internal/documents/upload-path")
async def create_internal_document_upload_path(
    file_name: str,
    file_size: int,
    mime_type: str,
    current_user: InternalUser = Depends(require_capability("documents.upload")),
):
    return await create_upload_path(file_name, file_size, mime_type, current_user)


@app.post("/api/internal/documents", status_code=201)
async def create_internal_document(
    payload: DocumentCreateInput,
    current_user: InternalUser = Depends(require_capability("documents.create")),
):
    return await create_document(payload, current_user)


@app.get("/api/internal/documents/{document_id}/download-url")
async def get_internal_document_download_url(
    document_id: str,
    current_user: InternalUser = Depends(require_capability("documents.download")),
):
    return await document_download_url(document_id, current_user)


@app.get("/api/internal/workflows")
async def read_internal_workflows(
    status: str | None = None,
    current_user: InternalUser = Depends(require_capability("workflow.view")),
):
    return await list_workflows(current_user, status=status)


@app.get("/api/internal/workflows/pending-approvals")
async def read_pending_workflows(
    current_user: InternalUser = Depends(require_capability("workflow.approval.view")),
):
    return await list_workflows(current_user, status="pending")


@app.get("/api/internal/workflows/{request_id}")
async def read_internal_workflow(
    request_id: str,
    current_user: InternalUser = Depends(require_capability("workflow.view")),
):
    return await get_workflow(request_id, current_user)


@app.post("/api/internal/workflows", status_code=201)
async def create_internal_workflow(
    payload: WorkflowCreateInput,
    current_user: InternalUser = Depends(require_capability("workflow.create")),
):
    return await create_workflow(payload, current_user)


@app.post("/api/internal/workflows/{request_id}/approve")
async def approve_internal_workflow(
    request_id: str,
    payload: WorkflowDecisionInput,
    current_user: InternalUser = Depends(require_capability("workflow.approve")),
):
    return await decide_workflow(request_id, "approve", payload, current_user)


@app.post("/api/internal/workflows/{request_id}/reject")
async def reject_internal_workflow(
    request_id: str,
    payload: WorkflowDecisionInput,
    current_user: InternalUser = Depends(require_capability("workflow.reject")),
):
    return await decide_workflow(request_id, "reject", payload, current_user)


@app.get("/api/internal/correspondence")
async def read_internal_correspondence(
    tipe: str | None = None,
    status: str | None = None,
    search: str | None = None,
    _: InternalUser = Depends(require_capability("correspondence.view")),
):
    return await list_correspondence(tipe=tipe, status=status, search=search)


@app.get("/api/internal/correspondence/{correspondence_id}")
async def read_one_internal_correspondence(
    correspondence_id: str,
    _: InternalUser = Depends(require_capability("correspondence.view")),
):
    return await get_correspondence(correspondence_id)


@app.post("/api/internal/correspondence", status_code=201)
async def add_internal_correspondence(
    payload: CorrespondenceCreateInput,
    current_user: InternalUser = Depends(require_capability("correspondence.create")),
):
    return await create_correspondence(payload, current_user)


@app.patch("/api/internal/correspondence/{correspondence_id}")
async def edit_internal_correspondence(
    correspondence_id: str,
    payload: CorrespondenceUpdateInput,
    current_user: InternalUser = Depends(require_capability("correspondence.update")),
):
    return await update_correspondence(correspondence_id, payload, current_user)


@app.post("/api/internal/correspondence/{correspondence_id}/archive")
async def archive_internal_correspondence(
    correspondence_id: str,
    current_user: InternalUser = Depends(require_capability("correspondence.archive")),
):
    return await archive_correspondence(correspondence_id, current_user)


@app.get("/api/internal/correspondence/{correspondence_id}/dispositions")
async def read_internal_dispositions(
    correspondence_id: str,
    current_user: InternalUser = Depends(require_capability("correspondence.disposition.view")),
):
    return await list_dispositions(correspondence_id, current_user)


@app.post("/api/internal/correspondence/{correspondence_id}/dispositions", status_code=201)
async def add_internal_disposition(
    correspondence_id: str,
    payload: DispositionCreateInput,
    current_user: InternalUser = Depends(require_capability("correspondence.disposition.create")),
):
    return await create_disposition(correspondence_id, payload, current_user)


@app.patch("/api/internal/dispositions/{disposition_id}")
async def edit_internal_disposition(
    disposition_id: str,
    payload: DispositionUpdateInput,
    current_user: InternalUser = Depends(require_capability("correspondence.disposition.update")),
):
    return await update_disposition(disposition_id, payload, current_user)


@app.get("/api/internal/knowledge/categories")
async def read_knowledge_categories(
    _: InternalUser = Depends(require_capability("knowledge.category.view")),
):
    return await list_categories()


@app.post("/api/internal/knowledge/categories", status_code=201)
async def add_knowledge_category(
    payload: CategoryInput,
    current_user: InternalUser = Depends(require_capability("knowledge.category.manage")),
):
    return await create_category(payload, current_user)


@app.patch("/api/internal/knowledge/categories/{category_id}")
async def edit_knowledge_category(
    category_id: str,
    payload: CategoryInput,
    current_user: InternalUser = Depends(require_capability("knowledge.category.manage")),
):
    return await update_category(category_id, payload, current_user)


@app.delete("/api/internal/knowledge/categories/{category_id}")
async def remove_knowledge_category(
    category_id: str,
    current_user: InternalUser = Depends(require_capability("knowledge.category.manage")),
):
    return await delete_category(category_id, current_user)


@app.get("/api/internal/knowledge/search")
async def search_internal_knowledge(
    q: str,
    knowledge_type: str | None = None,
    category_id: str | None = None,
    current_user: InternalUser = Depends(require_capability("knowledge.search")),
):
    return await search_knowledge(current_user, q, knowledge_type=knowledge_type, category_id=category_id)


@app.get("/api/internal/knowledge/bookmarks")
async def read_knowledge_bookmarks(
    current_user: InternalUser = Depends(require_capability("knowledge.bookmark")),
):
    return await list_bookmarks(current_user)


@app.get("/api/internal/knowledge/{knowledge_type}")
async def read_knowledge_list(
    knowledge_type: str,
    category_id: str | None = None,
    published: bool | None = None,
    search: str | None = None,
    current_user: InternalUser = Depends(require_capability("knowledge.view")),
):
    return await list_knowledge(knowledge_type, current_user, category_id=category_id, published=published, search=search)


@app.get("/api/internal/masterdata/knowledge")
async def read_masterdata_knowledge(
    knowledge_type: str | None = None,
    category_id: str | None = None,
    status: str | None = None,
    search: str | None = None,
    current_user: InternalUser = Depends(require_capability("knowledge.editor.manage")),
):
    types = [knowledge_type] if knowledge_type else ["policy", "faq", "article", "video", "case_study"]
    results: list[dict] = []
    for item_type in types:
        results.extend(await list_knowledge(item_type, current_user, category_id=category_id, status=status, search=search))
    return sorted(results, key=lambda item: str(item.get("updated_at") or ""), reverse=True)


@app.post("/api/internal/knowledge/{knowledge_type}", status_code=201)
async def add_knowledge_item(
    knowledge_type: str,
    payload: KnowledgeInput,
    current_user: InternalUser = Depends(require_capability("knowledge.create")),
):
    return await create_knowledge(knowledge_type, payload, current_user)


@app.get("/api/internal/knowledge/{knowledge_type}/{item_id}")
async def read_knowledge_item(
    knowledge_type: str,
    item_id: str,
    current_user: InternalUser = Depends(require_capability("knowledge.view")),
):
    return await get_knowledge(knowledge_type, item_id, current_user)


@app.patch("/api/internal/knowledge/{knowledge_type}/{item_id}")
async def edit_knowledge_item(
    knowledge_type: str,
    item_id: str,
    payload: KnowledgeUpdateInput,
    current_user: InternalUser = Depends(require_capability("knowledge.update")),
):
    return await update_knowledge(knowledge_type, item_id, payload, current_user)


@app.delete("/api/internal/knowledge/{knowledge_type}/{item_id}")
async def remove_knowledge_item(
    knowledge_type: str,
    item_id: str,
    current_user: InternalUser = Depends(require_capability("knowledge.delete")),
):
    return await delete_knowledge(knowledge_type, item_id, current_user)


@app.post("/api/internal/knowledge/{knowledge_type}/{item_id}/publish")
async def publish_internal_knowledge(
    knowledge_type: str,
    item_id: str,
    payload: KnowledgeLifecycleInput,
    current_user: InternalUser = Depends(require_capability("knowledge.publish")),
):
    return await publish_knowledge(knowledge_type, item_id, payload, current_user)


@app.post("/api/internal/knowledge/{knowledge_type}/{item_id}/archive")
async def archive_internal_knowledge(
    knowledge_type: str,
    item_id: str,
    payload: KnowledgeLifecycleInput,
    current_user: InternalUser = Depends(require_capability("knowledge.archive")),
):
    return await archive_knowledge(knowledge_type, item_id, payload, current_user)


@app.post("/api/internal/knowledge/{knowledge_type}/{item_id}/restore")
async def restore_internal_knowledge(
    knowledge_type: str,
    item_id: str,
    current_user: InternalUser = Depends(require_capability("knowledge.archive")),
):
    return await restore_knowledge(knowledge_type, item_id, current_user)


@app.get("/api/internal/knowledge/{knowledge_type}/{item_id}/versions")
async def read_knowledge_versions(
    knowledge_type: str,
    item_id: str,
    _: InternalUser = Depends(require_capability("knowledge.version.view")),
):
    return await list_versions(knowledge_type, item_id)


@app.get("/api/internal/knowledge/{knowledge_type}/{item_id}/versions/{version_id}")
async def read_knowledge_version(
    knowledge_type: str,
    item_id: str,
    version_id: str,
    _: InternalUser = Depends(require_capability("knowledge.version.view")),
):
    return await get_version(knowledge_type, item_id, version_id)


@app.post("/api/internal/knowledge/{knowledge_type}/{item_id}/versions/{version_id}/restore")
async def restore_knowledge_version(
    knowledge_type: str,
    item_id: str,
    version_id: str,
    current_user: InternalUser = Depends(require_capability("knowledge.version.restore")),
):
    return await restore_version(knowledge_type, item_id, version_id, current_user)


@app.post("/api/internal/knowledge/{knowledge_type}/{item_id}/attachments/upload-path")
async def create_knowledge_attachment_upload_path(
    knowledge_type: str,
    item_id: str,
    file_name: str,
    file_size: int,
    mime_type: str,
    current_user: InternalUser = Depends(require_capability("knowledge.upload")),
):
    return await create_attachment_upload_path(knowledge_type, item_id, file_name, file_size, mime_type, current_user)


@app.get("/api/internal/knowledge/{knowledge_type}/{item_id}/attachments")
async def read_knowledge_attachments(
    knowledge_type: str,
    item_id: str,
    current_user: InternalUser = Depends(require_capability("knowledge.view")),
):
    return await list_attachments(knowledge_type, item_id, current_user)


@app.post("/api/internal/knowledge/{knowledge_type}/{item_id}/attachments", status_code=201)
async def add_knowledge_attachment(
    knowledge_type: str,
    item_id: str,
    payload: AttachmentCreateInput,
    current_user: InternalUser = Depends(require_capability("knowledge.upload")),
):
    return await create_attachment(knowledge_type, item_id, payload, current_user)


@app.get("/api/internal/knowledge/attachments/{attachment_id}/download-url")
async def get_knowledge_attachment_download_url(
    attachment_id: str,
    current_user: InternalUser = Depends(require_capability("knowledge.download")),
):
    return await attachment_download_url(attachment_id, current_user)


@app.delete("/api/internal/knowledge/attachments/{attachment_id}")
async def remove_knowledge_attachment(
    attachment_id: str,
    current_user: InternalUser = Depends(require_capability("knowledge.upload")),
):
    return await delete_attachment(attachment_id, current_user)


@app.post("/api/internal/knowledge/{knowledge_type}/{item_id}/bookmark", status_code=201)
async def bookmark_knowledge_item(
    knowledge_type: str,
    item_id: str,
    current_user: InternalUser = Depends(require_capability("knowledge.bookmark")),
):
    return await add_bookmark(knowledge_type, item_id, current_user)


@app.delete("/api/internal/knowledge/{knowledge_type}/{item_id}/bookmark")
async def unbookmark_knowledge_item(
    knowledge_type: str,
    item_id: str,
    current_user: InternalUser = Depends(require_capability("knowledge.bookmark")),
):
    return await remove_bookmark(knowledge_type, item_id, current_user)
