export type InternalRole =
  | "admin"
  | "manager"
  | "staf_gudang"
  | "staf_operasional"

export type InternalUser = {
  auth_user_id: string
  email: string | null
  entity_type: "admin" | "manager" | "staff"
  entity_id: string
  role: InternalRole
  name: string
}

const apiUrl = import.meta.env.VITE_API_URL ?? "http://localhost:8000"

export class ApiError extends Error {
  readonly status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = "ApiError"
    this.status = status
  }
}

export async function getCurrentInternalUser(accessToken: string) {
  const response = await fetch(`${apiUrl}/api/auth/me`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  })
  if (!response.ok) {
    let detail = "Profil internal tidak dapat dimuat."
    try {
      const body = (await response.json()) as { detail?: string }
      if (body.detail) detail = body.detail
    } catch {
      // Gunakan pesan default jika backend tidak mengembalikan JSON.
    }
    throw new ApiError(detail, response.status)
  }

  return (await response.json()) as InternalUser
}

export type PosProduct = {
  product_id: string
  nama_barang: string
  kategori: string | null
  harga: number | string
  stok: number
  deskripsi: string | null
  gambar_url: string | null
  brand: string | null
  tags: string[] | null
  updated_at?: string | null
}

export type PosCartItem = {
  product: PosProduct
  qty: number
}

export type PosTransaction = {
  transaction_id: string
  no_invoice: string
  buyer_name_snapshot: string
  buyer_phone_snapshot: string
  tanggal_transaksi: string
  total_harga: number | string
  subtotal: number | string
  payment_method: string
  paid_amount: number | string
  change_amount: number | string
  status: "processing" | "completed" | "canceled"
  order_status: "processing" | "completed" | "canceled"
  payment_status: "unpaid" | "paid" | "canceled"
  items?: Array<{
    item_id: string
    product_id: string
    nama_barang_snapshot: string
    harga_satuan: number | string
    qty: number
    subtotal: number | string
  }>
}

async function posRequest<T>(accessToken: string, path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiUrl}${path}`, {
    ...init,
    headers: {
      Authorization: `Bearer ${accessToken}`,
      "Content-Type": "application/json",
      ...init?.headers,
    },
  })
  if (!response.ok) {
    let detail = "Permintaan POS gagal."
    try {
      const body = (await response.json()) as { detail?: string }
      if (body.detail) detail = body.detail
    } catch {
      // Gunakan pesan default jika backend tidak mengembalikan JSON.
    }
    throw new ApiError(detail, response.status)
  }
  return (await response.json()) as T
}

export function getPosProducts(accessToken: string) {
  return posRequest<PosProduct[]>(accessToken, "/api/pos/products")
}

export function getMarketplaceProducts() {
  return fetch(`${apiUrl}/api/marketplace/products`).then(async (response) => {
    if (!response.ok) throw new ApiError("Katalog produk gagal dimuat.", response.status)
    return (await response.json()) as PosProduct[]
  })
}

export function getMarketplaceProduct(productId: string) {
  return fetch(`${apiUrl}/api/marketplace/products/${productId}`).then(async (response) => {
    if (!response.ok) throw new ApiError("Produk tidak ditemukan.", response.status)
    return (await response.json()) as PosProduct
  })
}

export function createPosTransaction(accessToken: string, payload: {
  buyer_name: string
  buyer_phone: string
  items: Array<{ product_id: string; qty: number }>
  payment_method: string
  paid_amount: number
  reference?: string
}) {
  return posRequest<PosTransaction>(accessToken, "/api/pos/transactions", {
    method: "POST",
    body: JSON.stringify(payload),
  })
}

export function getTodayPosTransactions(accessToken: string) {
  return posRequest<PosTransaction[]>(accessToken, "/api/pos/transactions/today")
}

export function getPosTransaction(accessToken: string, transactionId: string) {
  return posRequest<PosTransaction>(accessToken, `/api/pos/transactions/${transactionId}`)
}

export function cancelPosTransaction(accessToken: string, transactionId: string) {
  return posRequest<PosTransaction>(accessToken, `/api/pos/transactions/${transactionId}/cancel`, {
    method: "POST",
    body: JSON.stringify({}),
  })
}

export type CustomerAddress = {
  address_id: string
  label: string
  recipient_name: string
  recipient_phone: string
  address: string
  is_default: boolean
}

export type MarketplaceOrder = {
  transaction_id: string
  no_invoice: string
  tanggal_transaksi: string
  total_harga: number | string
  status: string
  order_status: string
  payment_status: string
  payment_method: string
  fulfillment_method: string
  items?: Array<{ item_id: string; nama_barang_snapshot: string; harga_satuan: number | string; qty: number; subtotal: number | string }>
  payment?: { status: string; payment_method: string; amount: number | string }
  fulfillment?: { method: string; status: string }
}

export function getCustomerAddresses(accessToken: string) {
  return posRequest<CustomerAddress[]>(accessToken, "/api/customer/addresses")
}

export function createCustomerAddress(accessToken: string, payload: { label: string; recipient_name: string; recipient_phone: string; address: string; is_default?: boolean }) {
  return posRequest<CustomerAddress>(accessToken, "/api/customer/addresses", { method: "POST", body: JSON.stringify({ ...payload, is_default: payload.is_default ?? false }) })
}

export function createMarketplaceOrder(accessToken: string, payload: {
  items: Array<{ product_id: string; qty: number }>
  address_id?: string
  store_id?: string
  fulfillment_method: string
  payment_method: string
  shipping_fee: number
}) {
  return posRequest<{ transaction_id: string; no_invoice: string; total_harga: string; payment_status: string; order_status: string; payment_method: string; fulfillment_method: string }>(accessToken, "/api/marketplace/transactions", { method: "POST", body: JSON.stringify(payload) })
}

export function getCustomerOrders(accessToken: string) {
  return posRequest<MarketplaceOrder[]>(accessToken, "/api/customer/orders")
}

export function getCustomerOrder(accessToken: string, transactionId: string) {
  return posRequest<MarketplaceOrder>(accessToken, `/api/customer/orders/${transactionId}`)
}

export function confirmCustomerPayment(accessToken: string, transactionId: string) {
  return posRequest<MarketplaceOrder>(accessToken, `/api/customer/orders/${transactionId}/confirm-payment`, { method: "POST", body: JSON.stringify({}) })
}

export function updateCustomerProfile(accessToken: string, payload: { nama: string; no_hp: string }) {
  return posRequest<{ nama: string; no_hp: string }>(accessToken, "/api/customer/me", { method: "PATCH", body: JSON.stringify(payload) })
}

export function updateCustomerAddress(accessToken: string, addressId: string, payload: { label: string; recipient_name: string; recipient_phone: string; address: string; is_default: boolean }) {
  return posRequest<CustomerAddress>(accessToken, `/api/customer/addresses/${addressId}`, { method: "PATCH", body: JSON.stringify(payload) })
}

export function deleteCustomerAddress(accessToken: string, addressId: string) {
  return posRequest<{ deleted: boolean }>(accessToken, `/api/customer/addresses/${addressId}`, { method: "DELETE" })
}

export function getMarketplaceStores() {
  return fetch(`${apiUrl}/api/marketplace/stores`).then(async (response) => {
    if (!response.ok) throw new ApiError("Daftar toko gagal dimuat.", response.status)
    return (await response.json()) as Array<{ store_id: string; name: string; address: string; google_maps_url: string; opening_hours: string | null }>
  })
}

export function getCustomerCart(accessToken: string) { return posRequest<{ items: Array<{ cart_item_id: string; product_id: string; qty: number; product: PosProduct }> }>(accessToken, "/api/customer/cart") }
export function addCustomerCartItem(accessToken: string, productId: string, qty: number) { return posRequest<{ cart_item_id: string; qty: number }>(accessToken, "/api/customer/cart/items", { method: "POST", body: JSON.stringify({ product_id: productId, qty }) }) }
export function updateCustomerCartItem(accessToken: string, itemId: string, productId: string, qty: number) { return posRequest<{ cart_item_id: string }>(accessToken, `/api/customer/cart/items/${itemId}`, { method: "PATCH", body: JSON.stringify({ product_id: productId, qty }) }) }
export function clearCustomerCart(accessToken: string) { return posRequest(accessToken, "/api/customer/cart", { method: "DELETE" }) }
export function deleteCustomerCartItem(accessToken: string, itemId: string) { return posRequest(accessToken, `/api/customer/cart/items/${itemId}`, { method: "DELETE" }) }

export type MasterProduct = PosProduct & { created_at?: string; updated_at?: string }
export type MasterStore = { store_id: string; name: string; address: string; google_maps_url: string; opening_hours: string | null; is_active: boolean }
export type MasterProductInput = Omit<MasterProduct, "product_id" | "created_at" | "updated_at">
export type MasterStoreInput = Omit<MasterStore, "store_id">

export function getMasterProducts(accessToken: string) { return posRequest<MasterProduct[]>(accessToken, "/api/internal/masterdata/products") }
export function createMasterProduct(accessToken: string, payload: MasterProductInput) { return posRequest<MasterProduct>(accessToken, "/api/internal/masterdata/products", { method: "POST", body: JSON.stringify(payload) }) }
export function updateMasterProduct(accessToken: string, productId: string, payload: MasterProductInput) { return posRequest<MasterProduct>(accessToken, `/api/internal/masterdata/products/${productId}`, { method: "PATCH", body: JSON.stringify(payload) }) }
export function deleteMasterProduct(accessToken: string, productId: string) { return posRequest<{ deleted: boolean }>(accessToken, `/api/internal/masterdata/products/${productId}`, { method: "DELETE" }) }
export function getMasterStores(accessToken: string) { return posRequest<MasterStore[]>(accessToken, "/api/internal/masterdata/stores") }
export function createMasterStore(accessToken: string, payload: MasterStoreInput) { return posRequest<MasterStore>(accessToken, "/api/internal/masterdata/stores", { method: "POST", body: JSON.stringify(payload) }) }
export function updateMasterStore(accessToken: string, storeId: string, payload: MasterStoreInput) { return posRequest<MasterStore>(accessToken, `/api/internal/masterdata/stores/${storeId}`, { method: "PATCH", body: JSON.stringify(payload) }) }
export function deleteMasterStore(accessToken: string, storeId: string) { return posRequest<{ deleted: boolean }>(accessToken, `/api/internal/masterdata/stores/${storeId}`, { method: "DELETE" }) }

export type WarehouseStock = { product_id: string; nama_barang: string; kategori: string | null; brand: string | null; stok: number; harga: number | string }
export type WarehouseMovement = { movement_id: string; product_id: string; tipe_mutasi: string; qty_change: number; stok_sebelum: number; stok_sesudah: number; transaction_id: string | null; alasan: string | null; created_by: string | null; created_at: string; product?: Pick<WarehouseStock, "nama_barang" | "kategori" | "brand"> | null }
export function getWarehouseStock(accessToken: string) { return posRequest<WarehouseStock[]>(accessToken, "/api/internal/warehouse/stock") }
export function getWarehouseMovements(accessToken: string, params?: { product_id?: string; tipe_mutasi?: string }) { const query = new URLSearchParams(); if (params?.product_id) query.set("product_id", params.product_id); if (params?.tipe_mutasi) query.set("tipe_mutasi", params.tipe_mutasi); return posRequest<WarehouseMovement[]>(accessToken, `/api/internal/warehouse/movements${query.toString() ? `?${query}` : ""}`) }
export function createWarehouseMovement(accessToken: string, payload: { product_id: string; tipe_mutasi: string; qty_change: number; alasan: string }) { return posRequest<WarehouseMovement>(accessToken, "/api/internal/warehouse/movements", { method: "POST", body: JSON.stringify(payload) }) }
export type StockWorkflow = { request_id: string; tipe_request: string; reference_table: string; reference_id: string; deskripsi: string; requested_by: string; current_status: string; metadata?: Record<string, unknown>; created_at: string; approval?: { status: string; catatan?: string | null } | null }
export function createStockWorkflow(accessToken: string, payload: { product_id: string; tipe_mutasi: string; qty_change: number; alasan: string }) { return posRequest<StockWorkflow>(accessToken, "/api/internal/workflows", { method: "POST", body: JSON.stringify(payload) }) }
export function getWorkflows(accessToken: string, status?: string) { const query = status ? `?status=${encodeURIComponent(status)}` : ""; return posRequest<StockWorkflow[]>(accessToken, `/api/internal/workflows${query}`) }
export function approveWorkflow(accessToken: string, requestId: string, catatan?: string) { return posRequest<StockWorkflow>(accessToken, `/api/internal/workflows/${requestId}/approve`, { method: "POST", body: JSON.stringify({ catatan }) }) }
export function rejectWorkflow(accessToken: string, requestId: string, catatan: string) { return posRequest<StockWorkflow>(accessToken, `/api/internal/workflows/${requestId}/reject`, { method: "POST", body: JSON.stringify({ catatan }) }) }

export type InternalNotification = {
  notification_id: string
  type: string
  title: string
  message: string
  severity: "info" | "success" | "warning" | "critical"
  reference_table: string | null
  reference_id: string | null
  is_read: boolean
  read_at: string | null
  created_at: string
}

export type ActivityLog = {
  activity_id: string
  actor_user_id: string | null
  actor_role: string | null
  action: string
  resource_type: string
  resource_id: string | null
  module: string
  status: string
  description: string
  metadata: Record<string, unknown>
  created_at: string
}

export function getInternalNotifications(accessToken: string, unread?: boolean) {
  const query = unread === undefined ? "" : `?unread=${unread}`
  return posRequest<InternalNotification[]>(accessToken, `/api/internal/notifications${query}`)
}

export function getInternalUnreadCount(accessToken: string) {
  return posRequest<{ unread_count: number }>(accessToken, "/api/internal/notifications/unread-count")
}

export function markInternalNotificationRead(accessToken: string, notificationId: string) {
  return posRequest<InternalNotification>(accessToken, `/api/internal/notifications/${notificationId}/read`, { method: "PATCH" })
}

export function markAllInternalNotificationsRead(accessToken: string) {
  return posRequest<{ updated: number }>(accessToken, "/api/internal/notifications/read-all", { method: "POST" })
}

export function getActivityLogs(accessToken: string, params?: { module?: string; status?: string; limit?: number }) {
  const query = new URLSearchParams()
  if (params?.module) query.set("module", params.module)
  if (params?.status) query.set("status", params.status)
  if (params?.limit) query.set("limit", String(params.limit))
  return posRequest<ActivityLog[]>(accessToken, `/api/internal/activity-logs${query.toString() ? `?${query}` : ""}`)
}

export type InternalPersonnel = { personnel_id: string; nama: string; role?: string; personnel_type: string; manager_id?: string | null; status: string }
export type InternalMessage = { message_id: string; sender_id: string; receiver_id: string | null; target_role?: string | null; subject: string | null; body: string; is_read: boolean; created_at: string; reference_table?: string | null; reference_id?: string | null }
export type InternalDocument = { document_id: string; tipe_dokumen: string; judul: string; deskripsi: string | null; status: string; created_by: string; transaction_id: string | null; storage_bucket?: string; storage_path?: string; file_name?: string; mime_type?: string; file_size?: number; created_at: string }

export function getInternalPersonnel(accessToken: string, params?: { search?: string; role?: string }) {
  const query = new URLSearchParams(); if (params?.search) query.set("search", params.search); if (params?.role) query.set("role", params.role)
  return posRequest<InternalPersonnel[]>(accessToken, `/api/internal/personnel${query.toString() ? `?${query}` : ""}`)
}
export function getInternalMessages(accessToken: string) { return posRequest<InternalMessage[]>(accessToken, "/api/internal/messages") }
export function sendInternalMessage(accessToken: string, payload: { receiver_id?: string; target_role?: string; subject?: string; body: string }) { return posRequest<InternalMessage>(accessToken, "/api/internal/messages", { method: "POST", body: JSON.stringify(payload) }) }
export function markInternalMessageRead(accessToken: string, messageId: string) { return posRequest<InternalMessage>(accessToken, `/api/internal/messages/${messageId}/read`, { method: "POST" }) }
export function getInternalDocuments(accessToken: string, params?: { status?: string; tipe_dokumen?: string }) { const query = new URLSearchParams(); if (params?.status) query.set("status", params.status); if (params?.tipe_dokumen) query.set("tipe_dokumen", params.tipe_dokumen); return posRequest<InternalDocument[]>(accessToken, `/api/internal/documents${query.toString() ? `?${query}` : ""}`) }
export function getDocumentUploadPath(accessToken: string, file: File) { const query = new URLSearchParams({ file_name: file.name, file_size: String(file.size), mime_type: file.type || "application/octet-stream" }); return posRequest<{ bucket: string; path: string; file_name: string; mime_type: string }>(accessToken, `/api/internal/documents/upload-path?${query}`, { method: "POST" }) }
export function createInternalDocument(accessToken: string, payload: Record<string, unknown>) { return posRequest<InternalDocument>(accessToken, "/api/internal/documents", { method: "POST", body: JSON.stringify(payload) }) }
export function getDocumentDownloadUrl(accessToken: string, documentId: string) { return posRequest<{ url: string; expires_in: number }>(accessToken, `/api/internal/documents/${documentId}/download-url`) }

export type Correspondence = {
  correspondence_id: string
  nomor_agenda: string
  nomor_surat?: string | null
  tipe: "masuk" | "keluar"
  jenis_surat?: string | null
  sifat_surat?: string | null
  perihal: string
  asal_tujuan: string
  tanggal_surat?: string | null
  status: string
  created_at: string
  dispositions?: CorrespondenceDisposition[]
}
export type CorrespondenceDisposition = { disposition_id: string; correspondence_id: string; disposisi_ke: string; instruksi: string; status: string; catatan?: string | null; priority?: string; due_date?: string | null; created_at: string }
export function getCorrespondences(accessToken: string, params?: { tipe?: string; status?: string; search?: string }) { const query = new URLSearchParams(); if (params?.tipe) query.set("tipe", params.tipe); if (params?.status) query.set("status", params.status); if (params?.search) query.set("search", params.search); return posRequest<Correspondence[]>(accessToken, `/api/internal/correspondence${query.toString() ? `?${query}` : ""}`) }
export function createCorrespondence(accessToken: string, payload: Record<string, unknown>) { return posRequest<Correspondence>(accessToken, "/api/internal/correspondence", { method: "POST", body: JSON.stringify(payload) }) }
export function archiveCorrespondence(accessToken: string, id: string) { return posRequest<Correspondence>(accessToken, `/api/internal/correspondence/${id}/archive`, { method: "POST" }) }
export function createDisposition(accessToken: string, correspondenceId: string, payload: { disposisi_ke: string; instruksi: string; priority?: string; due_date?: string }) { return posRequest<CorrespondenceDisposition>(accessToken, `/api/internal/correspondence/${correspondenceId}/dispositions`, { method: "POST", body: JSON.stringify(payload) }) }
export function updateDisposition(accessToken: string, dispositionId: string, payload: { status: string; catatan?: string; completion_note?: string }) { return posRequest<CorrespondenceDisposition>(accessToken, `/api/internal/dispositions/${dispositionId}`, { method: "PATCH", body: JSON.stringify(payload) }) }

export type KnowledgeType = "policy" | "faq" | "article" | "video" | "case_study"
export type KnowledgeCategory = { category_id: string; nama_kategori: string; deskripsi?: string | null; urutan?: number; created_at?: string }
export type KnowledgeItem = {
  knowledge_type: KnowledgeType
  policy_id?: string
  faq_id?: string
  article_id?: string
  video_id?: string
  case_study_id?: string
  category_id?: string | null
  category?: KnowledgeCategory | null
  judul?: string | null
  pertanyaan?: string | null
  ringkasan?: string | null
  konten?: string | null
  jawaban?: string | null
  deskripsi?: string | null
  video_url?: string | null
  durasi_menit?: number | null
  thumbnail_url?: string | null
  kronologi?: string | null
  analisis?: string | null
  solusi?: string | null
  pelajaran?: string | null
  prioritas?: number
  nomor_versi?: string
  catatan_revisi?: string | null
  tags?: string[] | null
  created_by?: string | null
  is_published?: boolean
  status?: "draft" | "published" | "archived" | string
  published_at?: string | null
  archived_at?: string | null
  view_count?: number
  created_at?: string
  updated_at?: string
}
export type KnowledgeBookmark = { bookmark: { bookmark_id: string; source_table: string; source_id: string; personnel_id: string; created_at: string }; item: KnowledgeItem }
export function getKnowledgeCategories(accessToken: string) { return posRequest<KnowledgeCategory[]>(accessToken, "/api/internal/knowledge/categories") }
export function getKnowledgeItems(accessToken: string, type: KnowledgeType, params?: { category_id?: string; published?: boolean; search?: string }) { const query = new URLSearchParams(); if (params?.category_id) query.set("category_id", params.category_id); if (params?.published !== undefined) query.set("published", String(params.published)); if (params?.search) query.set("search", params.search); return posRequest<KnowledgeItem[]>(accessToken, `/api/internal/knowledge/${type}${query.toString() ? `?${query}` : ""}`) }
export function searchKnowledge(accessToken: string, queryText: string, params?: { knowledge_type?: KnowledgeType; category_id?: string }) { const query = new URLSearchParams({ q: queryText }); if (params?.knowledge_type) query.set("knowledge_type", params.knowledge_type); if (params?.category_id) query.set("category_id", params.category_id); return posRequest<KnowledgeItem[]>(accessToken, `/api/internal/knowledge/search?${query}`) }
export function getKnowledgeItem(accessToken: string, type: KnowledgeType, id: string) { return posRequest<KnowledgeItem>(accessToken, `/api/internal/knowledge/${type}/${id}`) }
export function createKnowledgeItem(accessToken: string, type: KnowledgeType, payload: Record<string, unknown>) { return posRequest<KnowledgeItem>(accessToken, `/api/internal/knowledge/${type}`, { method: "POST", body: JSON.stringify(payload) }) }
export function updateKnowledgeItem(accessToken: string, type: KnowledgeType, id: string, payload: Record<string, unknown>) { return posRequest<KnowledgeItem>(accessToken, `/api/internal/knowledge/${type}/${id}`, { method: "PATCH", body: JSON.stringify(payload) }) }
export function deleteKnowledgeItem(accessToken: string, type: KnowledgeType, id: string) { return posRequest<{ deleted: boolean }>(accessToken, `/api/internal/knowledge/${type}/${id}`, { method: "DELETE" }) }
export function getKnowledgeBookmarks(accessToken: string) { return posRequest<KnowledgeBookmark[]>(accessToken, "/api/internal/knowledge/bookmarks") }
export function addKnowledgeBookmark(accessToken: string, type: KnowledgeType, id: string) { return posRequest<Record<string, unknown>>(accessToken, `/api/internal/knowledge/${type}/${id}/bookmark`, { method: "POST" }) }
export function removeKnowledgeBookmark(accessToken: string, type: KnowledgeType, id: string) { return posRequest<{ deleted: boolean }>(accessToken, `/api/internal/knowledge/${type}/${id}/bookmark`, { method: "DELETE" }) }
export type KnowledgeVersion = { version_id: string; source_table: string; source_id: string; nomor_versi: string; catatan_perubahan?: string | null; diubah_oleh?: string | null; created_at: string; status?: string; change_type?: string; restore_source_version_id?: string | null; snapshot_data?: Record<string, unknown> }
export type KnowledgeAttachment = { attachment_id: string; source_table: string; source_id: string; nama_file?: string; file_name?: string; tipe_file?: string; mime_type?: string; ukuran_bytes?: number; file_size?: number; storage_bucket?: string; storage_path?: string; created_at: string }
export function getManagedKnowledge(accessToken: string, params?: { knowledge_type?: KnowledgeType; category_id?: string; status?: string; search?: string }) { const query = new URLSearchParams(); if (params?.knowledge_type) query.set("knowledge_type", params.knowledge_type); if (params?.category_id) query.set("category_id", params.category_id); if (params?.status) query.set("status", params.status); if (params?.search) query.set("search", params.search); return posRequest<KnowledgeItem[]>(accessToken, `/api/internal/masterdata/knowledge${query.toString() ? `?${query}` : ""}`) }
export function publishKnowledgeItem(accessToken: string, type: KnowledgeType, id: string, payload?: { catatan_perubahan?: string }) { return posRequest<KnowledgeItem>(accessToken, `/api/internal/knowledge/${type}/${id}/publish`, { method: "POST", body: JSON.stringify(payload || {}) }) }
export function archiveKnowledgeItem(accessToken: string, type: KnowledgeType, id: string, alasan: string) { return posRequest<KnowledgeItem>(accessToken, `/api/internal/knowledge/${type}/${id}/archive`, { method: "POST", body: JSON.stringify({ alasan }) }) }
export function restoreKnowledgeItem(accessToken: string, type: KnowledgeType, id: string) { return posRequest<KnowledgeItem>(accessToken, `/api/internal/knowledge/${type}/${id}/restore`, { method: "POST" }) }
export function getKnowledgeVersions(accessToken: string, type: KnowledgeType, id: string) { return posRequest<KnowledgeVersion[]>(accessToken, `/api/internal/knowledge/${type}/${id}/versions`) }
export function restoreKnowledgeVersion(accessToken: string, type: KnowledgeType, id: string, versionId: string) { return posRequest<KnowledgeItem>(accessToken, `/api/internal/knowledge/${type}/${id}/versions/${versionId}/restore`, { method: "POST" }) }
export function getKnowledgeAttachments(accessToken: string, type: KnowledgeType, id: string) { return posRequest<KnowledgeAttachment[]>(accessToken, `/api/internal/knowledge/${type}/${id}/attachments`) }
export function getKnowledgeUploadPath(accessToken: string, type: KnowledgeType, id: string, file: File) { const query = new URLSearchParams({ file_name: file.name, file_size: String(file.size), mime_type: file.type || "application/octet-stream" }); return posRequest<{ bucket: string; path: string; file_name: string; mime_type: string }>(accessToken, `/api/internal/knowledge/${type}/${id}/attachments/upload-path?${query}`, { method: "POST" }) }
export function createKnowledgeAttachment(accessToken: string, type: KnowledgeType, id: string, payload: Record<string, unknown>) { return posRequest<KnowledgeAttachment>(accessToken, `/api/internal/knowledge/${type}/${id}/attachments`, { method: "POST", body: JSON.stringify(payload) }) }
export function getKnowledgeAttachmentDownloadUrl(accessToken: string, attachmentId: string) { return posRequest<{ url: string; expires_in: number }>(accessToken, `/api/internal/knowledge/attachments/${attachmentId}/download-url`) }
export function deleteKnowledgeAttachment(accessToken: string, attachmentId: string) { return posRequest<{ deleted: boolean }>(accessToken, `/api/internal/knowledge/attachments/${attachmentId}`, { method: "DELETE" }) }

export type MisDashboard = {
  period: { date_from: string; date_to: string; channel?: string | null }
  kpis: { transactions: number; items: number; revenue: number; hpp: number; profit: number; shipping: number; unique_customers: number; new_customers: number; canceled: number; average_transaction: number; margin: number }
  daily: Array<{ date: string; revenue: number; profit: number; transactions: number; items: number }>
  channels: Array<{ channel: string; revenue: number; profit: number; transactions: number }>
  statuses: Array<{ status: string; count: number; revenue: number }>
  top_products: Array<{ product_id: string; name: string; qty: number; revenue: number; profit: number }>
  low_stock: Array<{ product_id: string; nama_barang: string; kategori?: string | null; brand?: string | null; stok: number; stock_threshold: number }>
  generated_at: string
}
export function getMisDashboard(accessToken: string, params?: { date_from?: string; date_to?: string; channel?: string }) { const query = new URLSearchParams(); if (params?.date_from) query.set("date_from", params.date_from); if (params?.date_to) query.set("date_to", params.date_to); if (params?.channel) query.set("channel", params.channel); return posRequest<MisDashboard>(accessToken, `/api/internal/mis/dashboard${query.toString() ? `?${query}` : ""}`) }

export type KpiPerformance = { kpi_id: string; kode_kpi: string; nama_kpi: string; satuan: string; arah_baik: string; actual: number; target: number | null; warning_threshold: number | null; achievement_percentage: number | null; variance: number | null; status: "achieved" | "warning" | "failed" | "no_target" }
export type KpiTarget = { target_id: string; kpi_id: string; personnel_id?: string | null; periode_tipe: string; periode_mulai: string; periode_selesai: string; nilai_target: number; nilai_peringatan: number | null; catatan: string | null; mis_kpi_definitions?: { kode_kpi: string; nama_kpi: string; satuan: string; arah_baik: string } }
export type MisReport = { period: { date_from: string; date_to: string; channel?: string | null }; summary: Record<string, number>; items: Array<Record<string, string | number | null>> }

export function getKpiPerformance(accessToken: string, params?: { date_from?: string; date_to?: string; personnel_id?: string }) { const query = new URLSearchParams(); if (params?.date_from) query.set("date_from", params.date_from); if (params?.date_to) query.set("date_to", params.date_to); if (params?.personnel_id) query.set("personnel_id", params.personnel_id); return posRequest<{ period: { date_from: string; date_to: string }; items: KpiPerformance[] }>(accessToken, `/api/internal/mis/kpis/performance${query.toString() ? `?${query}` : ""}`) }
export function getKpis(accessToken: string) { return posRequest<{ items: Array<Record<string, unknown>> }>(accessToken, "/api/internal/mis/kpis") }
export function getKpiTargets(accessToken: string, params?: { kpi_id?: string; periode_mulai?: string; periode_selesai?: string }) { const query = new URLSearchParams(); if (params?.kpi_id) query.set("kpi_id", params.kpi_id); if (params?.periode_mulai) query.set("periode_mulai", params.periode_mulai); if (params?.periode_selesai) query.set("periode_selesai", params.periode_selesai); return posRequest<{ items: KpiTarget[] }>(accessToken, `/api/internal/mis/kpis/targets${query.toString() ? `?${query}` : ""}`) }
export function createKpiTarget(accessToken: string, payload: Omit<KpiTarget, "target_id" | "mis_kpi_definitions">) { return posRequest<KpiTarget>(accessToken, "/api/internal/mis/kpis/targets", { method: "POST", body: JSON.stringify(payload) }) }
export function updateKpiTarget(accessToken: string, targetId: string, payload: Partial<Pick<KpiTarget, "nilai_target" | "nilai_peringatan" | "catatan">>) { return posRequest<KpiTarget>(accessToken, `/api/internal/mis/kpis/targets/${targetId}`, { method: "PATCH", body: JSON.stringify(payload) }) }

export function getMisReport(accessToken: string, report: "sales" | "profitability" | "inventory", params?: { date_from?: string; date_to?: string; channel?: string; product_id?: string; stock_status?: string; category?: string }) { const query = new URLSearchParams(); Object.entries(params ?? {}).forEach(([key, value]) => { if (value) query.set(key, value) }); return posRequest<MisReport>(accessToken, `/api/internal/mis/reports/${report}${query.toString() ? `?${query}` : ""}`) }
export async function exportMisReport(accessToken: string, report: "sales" | "profitability" | "inventory", params?: { date_from?: string; date_to?: string; channel?: string; product_id?: string; stock_status?: string; category?: string }) { const query = new URLSearchParams(); Object.entries(params ?? {}).forEach(([key, value]) => { if (value) query.set(key, value) }); const response = await fetch(`${apiUrl}/api/internal/mis/reports/${report}/export${query.toString() ? `?${query}` : ""}`, { headers: { Authorization: `Bearer ${accessToken}` } }); if (!response.ok) { let detail = "Export laporan gagal."; try { const body = await response.json() as { detail?: string }; if (body.detail) detail = body.detail } catch { /* response bukan JSON */ } throw new ApiError(detail, response.status) } return response.blob() }
